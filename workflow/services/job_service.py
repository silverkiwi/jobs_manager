from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from workflow.models import AdjustmentEntry, Job, MaterialEntry, TimeEntry


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
            Prefetch(f"{stage}__material_entries",
                     queryset=MaterialEntry.objects.all())
        )
        # Prefetch adjustment_entries
        prefetch_list.append(
            Prefetch(
                f"{stage}__adjustment_entries",
                queryset=AdjustmentEntry.objects.all()
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
