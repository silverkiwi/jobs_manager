import hashlib
import json
import logging
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from django.utils import timezone

import google.generativeai as genai

from apps.workflow.helpers import get_company_defaults
from apps.workflow.enums import AIProviderTypes
from apps.job.enums import MetalType
from apps.quoting.models import ProductParsingMapping

logger = logging.getLogger(__name__)


class ProductParser:
    """
    Optimistic parser that maps supplier product data to inventory format
    using LLM with permanent mapping storage for consistency.
    """
    
    PARSER_VERSION = "1.0.0"
    
    def __init__(self):
        self.company_defaults = get_company_defaults()
        self._gemini_client = None
    
    @property
    def gemini_client(self):
        """Lazy initialization of Gemini client."""
        if self._gemini_client is None:
            ai_provider = self.company_defaults.ai_providers.filter(
                provider_type=AIProviderTypes.GOOGLE,
                active=True
            ).first()
            
            if not ai_provider or not ai_provider.api_key:
                raise ValueError("No active Gemini AI provider configured")
            
            genai.configure(api_key=ai_provider.api_key)
            self._gemini_client = genai.GenerativeModel('gemini-1.5-flash')
        
        return self._gemini_client
    
    def _calculate_input_hash(self, product_data: Dict[str, Any]) -> str:
        """Calculate SHA-256 hash based on description only."""
        description = str(product_data.get('description', '') or product_data.get('product_name', ''))
        return hashlib.sha256(description.encode()).hexdigest()
    
    def _get_cached_mapping(self, input_hash: str) -> Optional[ProductParsingMapping]:
        """Retrieve existing mapping from database."""
        try:
            return ProductParsingMapping.objects.get(input_hash=input_hash)
        except ProductParsingMapping.DoesNotExist:
            return None
    
    def _create_parsing_prompt(self, product_data: Dict[str, Any]) -> str:
        """Create LLM prompt for parsing product data."""
        metal_types = [choice[0] for choice in MetalType.choices]
        
        prompt = f"""
Parse the following supplier product data and extract structured information for inventory management.

INPUT DATA:
Product Name: {product_data.get('product_name', 'N/A')}
Description: {product_data.get('description', 'N/A')}
Specifications: {product_data.get('specifications', 'N/A')}
Item Number: {product_data.get('item_no', 'N/A')}
Variant Info: {product_data.get('variant_id', 'N/A')}
Dimensions: {product_data.get('variant_width', 'N/A')} x {product_data.get('variant_length', 'N/A')}
Price: {product_data.get('variant_price', 'N/A')} {product_data.get('price_unit', 'N/A')}

EXTRACT and return JSON with these fields:

{{
    "item_code": "Standardized item code for inventory (create if none exists)",
    "description": "Clean, standardized description for inventory (max 255 chars)",
    "metal_type": "One of: {', '.join(metal_types)} or null if not metal",
    "alloy": "Alloy specification like 304, 6061, etc. or null",
    "specifics": "Specific details like grade, finish, etc. (max 255 chars)",
    "dimensions": "Standardized dimensions format like '2400x1200x3mm' or null",
    "unit_cost": "Numeric price value only (no currency symbols)",
    "price_unit": "Standardized unit like 'per metre', 'each', 'per kg', etc.",
    "confidence": "Your confidence in this parsing (0.0 to 1.0)"
}}

RULES:
- Be optimistic - make reasonable inferences from available data
- Standardize formats (dimensions, units, descriptions)
- If metal type is unclear, set to null rather than guessing
- Create meaningful item codes if none provided
- Keep descriptions concise but informative
- Ensure all dimensions follow consistent format
- Extract numeric price only (remove currency symbols, "from", etc.)
"""
        return prompt
    
    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """Call LLM and parse response."""
        try:
            response = self.gemini_client.generate_content(prompt)
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Try to find JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in LLM response")
            
            json_str = response_text[start_idx:end_idx]
            parsed_data = json.loads(json_str)
            
            return {
                'parsed_data': parsed_data,
                'full_response': response_text,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
            return {
                'parsed_data': {},
                'full_response': str(e),
                'success': False
            }
    
    def _save_mapping(
        self, 
        input_hash: str, 
        input_data: Dict[str, Any], 
        parsed_data: Dict[str, Any], 
        llm_response: Dict[str, Any]
    ) -> ProductParsingMapping:
        """Save parsing mapping to database."""
        
        # Convert Decimal values to strings for JSON serialization
        serializable_input = {}
        for key, value in input_data.items():
            if isinstance(value, Decimal):
                serializable_input[key] = str(value)
            else:
                serializable_input[key] = value
        
        # Convert confidence to Decimal if present
        confidence = parsed_data.get('confidence')
        if confidence is not None:
            try:
                confidence = Decimal(str(confidence))
            except:
                confidence = None
        
        # Convert unit_cost to Decimal if present
        unit_cost = parsed_data.get('unit_cost')
        if unit_cost is not None:
            try:
                unit_cost = Decimal(str(unit_cost))
            except:
                unit_cost = None
        
        mapping = ProductParsingMapping(
            input_hash=input_hash,
            input_data=serializable_input,
            mapped_item_code=parsed_data.get('item_code'),
            mapped_description=parsed_data.get('description'),
            mapped_metal_type=parsed_data.get('metal_type'),
            mapped_alloy=parsed_data.get('alloy'),
            mapped_specifics=parsed_data.get('specifics'),
            mapped_dimensions=parsed_data.get('dimensions'),
            mapped_unit_cost=unit_cost,
            mapped_price_unit=parsed_data.get('price_unit'),
            parser_version=self.PARSER_VERSION,
            parser_confidence=confidence,
            llm_response=llm_response
        )
        
        mapping.save()
        return mapping
    
    def parse_product(self, product_data: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """
        Parse supplier product data to inventory format.
        
        Args:
            product_data: Raw supplier product data
            
        Returns:
            Tuple of (parsed_data_dict, was_cached)
        """
        # Calculate input hash based on description
        input_hash = self._calculate_input_hash(product_data)
        
        # Check for existing mapping
        existing_mapping = self._get_cached_mapping(input_hash)
        if existing_mapping:
            logger.info(f"Using cached mapping for hash {input_hash[:8]}...")
            return {
                'item_code': existing_mapping.mapped_item_code,
                'description': existing_mapping.mapped_description,
                'metal_type': existing_mapping.mapped_metal_type,
                'alloy': existing_mapping.mapped_alloy,
                'specifics': existing_mapping.mapped_specifics,
                'dimensions': existing_mapping.mapped_dimensions,
                'unit_cost': existing_mapping.mapped_unit_cost,
                'price_unit': existing_mapping.mapped_price_unit,
                'confidence': existing_mapping.parser_confidence,
                'parser_version': existing_mapping.parser_version,
            }, True
        
        # Parse with LLM
        logger.info(f"Parsing new product data with LLM (hash: {input_hash[:8]}...)")
        prompt = self._create_parsing_prompt(product_data)
        llm_response = self._call_llm(prompt)
        
        if not llm_response['success']:
            logger.error(f"Failed to parse product data: {llm_response['full_response']}")
            return {}, False
        
        # Save mapping for future use
        mapping = self._save_mapping(
            input_hash, 
            product_data, 
            llm_response['parsed_data'], 
            llm_response
        )
        
        logger.info(f"Created new mapping for hash {input_hash[:8]}...")
        
        return {
            'item_code': mapping.mapped_item_code,
            'description': mapping.mapped_description,
            'metal_type': mapping.mapped_metal_type,
            'alloy': mapping.mapped_alloy,
            'specifics': mapping.mapped_specifics,
            'dimensions': mapping.mapped_dimensions,
            'unit_cost': mapping.mapped_unit_cost,
            'price_unit': mapping.mapped_price_unit,
            'confidence': mapping.parser_confidence,
            'parser_version': mapping.parser_version,
        }, False


def parse_supplier_product(product_data: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """
    Convenience function to parse a single supplier product.
    
    Args:
        product_data: Raw supplier product data
        
    Returns:
        Tuple of (parsed_data_dict, was_cached)
    """
    parser = ProductParser()
    return parser.parse_product(product_data)