"""REST views for purchasing module."""
import logging
from decimal import Decimal
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from apps.workflow.api.xero.xero import get_xero_items
from apps.purchasing.models import Stock
from apps.job.models import Job
from apps.purchasing.services.stock_service import consume_stock
from apps.purchasing.services.purchasing_rest_service import PurchasingRestService

logger = logging.getLogger(__name__)


class XeroItemList(APIView):
    """Return list of items from Xero."""

    def get(self, request):
        items = cache.get("xero_items")
        if items is None:
            items = get_xero_items()
            cache.set("xero_items", items, 300)
        data = [
            {"id": getattr(i, "item_id", None), "code": getattr(i, "code", ""), "name": getattr(i, "name", "")}
            for i in items
        ]
        return Response(data)


class PurchaseOrderListCreateRestView(APIView):
    def get(self, request):
        return Response(PurchasingRestService.list_purchase_orders())

    def post(self, request):
        po = PurchasingRestService.create_purchase_order(request.data)
        return Response({"id": str(po.id), "po_number": po.po_number}, status=status.HTTP_201_CREATED)


class PurchaseOrderPatchRestView(APIView):
    def patch(self, request, pk):
        po = PurchasingRestService.update_purchase_order(pk, request.data)
        return Response({"id": str(po.id), "status": po.status})


class DeliveryReceiptRestView(APIView):
    def post(self, request):
        purchase_order_id = request.data.get("purchase_order_id")
        allocations = request.data.get("allocations", {})
        from apps.purchasing.services.delivery_receipt_service import process_delivery_receipt

        process_delivery_receipt(purchase_order_id, allocations)
        return Response({"success": True})


class StockListRestView(APIView):
    def get(self, request):
        return Response(PurchasingRestService.list_stock())


class StockConsumeRestView(APIView):
    def post(self, request, stock_id):
        job_id = request.data.get("job_id")
        qty = request.data.get("quantity")
        if not all([job_id, qty]):
            return Response({"error": "Missing data"}, status=status.HTTP_400_BAD_REQUEST)

        job = get_object_or_404(Job, id=job_id)
        item = get_object_or_404(Stock, id=stock_id)
        try:
            qty_dec = Decimal(str(qty))
        except Exception:
            return Response({"error": "Invalid quantity"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            consume_stock(item, job, qty_dec, request.user)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": True})

