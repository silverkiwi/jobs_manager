from django.urls import path
from apps.purchasing.views.purchasing_rest_views import (
    XeroItemList,
    PurchaseOrderListCreateRestView,
    PurchaseOrderPatchRestView,
    DeliveryReceiptRestView,
    StockListRestView,
    StockConsumeRestView,
)

urlpatterns = [
    path("xero-items/", XeroItemList.as_view(), name="xero_items_rest"),
    path("purchase-orders/", PurchaseOrderListCreateRestView.as_view(), name="purchase_orders_rest"),
    path("purchase-orders/<uuid:pk>/", PurchaseOrderPatchRestView.as_view(), name="purchase_order_patch_rest"),
    path("delivery-receipts/", DeliveryReceiptRestView.as_view(), name="delivery_receipts_rest"),
    path("stock/", StockListRestView.as_view(), name="stock_list_rest"),
    path("stock/<uuid:stock_id>/consume/", StockConsumeRestView.as_view(), name="stock_consume_rest"),
]
