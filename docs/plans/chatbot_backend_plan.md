# Chatbot Backend Plan

## What we need:
- API endpoints for price/stock lookups
- API key authentication for the chatbot service

## Sample Conversation to Define Requirements

**User**: "I need to price 50 meters of 25x25x3mm steel angle for the Johnson job"

**Assistant**: "I found several options for 25x25x3mm steel angle:

**In Stock:**
- We have 45m available at $12.50/m (cost $8.30/m) - Location: Rack A3
- 23m at $11.80/m (cost $7.90/m) - Location: Yard 

**Supplier Pricing:**
- Steel Solutions: 50m available at $7.20/m (6m lengths)
- Metro Steel: 100m+ available at $6.95/m (12m lengths) 
- Aussie Steel: Out of stock, ETA 2 weeks

You need 50m total. Options:
1. Use our stock (45m + 23m = 68m available) - Mix of pricing
2. Order from Metro Steel - Best price, good lengths
3. Combine: Use 45m from stock + order 5m from Metro"

**User**: "What about 304 stainless instead?"

**Assistant**: "For 25x25x3mm 304 stainless angle:

**In Stock:**
- 12m available at $45.20/m (cost $32.80/m) - Location: SS Rack 

**Supplier Pricing:**
- Stainless Supplies: 25m available at $28.50/m 
- AllSteel: 50m+ available at $31.20/m
- Steel Solutions: Don't stock stainless angle

You'd need to order 38m more from suppliers. Stainless Supplies has the best price."

## Implementation:

### 1. API Endpoints (`apps/quoting/views.py`, `apps/quoting/urls.py`)

#### Material Search API
`GET /api/mcp/search_materials/?description=25x25x3mm+angle&metal_type=steel&limit=20`

**Optional Parameters:**
- `suppliers=steel-solutions,metro-steel` - Filter by specific suppliers
- `in_stock_only=true` - Only show items we have in stock
- `min_quantity=10` - Minimum quantity required
- `alloy=304` - Filter by alloy type

**Response Format:**
```json
{
  "stock_items": [
    {
      "description": "25x25x3mm Steel Angle",
      "quantity": 45.0,
      "unit_cost": 8.30,
      "retail_price": 12.50,
      "location": "Rack A3",
      "metal_type": "steel",
      "alloy": null
    }
  ],
  "supplier_products": [
    {
      "product_name": "25x25x3mm Steel Angle 6m lengths",
      "supplier_name": "Steel Solutions", 
      "variant_price": 7.20,
      "variant_available_stock": 50,
      "price_unit": "per metre",
      "metal_type": "steel"
    }
  ]
}
```

#### Alternative Materials API
`GET /api/mcp/search_alternatives/?base_description=25x25x3mm+angle&metal_type=stainless&alloy=304`

#### Past Quotes Vector Search API
`POST /api/mcp/search_similar_quotes/`

**Request Body:**
```json
{
  "query": "warehouse steel angle framing",
  "limit": 5
}
```

**Response Format:**
```json
{
  "similar_quotes": [
    {
      "job_name": "Johnson Warehouse Extension", 
      "client_name": "Johnson Construction",
      "quote_date": "2024-03-15",
      "materials_summary": "Steel angle framing, 60m @ $12.80/m",
      "total_value": 768.00,
      "similarity_score": 0.87,
      "context": "Warehouse structural framing using 25x25x3mm steel angle"
    }
  ]
}
```

#### Enriched Context API
`POST /api/mcp/get_enriched_context/`

**Request Body:**
```json
{
  "material_query": "steel angle warehouse",
  "include_trends": true,
  "include_recommendations": true
}
```

**Response Format:**
```json
{
  "material_insights": [
    "25x25x3mm Steel Angle commonly used for warehouse framing",
    "Typical warehouse jobs use 50-200m depending on span"
  ],
  "pricing_context": [
    "Recent jobs averaged $12.50/m for similar specifications",
    "Steel prices up 8% in last 6 months"
  ],
  "recommendations": [
    "Metro Steel typically best value for bulk orders",
    "Consider 12m lengths to minimize cuts and waste"
  ]
}
```

### 2. Authentication
- Simple API key in request header: `X-API-Key: <service_key>`
- Validate against a hardcoded key or basic API key model

### 3. Response Format
Return JSON combining Stock and SupplierProduct data:
- **Stock items**: description, quantity, unit_cost, retail_price, location, metal_type, alloy
- **Supplier products**: product_name, supplier_name, variant_price, variant_available_stock, price_unit, metal_type
