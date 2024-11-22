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
    wage_rate_multiplier = models.DecimalField(blank=False, null=False, default=1, max_digits=5, decimal_places=2,
                                               help_text="Set to 2 for double time, etc.  Do not set to 0 unless you want the staff member to work for free.")

    description = models.TextField(
        blank=False, null=False, default=""
    )

    # DATA MODEL WARNING
    #
    # Estimates (and quotes) have items and minutes per item.
    # Actuals have hours.
    # Be careful.  Save writes the property minutes and hours for estimates, so you can rely on them.
    # This means that actuals do not have items or minutes_per_item

    hours = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=False)
    items = models.IntegerField(null=True, blank=True)  # For quotes/estimates
    minutes_per_item = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']  # Default ordering by creation time

    def save(self, *args, **kwargs):
        # Ensure minutes and hours stay consistent
        if self.items is not None and self.minutes_per_item is not None:
            total_minutes = self.items * self.minutes_per_item
            self.hours = total_minutes / Decimal(60)
        super().save(*args, **kwargs)

    @property
    def minutes(self) -> Decimal:
        """Compute minutes dynamically based on hours."""
        return self.hours * Decimal(60)

    @property
    def cost(self) -> Decimal:
        return self.hours * self.wage_rate

    @property
    def revenue(self) -> Decimal:
        return self.hours * self.charge_out_rate


    def __str__(self):
        staff_name = self.staff.get_display_name()
        job_name = self.job_pricing.job.name if self.job_pricing else "No Job"
        time_date = self.date.strftime("%Y-%m-%d")
        return f"{staff_name} - {job_name} on {time_date}"
