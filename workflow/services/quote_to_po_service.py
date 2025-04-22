import logging
import os
import json
import base64
import requests
import mimetypes
import pdfplumber
import re
from decimal import Decimal, InvalidOperation
from rapidfuzz import process, fuzz

from django.conf import settings
from django.db.models import Q

from workflow.models import PurchaseOrder, PurchaseOrderLine, \
    PurchaseOrderSupplierQuote, Client
from workflow.helpers import get_company_defaults
from workflow.enums import MetalType

logger = logging.getLogger(__name__)

# Global flag to control PDF parser usage
USE_PDF_PARSER = False


def normalize(s):
    """Normalize a string for comparison."""
    if not s:
        return ""
    return ' '.join(
        s.lower().split())  # lower, remove extra whitespace, preserve everything else


def fuzzy_find_supplier(supplier_name):
    """
    Find a supplier in the database using fuzzy matching.

    Args:
        supplier_name (str): The supplier name to match

    Returns:
        tuple: (matched_supplier, original_name) - The matched supplier object and the original name
    """
    if not supplier_name:
        return None, supplier_name

    # Get all suppliers
    suppliers = Client.objects.all()

    # Extract supplier names and create a mapping from name to supplier object
    supplier_names = [s.name for s in suppliers]
    supplier_map = {s.name: s for s in suppliers}

    # Build a map from normalized -> original so we can return the true supplier name
    norm_map = {normalize(name): name for name in supplier_names}
    norm_names = list(norm_map.keys())

    # Normalize the input supplier name
    norm_supplier = normalize(supplier_name)

    # Find the best match
    if not norm_names:
        # No suppliers in database
        logger.warning(f"No suppliers in database to match against: {supplier_name}")
        return None, supplier_name

    match, score, _ = process.extractOne(
        norm_supplier,
        norm_names,
        scorer=fuzz.token_set_ratio
    )

    # Use a threshold to ensure the match is good enough
    if score < 85:
        # Score too low
        logger.warning(f"No supplier match found for: {supplier_name}")
        return None, supplier_name

    original_name = norm_map[match]
    matched_supplier = supplier_map[original_name]
    logger.info(
        f"Found fuzzy supplier match: '{supplier_name}' -> '{original_name}' (score: {score})")
    return matched_supplier, supplier_name


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


def extract_data_from_supplier_quote(quote_path, content_type=None,
                                     use_pdf_parser=USE_PDF_PARSER):
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

        # Determine if this is a PDF
        is_pdf = content_type == 'application/pdf' or quote_path.lower().endswith(
            '.pdf')

        # Extract text from PDF if requested
        extracted_text = None
        logger.info(f"PDF extraction: is_pdf={is_pdf}, use_pdf_parser={use_pdf_parser}")

        if is_pdf and use_pdf_parser:
            try:
                text = []
                with pdfplumber.open(quote_path) as pdf:
                    for page in pdf.pages:
                        text.append(page.extract_text())
                extracted_text = "\n\n".join(text)
                logger.info(f"Extracted {len(extracted_text)} characters from PDF")
                # Log a shorter version of the extracted text for debugging
                preview_length = min(10000, len(extracted_text))
                logger.info(
                    f"PDF TEXT PREVIEW (first {preview_length} chars): {extracted_text[:preview_length]}")
                # Log the full text if needed for detailed debugging
                logger.debug(f"FULL PDF EXTRACTED TEXT: {extracted_text}")
            except Exception as e:
                logger.error(f"Failed to extract text from PDF: {e}")
                # Continue with the original PDF if text extraction fails

        # Determine media type and content type
        if is_pdf and not use_pdf_parser:
            # Send PDF directly
            api_content_type = "document"
            media_type = "application/pdf"
        elif content_type and content_type.startswith('image/'):
            # Send image directly
            api_content_type = "image"
            media_type = content_type
        else:
            # Send as text (either extracted from PDF or other text format)
            api_content_type = "text"
            media_type = "text/plain"

        logger.info(
            f"File type detection: path={quote_path}, content_type={content_type}, is_pdf={is_pdf}, use_pdf_parser={use_pdf_parser}")

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
            "quantity": "Quantity as a numeric value only (e.g., 2, 3.5)",
            "dimensions": "Length, width, height, etc. if available",
            "unit_price": "Unit price as shown in the quote",
            "line_total": "Total cost for this line item as a numeric value only (e.g., 542.40)",
            "supplier_item_code": "Supplier's item code or SKU if available",
            "metal_type": "Type of metal (one of: {metal_types_str})",
            "alloy": "Alloy specification (if available)",
            "specifics": "Any specific details about grade, etc."
            }}
        ]
        }}

        IMPORTANT INSTRUCTIONS:
        1. Extract the "description" EXACTLY as it appears in the quote
        2. For "quantity" and "line_total", extract ONLY the numeric values (remove currency symbols, commas, etc.)
        3. For "unit_price", keep the original format including any price units (e.g., "per meter", "each")
        4. For "metal_type", ONLY use one of the following: {metal_types_str}
        5. If a price format contains units like "$/m" or "per meter", capture that in unit_price but extract the numeric line_total
        6. Do not guess values—leave them null or omit the field if unknown
        7. Return ONLY a single valid JSON object in the format above

        DO NOT return a JSON array of line items on their own—embed them in the full structure.

        Example output:
        {{
        "supplier": {{
            "name": "Abel Metal Products (2020) Ltd",
            "address": "12 Industrial Way, Penrose, Auckland"
        }},
        "quote_reference": "Q-12345",
        "items": [
            {{
            "description": "2m length of 50mm x 50mm x 3mm SHS Grade 350",
            "quantity": 6,
            "dimenisons": "2m",
            "unit_price": "90.40ea",
            "line_total": 542.40,
            "supplier_item_code": "SHS-50-3-350",
            "metal_type": "mild_steel",
            "alloy": "350",
            "specifics": "50mm x 50mm x 3mm SHS"
            }}
        ]
        }}
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
                "model": "claude-3-7-sonnet-20250219",
                "max_tokens": 4000,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                                       {"type": "text", "text": prompt},
                                   ] + (
                                       # If we have extracted text, send it as text
                                       [{"type": "text",
                                         "text": extracted_text}] if extracted_text else
                                       # Otherwise send the file
                                       [{
                                           "type": api_content_type,
                                           "source": {
                                               "type": "base64",
                                               "media_type": media_type,
                                               "data": file_b64
                                           }
                                       }]
                                   )
                    }
                ]
            }
        )

        if response.status_code != 200:
            try:
                error_details = response.json()
                error_message = error_details.get('error', {}).get('message',
                                                                   'Unknown error')
                logger.error(
                    f"Anthropic API error: {response.status_code} - {error_message}")
                logger.error(f"Full error response: {error_details}")
                return None, f"Error from Anthropic API: {response.status_code} - {error_message}"
            except Exception as e:
                logger.error(f"Failed to parse Anthropic API error response: {e}")
                logger.error(f"Raw response: {response.text}")
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

        # Process supplier data if it exists in the expected format
        try:
            supplier_name_from_quote = quote_data["supplier"]["name"]
            matched_supplier, original_name = fuzzy_find_supplier(
                supplier_name_from_quote)

            # Add original and matched supplier info
            quote_data["supplier"]["original_name"] = original_name
            quote_data["matched_supplier"] = None

            if matched_supplier:
                quote_data["matched_supplier"] = {
                    "id": str(matched_supplier.id),
                    "name": matched_supplier.name,
                    "xero_id": getattr(matched_supplier, 'xero_id', None)
                }
        except (KeyError, TypeError):
            logging.warning("Supplier name not found in quote JSON")
            pass

        # Return the extracted data
        return quote_data, None

    except Exception as e:
        logger.exception(f"Error extracting data from supplier quote: {e}")
        return None, str(e)


def create_po_from_quote(purchase_order, quote):
    """Create purchase order lines from a supplier quote."""
    # Get the quote file path
    quote_path = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, quote.file_path)

    # Extract data from the quote
    quote_data, error = extract_data_from_supplier_quote(quote_path, quote.mime_type)

    if error:
        return None, error

    # Save the raw extracted data to the quote record
    quote.extracted_data = quote_data
    quote.save()

    # Get items array
    items = quote_data.get("items", [])

    # Create PO lines
    items = quote_data.get("items", [])
    for line_data in items:
        description = line_data.get("description", "")
        if not description:
            logger.warning("Skipping line item with no description")
            continue

        # Extract numeric values directly
        try:
            quantity = float(line_data.get("quantity", 1))
        except (ValueError, TypeError):
            quantity = 1

        try:
            line_total = float(line_data.get("line_total", 0))
        except (ValueError, TypeError):
            line_total = 0

        extracted_unit_price = None
        try:
            if line_data.get("unit_price") is not None:
                extracted_unit_price = float(line_data.get("unit_price"))
        except (ValueError, TypeError):
            pass

        # Calculate unit cost
        unit_cost = None
        if line_total > 0 and quantity > 0:
            unit_cost = line_total / quantity

            # Log warning if extracted price exists and differs significantly
            if extracted_unit_price is not None and abs(
                    unit_cost - extracted_unit_price) > 0.01:
                logger.warning(
                    f"Unit cost discrepancy for: '{description}'. "
                    f"Calculated: {unit_cost:.2f} vs Extracted: {extracted_unit_price:.2f}. "
                    f"Using calculated value."
                )
        else:
            logger.warning(
                f"Could not calculate unit cost for: '{description}'. Line total: {line_total}, Quantity: {quantity}")

        # Create the PO line
        PurchaseOrderLine.objects.create(
            purchase_order=purchase_order,
            description=description,
            quantity=quantity,
            unit_cost=unit_cost,
            price_tbc=False,
            supplier_item_code=line_data.get("supplier_item_code", ""),
            metal_type=line_data.get("metal_type", "unspecified"),
            alloy=line_data.get("alloy", ""),
            specifics=line_data.get("specifics", ""),
            dimensions=line_data.get("dimensions", ""),
            raw_line_data=json.loads(json.dumps(line_data))
            # Use JSON serialization to avoid validation issues
        )

    return purchase_order, None
