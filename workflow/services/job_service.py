from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from workflow.models import (
    AdjustmentEntry,
    CompanyDefaults,
    Job,
    JobPricing,
    MaterialEntry,
    TimeEntry,
)


def archive_and_reset_job_pricing(job_id):
    """Archives current pricing and resets to defaults based on company defaults."""
    job = Job.objects.get(id=job_id)

    # Fetch company defaults (assuming only one instance exists)
    company_defaults = CompanyDefaults.objects.first()
    if not company_defaults:
        raise ValueError("Company defaults are not configured.")

    with transaction.atomic():
        # Archive current pricing by marking them as historical
        current_pricings = JobPricing.objects.filter(job=job, is_historical=False)
        for pricing in current_pricings:
            pricing.is_historical = True
            pricing.save()

        # Create new pricing for "estimate"
        estimate_pricing = JobPricing.objects.create(
            job=job,
            pricing_stage="estimate",
        )
        estimate_pricing.time_entries.create(
            wage_rate=company_defaults.wage_rate,
            charge_out_rate=company_defaults.charge_out_rate,
        )

        # Create new pricing for "quote"
        quote_pricing = JobPricing.objects.create(
            job=job,
            pricing_stage="quote",
        )
        quote_pricing.adjustment_entries.create(
            cost_adjustment=company_defaults.time_markup,
            price_adjustment=company_defaults.charge_out_rate
            * company_defaults.time_markup,
        )

        # Create new pricing for "reality"
        reality_pricing = JobPricing.objects.create(
            job=job,
            pricing_stage="reality",
        )
        reality_pricing.material_entries.create(
            unit_cost=company_defaults.wage_rate,
            unit_revenue=company_defaults.charge_out_rate,
        )

        # Save references to the job
        job.latest_estimate_pricing = estimate_pricing
        job.latest_quote_pricing = quote_pricing
        job.latest_reality_pricing = reality_pricing
        job.save()


def get_job_with_pricings(job_id):
    """Fetches a Job object with all relevant latest JobPricing data,
    including time, material, and adjustment entries."""

    # Define pricing stages to reduce redundancy
    pricing_stages = [
        "latest_estimate_pricing",
        "latest_quote_pricing",
        "latest_reality_pricing",
    ]

    # Prefetch list to store all prefetch operations
    prefetch_list = []

    # Loop through each pricing stage to create Prefetch objects for pricing entries
    for stage in pricing_stages:
        # Prefetch time_entries with related staff
        prefetch_list.append(
            Prefetch(
                f"{stage}__time_entries",
                queryset=TimeEntry.objects.select_related("staff"),
            )
        )
        # Prefetch material_entries
        prefetch_list.append(
            Prefetch(f"{stage}__material_entries", queryset=MaterialEntry.objects.all())
        )
        # Prefetch adjustment_entries
        prefetch_list.append(
            Prefetch(
                f"{stage}__adjustment_entries", queryset=AdjustmentEntry.objects.all()
            )
        )

    # Get the job with the relevant prefetch operations for each pricing stage
    job = get_object_or_404(
        Job.objects.select_related("client").prefetch_related(*prefetch_list),
        id=job_id,
    )

    return job


def get_historical_job_pricings(job):
    """Fetch all historical (archived) revisions for the job."""
    # Fetch all archived pricings for the given job
    historical_pricings = job.archived_pricings.all().order_by("-created_at")
    return list(historical_pricings)


# Utility to fetch the latest pricing per stage
def get_latest_job_pricings(job):
    """Fetches the latest revision of each pricing stage for the given job."""
    return {
        "estimate_pricing": job.latest_estimate_pricing,
        "quote_pricing": job.latest_quote_pricing,
        "reality_pricing": job.latest_reality_pricing,
    }
