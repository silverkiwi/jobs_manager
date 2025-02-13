import uuid

from django.db import models
from django.utils import timezone

from workflow.enums import QuoteStatus


class Quote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    xero_id = models.UUIDField(unique=True)
    job = models.OneToOneField(
        "Job", on_delete=models.CASCADE, related_name="quote", null=True, blank=True
    )
    client = models.ForeignKey("Client", on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(
        max_length=50, choices=QuoteStatus.choices, default=QuoteStatus.DRAFT
    )
    total_excl_tax = models.DecimalField(max_digits=10, decimal_places=2)
    total_incl_tax = models.DecimalField(max_digits=10, decimal_places=2)
    xero_last_modified = models.DateTimeField(null=True, blank=True)
    xero_last_synced = models.DateTimeField(default=timezone.now)
    online_url = models.URLField(null=True, blank=True)
    raw_json = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Quote ({self.status}) for Job {self.job.job_number}"
