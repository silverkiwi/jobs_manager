import logging
from decimal import Decimal
from typing import Any, Dict, List

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.client.models import Supplier
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

        supplier = get_object_or_404(Supplier, id=data["supplier_id"])

        po = PurchaseOrder.objects.create(
            supplier=supplier,
            reference=data.get("reference", ""),
            order_date=data.get("order_date", timezone.now().date()),
            expected_delivery=data.get("expected_delivery"),
        )

        for line in data.get("lines", []):
            price_tbc = bool(line.get("price_tbc", False))
            unit_cost = line.get("unit_cost")
            if price_tbc:
                unit_cost = None
            elif unit_cost is not None:
                unit_cost = Decimal(str(unit_cost))

            PurchaseOrderLine.objects.create(
                purchase_order=po,
                job_id=line.get("job_id"),
                description=line.get("description", ""),
                quantity=Decimal(str(line.get("quantity", 0)))
                if line.get("quantity") is not None
                else Decimal("0"),
                unit_cost=unit_cost,
                price_tbc=price_tbc,
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
            line_id = line_data.get("id")
            if not line_id:
                continue
            line = get_object_or_404(PurchaseOrderLine, id=line_id, purchase_order=po)

            if "description" in line_data:
                line.description = line_data["description"]
            if "item_code" in line_data:
                line.item_code = line_data["item_code"]
            if "quantity" in line_data:
                line.quantity = Decimal(str(line_data["quantity"]))
            if "unit_cost" in line_data:
                value = line_data["unit_cost"]
                line.unit_cost = Decimal(str(value)) if value is not None else None
            if "price_tbc" in line_data:
                line.price_tbc = bool(line_data["price_tbc"])

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

    @staticmethod
    def create_stock(data: dict) -> Stock:
        required = ["description", "quantity", "unit_cost", "source"]
        if not all(k in data for k in required):
            raise ValueError(f"Missing required fields")

        return Stock.objects.create(
            job=Stock.get_stock_holding_job(),
            description=data["description"],
            quantity=Decimal(str(data["quantity"])),
            unit_cost=Decimal(str(data["unit_cost"])),
            source=data["source"],
            notes=data.get("notes", ""),
            metal_type=data.get("metal_type", ""),
            alloy=data.get("alloy", ""),
            specifics=data.get("specifics", ""),
            location=data.get("location", ""),
            is_active=True,
        )
