# workflow/models.py

from django.db import models
from workflow.models import Job
from workflow.enums import JobPricingType


class JobPricing(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='pricings')
    estimate_type = models.CharField(
        max_length=20,
        choices=JobPricingType.choices,
        default=JobPricingType.TIME_AND_MATERIALS,
        help_text="Type of estimate for the job pricing.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.job.name} - {self.get_estimate_type_display()}"
