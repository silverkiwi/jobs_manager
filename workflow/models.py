import uuid
from typing import Dict, List, Any

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords


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
    parent: models.ForeignKey = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="revisions",
        on_delete=models.SET_NULL,
    )
    paid: models.BooleanField = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self) -> str:
        job_or_order = f"{self.job_number or self.order_number}"
        return f"{self.client_name} - {self.name} - {job_or_order} - ({self.status})"

    @property
    def _history_user(self) -> Any:
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value: Any) -> None:
        self.changed_by = value


class JobPricing(models.Model):
    PRICING_TYPE_CHOICES = [
        ("estimate", "Estimate"),
        ("actual", "Actual"),
        ("quote", "Quote"),
        ("invoice", "Invoice"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="job_pricings")
    pricing_type = models.CharField(max_length=10, choices=PRICING_TYPE_CHOICES)

    @property
    def profit(self):
        return self.total_revenue() - self.total_cost()

    @property
    def total_cost(self):
        return (
            sum(entry.cost for entry in self.time_entries.all())
            + sum(entry.cost for entry in self.material_entries.all())
            + sum(entry.cost for entry in self.adjustment_entries.all())
        )

    @property
    def total_revenue(self):
        return (
            sum(entry.revenue for entry in self.time_entries.all())
            + sum(entry.revenue for entry in self.material_entries.all())
            + sum(entry.revenue for entry in self.adjustment_entries.all())
        )

    def __str__(self):
        return f"{self.job} - {self.pricing_type}"


class MaterialEntry(models.Model):
    """Materials, e.g. sheets"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_pricing = models.ForeignKey(
        JobPricing, on_delete=models.CASCADE, related_name="material_entries"
    )
    description = models.CharField(max_length=200)
    cost_price = models.DecimalField(
        max_digits=10, decimal_places=2
    )  # Changed from FloatField to DecimalField
    sale_price = models.DecimalField(
        max_digits=10, decimal_places=2
    )  # Changed from FloatField to DecimalField
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2
    )  # Changed from FloatField to DecimalField

    @property
    def cost(self):
        return self.cost_price * self.quantity

    @property
    def revenue(self):
        return self.sale_price * self.quantity


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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    preferred_name = models.CharField(max_length=30, blank=True, null=True)
    wage_rate = models.DecimalField(max_digits=10, decimal_places=2)
    charge_out_rate = models.DecimalField(max_digits=10, decimal_places=2)
    ims_payroll_id = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()

    objects = StaffManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [
        "first_name",
        "last_name",
        "wage_rate",
        "charge_out_rate",
        "ims_payroll_id",
    ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_display_name(self):
        return self.preferred_name or self.first_name


class TimeEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="time_entries")
    job_pricing = models.ForeignKey(
        JobPricing,
        on_delete=models.CASCADE,
        related_name="time_entries",
        null=True,
        blank=True,
    )
    staff = models.ForeignKey(
        "Staff", on_delete=models.CASCADE, related_name="time_entries"
    )
    date = models.DateField()
    minutes = models.DecimalField(max_digits=5, decimal_places=2)  # Duration in minutes
    note = models.TextField(blank=True, null=True)
    is_billable = models.BooleanField(default=True)
    wage_rate = models.DecimalField(max_digits=10, decimal_places=2)
    charge_out_rate = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def cost(self):
        return self.hours * self.wage_rate

    @property
    def revenue(self):
        return self.hours * self.charge_out_rate

    @property
    def hours(self):
        return self.minutes / 60

    def __str__(self):
        return f"{self.staff.get_display_name()} {self.job.name} on {self.date}"
