"""
Purchasing views module.
Centralized imports following Single Responsibility Principle.
"""

# Purchase Order views
from .purchase_order import (
    PurchaseOrderListView,
    PurchaseOrderCreateView,
    autosave_purchase_order_view,
    delete_purchase_order_view,
    extract_supplier_quote_data_view,
    PurchaseOrderPDFView,
    PurchaseOrderEmailView,
)

# Delivery Receipt views
from .delivery_receipt import (
    DeliveryReceiptListView,
    DeliveryReceiptCreateView,
    process_delivery_receipt_view,
)

# Stock Management views
from .stock import (
    StockListView,
    StockCreateView,
    UseStockView,
    consume_stock_api_view,
    create_stock_api_view,
    search_available_stock_api,
    deactivate_stock_api_view,
)

__all__ = [
    # Purchase Order views
    'PurchaseOrderListView',
    'PurchaseOrderCreateView', 
    'autosave_purchase_order_view',
    'delete_purchase_order_view',
    'extract_supplier_quote_data_view',
    'PurchaseOrderPDFView',
    'PurchaseOrderEmailView',
    
    # Delivery Receipt views
    'DeliveryReceiptListView',
    'DeliveryReceiptCreateView',
    'process_delivery_receipt_view',
    
    # Stock Management views
    'StockListView',
    'StockCreateView',
    'UseStockView',
    'consume_stock_api_view',
    'create_stock_api_view',
    'search_available_stock_api',
    'deactivate_stock_api_view',
]
