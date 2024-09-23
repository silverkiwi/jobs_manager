# workflow/models/job_pricing.py
import uuid

from django.db import models, transaction

from workflow.enums import JobPricingStage, JobPricingType
from workflow.models import Job


class JobPricing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_pricing_number = models.IntegerField(unique=True, null=False, blank=False)

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
    job_pricing_number = models.IntegerField(null=False, blank=False, unique=True)  # For Quote #123

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @staticmethod
    def generate_unique_job_pricing_number():
        with transaction.atomic():
            last_pricing = JobPricing.objects.select_for_update().order_by('-job_pricing_number').first()
            if last_pricing and last_pricing.job_pricing_number:
                return last_pricing.job_pricing_number + 1
            return 1  # Start numbering from 1 if there are no existing records

    @property
    def total_cost(self):
        total_time_cost = sum(entry.cost for entry in self.time_entries.all())
        total_material_cost = sum(entry.cost for entry in self.material_entries.all())
        total_adjustment_cost = sum(
            entry.cost for entry in self.adjustment_entries.all()
        )
        return total_time_cost + total_material_cost + total_adjustment_cost

    @property
    def total_revenue(self):
        total_time_revenue = sum(
            entry.revenue or 0 for entry in self.time_entries.all()
        )
        total_material_revenue = sum(
            entry.revenue or 0 for entry in self.material_entries.all()
        )
        total_adjustment_revenue = sum(
            entry.revenue or 0 for entry in self.adjustment_entries.all()
        )
        return total_time_revenue + total_material_revenue + total_adjustment_revenue

    def __str__(self):
        return f"{self.job.name} - {self.get_pricing_stage_display()} ({self.get_pricing_type_display()})"


    def save(self, *args, **kwargs):
        if not self.job_pricing_number:
            self.job_pricing_number = self.generate_unique_job_pricing_number()
        super(JobPricing, self).save(*args, **kwargs)

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
