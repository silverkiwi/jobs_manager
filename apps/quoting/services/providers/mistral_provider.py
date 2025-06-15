import os
import base64
import json
import tempfile
import logging
from typing import Optional, Tuple, Dict, Any
from mistralai import Mistral

from ..ai_price_extraction import PriceExtractionProvider

logger = logging.getLogger(__name__)


def encode_pdf(pdf_path):
    """Encode the PDF file to base64."""
    try:
        with open(pdf_path, "rb") as pdf_file:
            return base64.b64encode(pdf_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encoding PDF: {str(e)}")
        return None


class MistralPriceExtractionProvider(PriceExtractionProvider):
    """Mistral AI provider for price extraction using OCR - EXACTLY like adhoc/mistral_parsing.py"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    def get_provider_name(self) -> str:
        return "Mistral"
    
    def _parse_ocr_to_price_data(self, client, ocr_response) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Parse OCR response into structured price data using Python parsing."""
        try:
            # Extract raw text from OCR response
            all_text = ""
            pages_data = []
            
            if hasattr(ocr_response, 'pages') and ocr_response.pages:
                for i, page in enumerate(ocr_response.pages, 1):
                    page_text = ""
                    if hasattr(page, 'markdown') and page.markdown:
                        page_text = page.markdown
                    elif hasattr(page, 'text') and page.text:
                        page_text = page.text
                    
                    if page_text:
                        all_text += page_text + "\n"
                        pages_data.append({
                            'page_number': i,
                            'text': page_text
                        })
            
            if not all_text.strip():
                return None, "No text content extracted from PDF"
            
            # Parse supplier name from first few lines
            lines = all_text.split('\n')
            supplier_name = "Unknown Supplier"
            for line in lines[:10]:  # Check first 10 lines
                line = line.strip()
                if line and len(line) > 3 and not line.isdigit():
                    supplier_name = line
                    break
            
            logger.info(f"Identified supplier: {supplier_name}")
            
            # Parse individual product items from OCR text
            items = []
            line_count = 0
            
            for line in lines:
                line = line.strip()
                line_count += 1
                
                # Skip empty lines and headers
                if not line or len(line) < 10:
                    continue
                    
                # Look for lines that might contain product data
                # This is a basic parser - can be enhanced based on actual price list formats
                if any(char.isdigit() for char in line) and ('$' in line or '.' in line):
                    # Extract basic product info
                    description = line[:200] if len(line) > 200 else line  # Limit description length
                    
                    # Try to extract price (basic regex for price patterns)
                    import re
                    price_match = re.search(r'\$?(\d+\.?\d*)', line)
                    unit_price = price_match.group(1) if price_match else None
                    
                    # Create basic product item
                    item = {
                        'description': description,
                        'supplier_item_code': '',
                        'variant_id': f"line_{line_count}",  # Simple variant ID
                        'unit_price': unit_price,
                        'specifications': '',
                        'dimensions': ''
                    }
                    items.append(item)
            
            logger.info(f"Parsed {len(items)} potential product items from OCR text")
            
            # Return structured data for Django ORM
            structured_data = {
                'supplier': {
                    'name': supplier_name,
                    'customer': '',
                    'date': ''
                },
                'items': items,
                'raw_ocr_text': all_text,
                'pages': pages_data,
                'parsing_stats': {
                    'total_lines': len(lines),
                    'items_found': len(items),
                    'pages_processed': len(pages_data)
                }
            }
            
            logger.info(f"Final parsing results: supplier={supplier_name}, {len(items)} items, {len(pages_data)} pages")
            return structured_data, None
            
        except Exception as e:
            logger.error(f"Error parsing OCR to price data: {e}")
            return None, str(e)
        
    def extract_price_data(
        self, 
        file_path: str, 
        content_type: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Extract OCR data using Mistral - EXACTLY what adhoc/mistral_parsing.py does."""
        try:
            # Initialize the client
            if not self.api_key:
                raise ValueError("MISTRAL_API_KEY not provided")

            client = Mistral(api_key=self.api_key)

            # File handling
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF file not found: {file_path}")

            logger.info("Processing PDF with Mistral OCR...")
            # Encode the PDF to base64
            base64_pdf = encode_pdf(file_path)
            if not base64_pdf:
                raise ValueError("Failed to encode PDF file")
            # Process the document with OCR
            ocr_response = client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "document_url",
                    "document_url": f"data:application/pdf;base64,{base64_pdf}"
                },
                include_image_base64=True
            )
            # Convert OCR response to a serializable dictionary
            # This function should be outside main or properly nested if it's a local helper
            # For now, assuming it's a helper function for the try block
            def ocr_response_to_dict(ocr_obj):
                if hasattr(ocr_obj, '__dict__'):
                    return {k: ocr_response_to_dict(v) for k, v in ocr_obj.__dict__.items()}
                elif isinstance(ocr_obj, list):
                    return [ocr_response_to_dict(item) for item in ocr_obj]
                else:
                    return ocr_obj
            # Save the results to a JSON file
            json_output_file = os.path.join(tempfile.gettempdir(), "ocr_results.json")
            with open(json_output_file, "w") as f:
                json.dump(ocr_response_to_dict(ocr_response), f, indent=2)
            # Save the results to a Markdown file
            md_output_file = os.path.join(tempfile.gettempdir(), "ocr_results.md")
            with open(md_output_file, "w", encoding="utf-8") as f:
                if hasattr(ocr_response, 'pages') and ocr_response.pages:
                    for i, page in enumerate(ocr_response.pages, 1):
                        if hasattr(page, 'markdown') and page.markdown:
                            f.write(f"# Page {i}\n\n")
                            f.write(page.markdown)
                            f.write("\n\n---\n\n") # Add separator between pages
            logger.info("OCR processing complete!")
            logger.info(f"JSON results saved to: {os.path.abspath(json_output_file)}")
            logger.info(f"Markdown results saved to: {os.path.abspath(md_output_file)}")
            # Log a preview of the results
            logger.debug("Preview of the OCR results (first page):")
            if hasattr(ocr_response, 'pages') and ocr_response.pages:
                first_page = ocr_response.pages[0]
                logger.debug(f"Page 1 of {len(ocr_response.pages)}:")
                # Try to get markdown content first, fall back to text
                if hasattr(first_page, 'markdown') and first_page.markdown:
                    preview = first_page.markdown[:500]
                    logger.debug(preview + ("..." if len(first_page.markdown) > 500 else ""))
                elif hasattr(first_page, 'text') and first_page.text:
                    preview = first_page.text[:500]
                    logger.debug(preview + ("..." if len(first_page.text) > 500 else ""))
                else:
                    logger.debug("No text content available for preview")
            else:
                logger.warning("No pages found in the OCR response.")
            logger.info(f"Full results have been saved to:")
            logger.info(f"- {os.path.abspath(json_output_file)}")
            logger.info(f"- {os.path.abspath(md_output_file)}")
            
            # Now parse the OCR text into structured price data
            return self._parse_ocr_to_price_data(client, ocr_response)
            
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            if 'retry_after' in str(e).lower():
                logger.warning("The server is processing your request. Please try again in a few moments.")
            return None, str(e)