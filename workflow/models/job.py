import datetime
import uuid
from typing import Dict, List

from django.db import models, transaction
from django.utils import timezone
from simple_history.models import HistoricalRecords  # type: ignore


class Job(models.Model):
    name = models.CharField(max_length=100, null=False, blank=False)  # type: ignore

    id: uuid.UUID = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )  # type: ignore

    JOB_STATUS_CHOICES: List[tuple[str, str]] = [
        ("quoting", "Quoting"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("in_progress", "In Progress"),
        ("on_hold", "On Hold"),
        ("special", "Special"),
        ("completed", "Completed"),
        ("archived", "Archived"),
    ]

    STATUS_TOOLTIPS: Dict[str, str] = {
        "quoting": "The quote is currently being prepared.",
        "approved": "The quote has been approved, but work hasn't started yet.",
        "rejected": "The quote was declined.",
        "in_progress": "Work has started on this job.",
        "on_hold": "The job is on hold, possibly awaiting materials.",
        "special": "Shop jobs, upcoming shutdowns, etc.",
        "completed": "Work has finished on this job.",
        "archived": "The job has been paid for and picked up.",
    }

    client = models.ForeignKey(
        'Client',
        on_delete=models.SET_NULL,  # Option to handle if a client is deleted
        null=True,
        related_name='jobs'  # Allows reverse lookup of jobs for a client
    )
    order_number: str = models.CharField(
        max_length=100, null=True, blank=True
    )  # type: ignore
    contact_person: str = models.CharField(max_length=100)  # type: ignore
    contact_phone: str = models.CharField(max_length=15)  # type: ignore
    job_number = models.IntegerField(null=False, blank=False, unique=True)  # Job 1234
    description: str = models.TextField()  # type: ignore
    quote_acceptance_date: datetime.datetime = models.DateTimeField(null=True, blank=True)  # type: ignore
    delivery_date: datetime.datetime = models.DateTimeField(null=True, blank=True)  # type: ignore
    date_created: datetime.datetime = models.DateTimeField(
        default=timezone.now
    )  # type: ignore
    last_updated: datetime.datetime = models.DateTimeField(
        auto_now=True
    )  # type: ignore
    status: str = models.CharField(
        max_length=30, choices=JOB_STATUS_CHOICES, default="quoting"
    )  # type: ignore
    # Decided not to bother with parent for now since we don't have a hierarchy of jobs.
    # Can be restored.  Would also provide an alternative to historical records for tracking changes.
    # parent: models.ForeignKey = models.ForeignKey(
    #     "self",
    #     null=True,
    #     blank=True,
    #     related_name="revisions",
    #     on_delete=models.SET_NULL,
    # )
    job_is_valid = models.BooleanField(default=False)  # type: ignore
    paid: bool = models.BooleanField(default=False)  # type: ignore
    history: HistoricalRecords = HistoricalRecords()


    def __str__(self) -> str:
        client_name = self.client.name if self.client else "No Client"
        return f"{client_name} - {self.job_number}"

    def get_display_name(self) -> str:
        return f"Job: {self.job_number}"  # type: ignore

    def save(self, *args, **kwargs):
        if not self.job_number:
            self.job_number = self.generate_unique_job_number()
        super(Job, self).save(*args, **kwargs)

    @property
    def estimate_pricing(self):
        """Returns the estimate JobPricing related to this job."""
        return self.pricings.filter(pricing_stage='estimate').first()

    @property
    def quote_pricing(self):
        """Returns the quote JobPricing related to this job."""
        return self.pricings.filter(pricing_stage='quote').first()

    @property
    def reality_pricing(self):
        """Returns the reality JobPricing related to this job."""
        return self.pricings.filter(pricing_stage='reality').first()


    @staticmethod
    def generate_unique_job_number():
        with transaction.atomic():
            last_job = Job.objects.select_for_update().order_by('-job_number').first()
            if last_job and last_job.job_number:
                return last_job.job_number + 1
            return 1  # Start numbering from 1 if there are no existing records
