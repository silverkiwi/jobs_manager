import uuid

from django.db import models

from workflow.models.job import Job


class JobPricingType(models.Model):
    id: models.UUIDField = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    job: Job = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="job_pricings"
    )  # type: ignore
    pricing_type: models.CharField = models.CharField(
        max_length=10, choices=[("fixed", "Fixed"), ("hourly", "Hourly")]
    )
