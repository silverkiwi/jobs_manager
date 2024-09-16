# time_entry.py

import uuid
from decimal import Decimal

from django.db import models

from workflow.models import Staff  # Import the necessary models


class TimeEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_pricing = models.ForeignKey(
        "JobPricing",
        on_delete=models.CASCADE,
        related_name="time_entries",
        null=True,
        blank=True,
    )
    staff = models.ForeignKey(
        Staff, on_delete=models.CASCADE, related_name="time_entries"
    )
    date = models.DateField()
    minutes = models.DecimalField(max_digits=5, decimal_places=2)  # Duration in minutes
    note = models.TextField(blank=True, null=True)
    is_billable = models.BooleanField(default=True)
    wage_rate = models.DecimalField(max_digits=10, decimal_places=2)
    charge_out_rate = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def cost(self) -> Decimal:
        return self.hours * self.wage_rate

    @property
    def revenue(self) -> Decimal:
        return self.hours * self.charge_out_rate

    @property
    def hours(self) -> Decimal:
        return self.minutes / Decimal(60)

    def __str__(self):
        staff_name = self.staff.get_display_name()
        job_name = self.job_pricing.job.name if self.job_pricing else "No Job"
        time_date = self.date.strftime("%Y-%m-%d")
        return f"{staff_name} - {job_name} on {time_date}"
