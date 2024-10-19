# workflow/models/job_pricing.py
import uuid
from decimal import Decimal

from django.db import models, transaction

from workflow.enums import JobPricingStage, JobPricingType
from workflow.models import Job


def decimal_to_float(value):
    return float(value) if isinstance(value, Decimal) else value


class JobPricing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="pricings")
    pricing_stage = models.CharField(
        max_length=20,
        choices=JobPricingStage.choices,
        default=JobPricingStage.ESTIMATE,
        help_text="Stage of the job pricing (estimate, quote, or reality).",
    )
    pricing_type = models.CharField(
        max_length=20,
        choices=JobPricingType.choices,
        default=JobPricingType.TIME_AND_MATERIALS,
        help_text="Type of pricing for the job (fixed price or time and materials).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def material_entries(self):
        """Returns all MaterialEntries related to this JobPricing"""
        return self.materialentries_set.all()

    @property
    def time_entries(self):
        """Returns all TimeEntries related to this JobPricing"""
        return self.timeentries_set.all()

    @property
    def adjustment_entries(self):
        """Returns all AdjustmentEntries related to this JobPricing"""
        return self.adjustmententries_set.all()

    @property
    def total_time_cost(self):
        """Calculate the total cost for all time entries."""
        return sum(entry.cost for entry in self.time_entries.all())

    @property
    def total_time_revenue(self):
        """Calculate the total revenue for all time entries."""
        return sum(entry.revenue for entry in self.time_entries.all())  # Assuming 'revenue' field exists

    @property
    def total_material_cost(self):
        """Calculate the total cost for all material entries."""
        return sum(entry.unit_cost * entry.quantity for entry in self.material_entries.all())

    @property
    def total_material_revenue(self):
        """Calculate the total revenue for all material entries."""
        return sum(entry.unit_revenue * entry.quantity for entry in self.material_entries.all())

    @property
    def total_adjustment_cost(self):
        """Calculate the total cost for all adjustment entries."""
        return sum(entry.cost_adjustment for entry in self.adjustment_entries.all())

    @property
    def total_adjustment_revenuet(self):
        """Calculate the total cost for all adjustment entries."""
        return sum(entry.price_adjustment for entry in self.adjustment_entries.all())

    @property
    def total_cost(self):
        """Calculate the total cost including time, materials, and adjustments."""
        return self.total_time_cost + self.total_material_cost + self.total_adjustment_cost

    @property
    def total_revenue(self):
        """Calculate the total cost including time, materials, and adjustments."""
        return self.total_time_revenue + self.total_material_revenue + self.total_adjustment_revenue

    def extract_pricing_data(self):
        """Used for passing pricing data into HTML templates."""
        time_entries = [
                {
                    'description': entry.description,
                    'items': decimal_to_float(entry.items),
                    'mins_per_item': decimal_to_float(entry.mins_per_item),
                    'wage_rate': decimal_to_float(entry.wage_rate),
                    'charge_out_rate': decimal_to_float(entry.charge_out_rate)
                }
                for entry in self.time_entries.all()  # Reverse lookup assuming related_name='time_entries'
            ]
        material_entries = [
                {
                    'item_code': entry.item_code,
                    'description': entry.description,
                    'quantity': decimal_to_float(entry.quantity),
                    'cost_price': decimal_to_float(entry.unit_cost),
                    'retail_price': decimal_to_float(entry.unit_revenue),
                    'comments': entry.comments
                }
                for entry in self.material_entries.all()  # Reverse lookup assuming related_name='material_entries'
            ]
        adjustment_entries = [
                {
                    'description': entry.description,
                    'cost_adjustment': decimal_to_float(entry.cost_adjustment),
                    'price_adjustment': decimal_to_float(entry.price_adjustment),
                    'comments': entry.comments
                }
                for entry in self.adjustment_entries.all()  # Reverse lookup assuming related_name='adjustment_entries'
            ]
        pricing_entries = {
            'time': time_entries,
            'material': material_entries,
            'adjustment': adjustment_entries
        }
        return pricing_entries

    def __str__(self):
        return f"{self.job.name} - {self.get_pricing_stage_display()} ({self.get_pricing_type_display()})"


# Not implemented yet - just putting this here to add in future design thinking
def snapshot_and_add_time_entry(job_pricing, hours_worked):
    # Create a snapshot of the current JobPricing before modifying it
    snapshot_pricing = JobPricing.objects.create(
        job=job_pricing.job,
        pricing_stage=job_pricing.pricing_stage,
        pricing_type=job_pricing.pricing_type,
        created_at=job_pricing.created_at,
        updated_at=job_pricing.updated_at,
    )

    # Copy related time entries to the snapshot
    for time_entry in job_pricing.time_entries.all():
        TimeEntry.objects.create(job_pricing=snapshot_pricing, hours_worked=time_entry.hours_worked)

    # Copy related materials and adjustments if necessary
    for material_entry in job_pricing.material_entries.all():
        MaterialEntry.objects.create(job_pricing=snapshot_pricing, material=material_entry.material,
                                     quantity=material_entry.quantity)

    for adjustment_entry in job_pricing.adjustment_entries.all():
        AdjustmentEntry.objects.create(job_pricing=snapshot_pricing, description=adjustment_entry.description,
                                       amount=adjustment_entry.amount)

    # Now, add the new time entry to the current (updated) JobPricing
    TimeEntry.objects.create(job_pricing=job_pricing, hours_worked=hours_worked)

    return snapshot_pricing  # Return the snapshot to track it if needed


class QuotePricing(JobPricing):
    quote_is_finished = models.BooleanField(default=False)  # Locks the quote when true
    date_quote_submitted = models.DateField(null=True, blank=True)  # Date the quote was submitted to client
    quote_number = models.IntegerField(null=False, blank=False, unique=True)  # For Quote #123

    @staticmethod
    def generate_unique_quote_number():
        with transaction.atomic():
            last_pricing = JobPricing.objects.select_for_update().order_by('-quote_number').first()
            if last_pricing and last_pricing.quote_number:
                return last_pricing.quote_number + 1
            return 1  # Start numbering from 1 if there are no existing records
