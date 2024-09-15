# workflow/models/job_pricing.py
import uuid

from django.db import models
from workflow.models import Job
from workflow.enums import JobPricingType, JobPricingStage


class JobPricing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='pricings')
    pricing_stage = models.CharField(
        max_length=20,
        choices=JobPricingStage.choices,
        default=JobPricingStage.ESTIMATE,
        help_text="Stage of the job pricing (estimate, quote, or reality).",
    )
    pricing_type = models.CharField(
        max_length=20,
        choices=JobPricingType.choices,
        default=JobPricingType.TIME_AND_MATERIALS,
        help_text="Type of pricing for the job (fixed price or time and materials).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_cost(self):
        total_time_cost = sum(entry.cost for entry in self.time_entries.all())
        total_material_cost = sum(entry.cost for entry in self.material_entries.all())
        total_adjustment_cost = sum(entry.cost for entry in self.adjustment_entries.all())
        return total_time_cost + total_material_cost + total_adjustment_cost

    @property
    def total_revenue(self):
        total_time_revenue = sum(entry.revenue or 0 for entry in self.time_entries.all())
        total_material_revenue = sum(entry.revenue or 0 for entry in self.material_entries.all())
        total_adjustment_revenue = sum(entry.revenue or 0 for entry in self.adjustment_entries.all())
        return total_time_revenue + total_material_revenue + total_adjustment_revenue

    def __str__(self):
        return f"{self.job.name} - {self.get_pricing_stage_display()} ({self.get_pricing_type_display()})"
