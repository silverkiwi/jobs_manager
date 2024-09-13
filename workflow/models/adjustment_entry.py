import decimal
import uuid

from django.db import models

from workflow.models import JobPricing


class AdjustmentEntry(models.Model):
    """For when costs are manually added to a job"""

    id: uuid.UUID = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )  # type: ignore
    job_pricing: models.ForeignKey = models.ForeignKey(
        JobPricing, on_delete=models.CASCADE, related_name="adjustment_entries"
    )
    description: str = models.CharField(
        max_length=200, null=True, blank=True
    )  # type: ignore
    cost: decimal.Decimal = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0
    )  # type: ignore
    revenue: decimal.Decimal = models.DecimalField(
        max_digits=10, ecimal_places=2, default=0.0
    )  # type: ignore
