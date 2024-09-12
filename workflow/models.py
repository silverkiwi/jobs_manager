import uuid
from typing import Union, List, Optional, Dict

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords  # type: ignore


class Job(models.Model):
    id: models.UUIDField = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    name: models.CharField = models.CharField(max_length=100)
    STATUS_CHOICES: List[tuple[str, str]] = [
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

    client_name: models.CharField = models.CharField(max_length=100)
    order_number: models.CharField = models.CharField(
        max_length=100, null=True, blank=True
    )
    contact_person: models.CharField = models.CharField(max_length=100)
    contact_phone: models.CharField = models.CharField(max_length=15)
    job_number: models.CharField = models.CharField(
        max_length=100, null=True, blank=True
    )
    description: models.TextField = models.TextField()
    date_created: models.DateTimeField = models.DateTimeField(default=timezone.now)
    last_updated: models.DateTimeField = models.DateTimeField(auto_now=True)
    status: models.CharField = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default="quoting"
    )
    parent: Optional["Job"] = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="revisions",
        on_delete=models.SET_NULL,
    )
    paid: bool = models.BooleanField(default=False)
    history: HistoricalRecords = HistoricalRecords()

    def __str__(self) -> str:
        return f"{self.client_name} - {self.job_number or self.order_number}"

    def get_display_name(self) -> str:
        return self.name


class JobPricing(models.Model):
    id: models.UUIDField = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    job: models.ForeignKey = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="job_pricings"
    )
    pricing_type: models.CharField = models.CharField(
        max_length=10, choices=[("fixed", "Fixed"), ("hourly", "Hourly")]
    )


class TimeEntry(models.Model):
    id: models.UUIDField = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    job: models.ForeignKey = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="time_entries"
    )
    job_pricing: models.ForeignKey = models.ForeignKey(
        JobPricing,
        on_delete=models.CASCADE,
        related_name="time_entries",
        null=True,
        blank=True,
    )
    staff: models.ForeignKey = models.ForeignKey(
        "Staff", on_delete=models.CASCADE, related_name="time_entries"
    )
    date: models.DateField = models.DateField()
    minutes: models.DecimalField = models.DecimalField(
        max_digits=5, decimal_places=2
    )  # Duration in minutes
    note: models.TextField = models.TextField(blank=True, null=True)
    is_billable: models.BooleanField = models.BooleanField(default=True)
    wage_rate: models.DecimalField = models.DecimalField(
        max_digits=10, decimal_places=2
    )
    charge_out_rate: models.DecimalField = models.DecimalField(
        max_digits=10, decimal_places=2
    )

    @property
    def cost(self) -> float:
        return self.hours * self.wage_rate

    @property
    def revenue(self) -> float:
        return self.hours * self.charge_out_rate

    @property
    def hours(self) -> float:
        return self.minutes / 60

    def __str__(self) -> str:
        return f"{self.staff.get_display_name()} {self.job.name} on {self.date}"


class AdjustmentEntry(models.Model):
    """For when costs are manually added to a job"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_pricing = models.ForeignKey(
        JobPricing, on_delete=models.CASCADE, related_name="adjustment_entries"
    )
    description = models.CharField(max_length=200, null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)


class StaffManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("wage_rate", 0)
        extra_fields.setdefault("charge_out_rate", 0)
        return self.create_user(email, password, **extra_fields)


class Staff(AbstractBaseUser, PermissionsMixin):
    id: uuid.UUID = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    email: str = models.EmailField(unique=True)
    first_name: str = models.CharField(max_length=30)
    last_name: str = models.CharField(max_length=30)
    preferred_name: Optional[str] = models.CharField(
        max_length=30, blank=True, null=True
    )
    wage_rate: float = models.DecimalField(max_digits=10, decimal_places=2)
    charge_out_rate: float = models.DecimalField(max_digits=10, decimal_places=2)
    ims_payroll_id: str = models.CharField(max_length=100, unique=True)
    is_active: bool = models.BooleanField(default=True)
    is_staff: bool = models.BooleanField(default=False)
    date_joined: timezone.datetime = models.DateTimeField(default=timezone.now)
    history: HistoricalRecords = HistoricalRecords()

    objects: "StaffManager" = StaffManager()

    USERNAME_FIELD: str = "email"
    REQUIRED_FIELDS: List[str] = [
        "first_name",
        "last_name",
        "wage_rate",
        "charge_out_rate",
        "ims_payroll_id",
    ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def get_display_name(self) -> str:
        return self.preferred_name or self.first_name
