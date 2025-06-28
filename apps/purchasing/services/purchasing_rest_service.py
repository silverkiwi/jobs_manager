import logging
from decimal import Decimal
from typing import Any, Dict, List
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction

from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine, Stock

logger = logging.getLogger(__name__)


class PurchasingRestService:
    """Service layer for purchasing REST operations."""

    @staticmethod
    def list_purchase_orders() -> List[Dict[str, Any]]:
        pos = PurchaseOrder.objects.all().order_by("-created_at")
        return [
            {
                "id": str(po.id),
                "po_number": po.po_number,
                "status": po.status,
                "supplier": po.supplier.name if po.supplier else "",
            }
            for po in pos
        ]

    @staticmethod
    def create_purchase_order(data: Dict[str, Any]) -> PurchaseOrder:
        if not data.get("supplier_id"):
            raise ValueError("supplier_id is required")

        po = PurchaseOrder.objects.create(
            supplier_id=data["supplier_id"],
            reference=data.get("reference", ""),
            order_date=data.get("order_date", timezone.now().date()),
            expected_delivery=data.get("expected_delivery"),
        )

        for line in data.get("lines", []):
            PurchaseOrderLine.objects.create(
                purchase_order=po,
                job_id=line.get("job_id"),
                description=line.get("description", ""),
                quantity=Decimal(str(line.get("quantity", 0))),
                unit_cost=Decimal(str(line.get("unit_cost", 0))) if line.get("unit_cost") is not None else None,
                price_tbc=line.get("price_tbc", False),
                item_code=line.get("item_code"),
            )
        return po

    @staticmethod
    def update_purchase_order(po_id: str, data: Dict[str, Any]) -> PurchaseOrder:
        po = get_object_or_404(PurchaseOrder, id=po_id)
        for field in ["reference", "expected_delivery", "status"]:
            if field in data:
                setattr(po, field, data[field])
        po.save()

        for line_data in data.get("lines", []):
            if not line_data.get("id"):
                continue
            line = get_object_or_404(PurchaseOrderLine, id=line_data["id"], purchase_order=po)
            if "item_code" in line_data:
                line.item_code = line_data["item_code"]
            line.save()
        return po

    @staticmethod
    def list_stock() -> List[Dict[str, Any]]:
        items = Stock.objects.filter(is_active=True)
        return [
            {
                "id": str(s.id),
                "description": s.description,
                "quantity": float(s.quantity),
                "unit_cost": float(s.unit_cost),
            }
            for s in items
        ]

