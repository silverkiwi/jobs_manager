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
        null=False,
        blank=False,
    )
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name="time_entries",
        help_text="The Staff member who did the work.  Null for estimates/quotes.",
        null=True,
        blank=True,  # Allow null and blank for estimates and quotes
    )
    date = models.DateField(
        null=True, blank=True,
        help_text="The date of the time entry.  Ie. the date the work was done.",
    )  # Allow null and blank for estimates and quotes.
    note = models.TextField(blank=True, null=True)
    is_billable = models.BooleanField(default=True,
                                      help_text="Set to false to avoid billing the client.  E.g. fixup work")
    wage_rate = models.DecimalField(max_digits=10, decimal_places=2)
    charge_out_rate = models.DecimalField(max_digits=10, decimal_places=2)

    description = models.TextField(
        blank=False, null=False, default=""
    )
    items = models.IntegerField(default=1)  # New field, defaulting to 1
    mins_per_item = models.DecimalField(
        max_digits=5, decimal_places=2, null=False, blank=True, default=0
    )  # items * mins_per_item = minutes

    @property
    def minutes(self) -> Decimal:
        # Calculate minutes dynamically
        if self.items and self.mins_per_item:
            return self.items * self.mins_per_item
        return Decimal(0)

    @property
    def hours(self) -> Decimal:
        # Use computed minutes to calculate hours
        return self.minutes / Decimal(60)

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
