import logging
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Max

from apps.purchasing.models import Stock
from apps.job.models import Job, CostSet, CostLine

logger = logging.getLogger(__name__)


def _get_actual_cost_set(job: Job) -> CostSet:
    cost_set = job.get_latest("actual")
    if cost_set:
        return cost_set

    max_rev = (
        CostSet.objects.filter(job=job, kind="actual").aggregate(Max("rev"))
    ).get("rev__max") or 0
    cost_set = CostSet.objects.create(job=job, kind="actual", rev=max_rev + 1)
    job.set_latest("actual", cost_set)
    return cost_set


def consume_stock(item: Stock, job: Job, qty: Decimal, user: Any) -> CostLine:
    if qty <= 0:
        raise ValueError("Quantity must be positive")

    with transaction.atomic():
        if qty > item.quantity:
            raise ValueError("Quantity used exceeds available stock")

        item.quantity -= qty
        if item.quantity <= 0:
            item.is_active = False
            item.save(update_fields=["quantity", "is_active"])
        else:
            item.save(update_fields=["quantity"])

        unit_rev = item.unit_cost * (1 + item.retail_rate)
        cost_set = _get_actual_cost_set(job)
        cost_line = CostLine.objects.create(
            cost_set=cost_set,
            kind="material",
            desc=f"Consumed: {item.description}",
            quantity=qty,
            unit_cost=item.unit_cost,
            unit_rev=unit_rev,
            ext_refs={"stock_id": str(item.id)},
            meta={"consumed_by": getattr(user, "id", None)},
        )

    logger.info(
        "Consumed %s of stock %s for job %s", qty, item.id, job.id
    )
    return cost_line
