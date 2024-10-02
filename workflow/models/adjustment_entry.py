# adjustment_entry.py

import uuid

from django.db import models


class AdjustmentEntry(models.Model):
    """For when costs are manually added to a job"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_pricing = models.ForeignKey(
        "JobPricing",  # Use string reference to avoid circular import
        on_delete=models.CASCADE,
        related_name="adjustment_entries",
    )
    description = models.CharField(max_length=200, null=True, blank=True)
    cost_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    price_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    comments = models.CharField(max_length=200, null=True, blank=True) # Freetext internal note

    def __str__(self):
        return f"Adjustment for {self.job_pricing.job.name} - {self.description or 'No Description'}"
