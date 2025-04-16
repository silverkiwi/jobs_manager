import logging
import os
import json
import base64
import requests

from django.conf import settings

from workflow.models import PurchaseOrder, PurchaseOrderLine, PurchaseOrderSupplierQuote
from workflow.helpers import get_company_defaults
from workflow.enums import MetalType

logger = logging.getLogger(__name__)

def save_quote_file(purchase_order, file_obj):
    """Save a supplier quote file and create a PurchaseOrderSupplierQuote record."""
    # Create quotes folder if it doesn't exist
    quotes_folder = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, "PO_Quotes")
    os.makedirs(quotes_folder, exist_ok=True)
    
    # Create a unique filename
    filename = f"{purchase_order.po_number}_{file_obj.name}"
    file_path = os.path.join(quotes_folder, filename)
    
    # Save the file
    with open(file_path, "wb") as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)
    
    # Create the record
    relative_path = os.path.relpath(file_path, settings.DROPBOX_WORKFLOW_FOLDER)
    quote = PurchaseOrderSupplierQuote.objects.create(
        purchase_order=purchase_order,
        filename=filename,
        file_path=relative_path,
        mime_type=file_obj.content_type,
    )
    
    return quote

def extract_data_from_supplier_quote(quote_path):
    """Extract data from a supplier quote file using Claude."""
    try:
        # Get the API key
        company_defaults = get_company_defaults()
        api_key = company_defaults.anthropic_api_key
        
        if not api_key:
            return None, "Anthropic API key not configured. Please add it in company settings."
        
        # Read and encode the file
        with open(quote_path, 'rb') as file:
            file_content = file.read()
        file_b64 = base64.b64encode(file_content).decode('utf-8')
        
        # Determine media type
        media_type = "application/pdf"
        if quote_path.lower().endswith(('.jpg', '.jpeg')):
            media_type = "image/jpeg"
        elif quote_path.lower().endswith('.png'):
            media_type = "image/png"
        
        # Get valid metal types for the prompt
        valid_metal_types = [choice[0] for choice in MetalType.choices]
        metal_types_str = ", ".join(valid_metal_types)
        
        # Create the prompt
        prompt = f"""
        Based on this quote document, please create a complete purchase order in JSON format with the following structure:

        {{
          "supplier": {{
            "name": "Supplier Name",
            "address": "Supplier Address (if available)"
          }},
          "quote_reference": "Quote reference number (if available)",
          "items": [
            {{
              "description": "EXACT raw text description from the quote",
              "quantity": "Quantity as shown in the quote",
              "unit_price": "Unit price as shown in the quote",
              "line_total": "Total cost for this line item",
              "metal_type": "Type of metal (one of: {metal_types_str})",
              "alloy": "Alloy specification (if available)",
              "specifics": "Any specific details about dimensions, grade, etc."
            }}
          ]
        }}

        IMPORTANT NOTES:
        1. Extract values EXACTLY as they appear in the quote, including any units (e.g., "per meter", "each", etc.)
        2. Make your best effort to extract all fields, but focus on getting the line item description and line_total correct
        3. For metal_type, ONLY use one of these valid values: {metal_types_str}
        4. Return ONLY the JSON object, no additional text
        
        Example JSON structure:
        [
          {{
            "description": "2m length of 50mm x 50mm x 3mm SHS Grade 350",
            "quantity": 6,
            "unit_cost": 90.40,
            "total_cost": 542.40,
            "price_tbc": false,
            "metal_type": "mild_steel",
            "alloy": "350",
            "specifics": "50mm x 50mm x 3mm SHS"
          }}
        ]
        
        Return ONLY a valid JSON array of line items.
        """
        
        # Call Claude API
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-3-opus-20240229",
                "max_tokens": 4000,
                "messages": [
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": file_b64
                                }
                            }
                        ]
                    }
                ]
            }
        )
        
        if response.status_code != 200:
            return None, f"Error from Anthropic API: {response.status_code}"
        
        # Extract JSON from response
        response_data = response.json()
        
        # Log token usage
        input_tokens = response_data.get("usage", {}).get("input_tokens", 0)
        output_tokens = response_data.get("usage", {}).get("output_tokens", 0)
        total_tokens = input_tokens + output_tokens
        
        logger.info(
            f"Claude API token usage for quote extraction: "
            f"Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}"
        )
        
        content = response_data.get("content", [])
        
        json_text = ""
        for block in content:
            if block.get("type") == "text":
                json_text += block.get("text", "")
        
        # Clean up JSON text
        json_text = json_text.strip()
        if json_text.startswith("```json"):
            json_text = json_text[7:]
        if json_text.endswith("```"):
            json_text = json_text[:-3]
        
        json_text = json_text.strip()
        
        # Parse JSON
        quote_data = json.loads(json_text)
        
        # Return the extracted data
        return quote_data, None
    
    except Exception as e:
        logger.exception(f"Error extracting data from supplier quote: {e}")
        return None, str(e)


def create_po_from_quote(purchase_order, quote):
    """Create purchase order lines from a supplier quote."""
    try:
        # Get the quote file path
        quote_path = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, quote.file_path)
        
        # Extract data from the quote
        quote_data, error = extract_data_from_supplier_quote(quote_path)
        
        if error:
            return None, error
        
        # Get items array
        if isinstance(quote_data, dict) and "items" in quote_data:
            items = quote_data["items"]
        else:
            return None, "Invalid response format from LLM"
        
        # Create PO lines
        for line_data in items:
            # Ensure description is present
            if not line_data.get("description"):
                continue
            
            # Create the PO line
            PurchaseOrderLine.objects.create(
                purchase_order=purchase_order,
                description=line_data.get("description", ""),
                quantity=line_data.get("quantity", 1),
                unit_cost=line_data.get("unit_price"),
                price_tbc=False,  # For quotes, price is typically known
                metal_type=line_data.get("metal_type", "unspecified"),
                alloy=line_data.get("alloy", ""),
                specifics=line_data.get("specifics", "")
            )
        
        return purchase_order, None
    
    except Exception as e:
        logger.exception(f"Error creating PO from quote: {e}")
        return None, str(e)