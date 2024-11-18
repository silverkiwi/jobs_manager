import datetime
import uuid
from typing import Dict, List
import logging

from django.db import models, transaction
from django.apps import apps
from django.utils import timezone
from simple_history.models import HistoricalRecords  # type: ignore

logger = logging.getLogger(__name__)

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
        "Client",
        on_delete=models.SET_NULL,  # Option to handle if a client is deleted
        null=True,
        related_name="jobs",  # Allows reverse lookup of jobs for a client
    )
    order_number: str = models.CharField(
        max_length=100, null=True, blank=True
    )  # type: ignore
    contact_person: str = models.CharField(max_length=100)  # type: ignore
    contact_phone: str = models.CharField(max_length=15, null=True, blank=True)  # type: ignore
    job_number = models.IntegerField(null=False, blank=False, unique=True)  # Job 1234
    material_gauge_quantity: str = models.TextField(blank=True, null=True)  # type: ignore
    description: str = models.TextField(blank=True, null=True)  # type: ignore
    quote_acceptance_date: datetime.datetime = models.DateTimeField(null=True, blank=True)  # type: ignore
    delivery_date = models.DateField(null=True, blank=True)  # type: ignore
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
    shop_job = models.BooleanField(default=False, null=False, blank=False)  # type: ignore  # Essentially true if and only if client_id is None

    job_is_valid = models.BooleanField(default=False)  # type: ignore
    paid: bool = models.BooleanField(default=False)  # type: ignore

    # Direct relationships for estimate, quote, reality
    latest_estimate_pricing = models.OneToOneField(
        'JobPricing',
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name='latest_estimate_for_job'
    )

    latest_quote_pricing = models.OneToOneField(
        'JobPricing',
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name='latest_quote_for_job'
    )

    latest_reality_pricing = models.OneToOneField(
        'JobPricing',
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name='latest_reality_for_job'
    )

    archived_pricings = models.ManyToManyField(
        "JobPricing",
        related_name="archived_pricings_for_job",
        blank=True,
    )

    history: HistoricalRecords = HistoricalRecords()

    def __str__(self) -> str:
        client_name = self.client.name if self.client else "No Client"
        return f"{client_name} - {self.job_number}"

    def get_display_name(self) -> str:
        return f"Job: {self.job_number}"  # type: ignore

    def save(self, *args, **kwargs):
        # Step 1: Check if this is a new instance (based on `self._state.adding`)
        if self._state.adding:
            # Step 2: Generate a unique job number if it's not set yet
            if not self.job_number:
                self.job_number = self.generate_unique_job_number()

            # Lazy import JobPricing using Django's apps.get_model()
            JobPricing = apps.get_model('workflow', 'JobPricing')

            # Step 3: Create the initial JobPricing instances for estimate, quote, and reality
            logger.debug("Creating related JobPricing entries.")
            estimate_pricing = JobPricing.objects.create(pricing_stage="estimate")
            quote_pricing = JobPricing.objects.create(pricing_stage="quote")
            reality_pricing = JobPricing.objects.create(pricing_stage="reality")
            logger.debug("Initial pricings created successfully.")

            # Step 4: Link the JobPricing objects to this job
            self.latest_estimate_pricing = estimate_pricing
            self.latest_quote_pricing = quote_pricing
            self.latest_reality_pricing = reality_pricing

        # Step 5: Save the Job to persist everything, including relationships
        logger.debug(f"Saving job with job number: {self.job_number}")
        super(Job, self).save(*args, **kwargs)

    @staticmethod
    def generate_unique_job_number():
        with transaction.atomic():
            last_job = Job.objects.select_for_update().order_by("-job_number").first()
            if last_job and last_job.job_number:
                return last_job.job_number + 1
            return 1  # Start numbering from 1 if there are no existing records
