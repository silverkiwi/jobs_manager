"""
RESTful URLs for the purchasing app.
Following REST conventions with clear resource-based naming.
"""

from django.urls import path
from . import views

app_name = 'purchasing'

urlpatterns = [
    # Purchase Orders - REST endpoints
    path(
        'purchase-orders/',
        views.PurchaseOrderListView.as_view(),
        name='purchase_orders_list'
    ),
    path(
        'purchase-orders/new/',
        views.PurchaseOrderCreateView.as_view(),
        name='purchase_orders_create'
    ),
    path(
        'purchase-orders/<uuid:pk>/',
        views.PurchaseOrderCreateView.as_view(),
        name='purchase_orders_detail'
    ),
    path(
        'purchase-orders/<uuid:pk>/delete/',
        views.delete_purchase_order_view,
        name='purchase_orders_delete'
    ),
    
    # Purchase Orders - API endpoints
    path(
        'api/purchase-orders/autosave/',
        views.autosave_purchase_order_view,
        name='purchase_orders_autosave'
    ),
    path(
        'api/purchase-orders/<uuid:pk>/pdf/',
        views.PurchaseOrderPDFView.as_view(),
        name='purchase_orders_pdf'
    ),
    path(
        'api/purchase-orders/<uuid:pk>/email/',
        views.PurchaseOrderEmailView.as_view(),
        name='purchase_orders_email'
    ),
    path(
        'api/supplier-quotes/extract/',
        views.extract_supplier_quote_data_view,
        name='supplier_quotes_extract'
    ),
    
    # Delivery Receipts - REST endpoints
    path(
        'delivery-receipts/',
        views.DeliveryReceiptListView.as_view(),
        name='delivery_receipts_list'
    ),
    path(
        'delivery-receipts/<uuid:pk>/',
        views.DeliveryReceiptCreateView.as_view(),
        name='delivery_receipts_create'
    ),
    
    # Delivery Receipts - API endpoints
    path(
        'api/delivery-receipts/process/',
        views.process_delivery_receipt_view,
        name='delivery_receipts_process'
    ),
    
    # Stock Management - REST endpoints
    path(
        'stock/',
        views.StockListView.as_view(),
        name='stock_list'
    ),
    path(
        'stock/create/',
        views.StockCreateView.as_view(),
        name='stock_create'
    ),
    path(
        'stock/use/',
        views.UseStockView.as_view(),
        name='stock_use'
    ),
    
    # Stock Management - API endpoints
    path(
        'api/stock/create/',
        views.create_stock_api_view,
        name='stock_create_api'
    ),
    path(
        'api/stock/consume/',
        views.consume_stock_api_view,
        name='stock_consume_api'
    ),
    path(
        'api/stock/<uuid:stock_id>/deactivate/',
        views.deactivate_stock_api_view,
        name='stock_deactivate_api'
    ),
    path(
        'api/stock/search/',
        views.search_available_stock_api,
        name='stock_search_api'
    ),
]