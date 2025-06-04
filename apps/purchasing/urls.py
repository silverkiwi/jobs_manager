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
]