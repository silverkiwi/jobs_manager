import uuid
from decimal import Decimal
from typing import Optional

from django.db import models

# from workflow.models import JobPricingType


class AdjustmentEntry(models.Model):
    """For when costs are manually added to a job"""

    id: uuid.UUID = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )  # type: ignore
    job_pricing_type = models.ForeignKey(
        "JobPricingType",
        on_delete=models.CASCADE,
        related_name="adjustment_entries",
    )  # type: ignore
    description: Optional[str] = models.CharField(
        max_length=200, null=True, blank=True
    )  # type: ignore
    cost: Decimal = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0
    )  # type: ignore
    revenue: Decimal = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0
    )  # type: ignore
