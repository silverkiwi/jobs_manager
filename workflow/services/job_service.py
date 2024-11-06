from django.shortcuts import get_object_or_404
from workflow.models import Job, JobPricing

# Utility to fetch job and related pricing data
def get_job_with_pricings(job_id):
    """Fetches a Job object with all related JobPricing data and prefetches relevant entries."""
    return get_object_or_404(
        Job.objects.select_related("client").prefetch_related(
            "pricings__time_entries",
            "pricings__material_entries",
            "pricings__adjustment_entries",
            "pricings__time_entries__staff",
        ),
        id=job_id,
    )

# Utility to create a new job with default job pricings
def create_new_job():
    """Creates a new Job along with initial JobPricings for estimate, quote, and reality."""
    job = Job.objects.create()
    # Create the necessary job pricings immediately upon job creation
    JobPricing.objects.create(job=job, pricing_stage="estimate")
    JobPricing.objects.create(job=job, pricing_stage="quote")
    JobPricing.objects.create(job=job, pricing_stage="reality")
    return job

# Utility to get job pricings
def get_job_pricings(job):
    """Fetch all revisions for each section of pricing, assuming they always exist."""
    return {
        "estimate": job.estimate_pricings.all(),
        "quote": job.quote_pricings.all(),
        "reality": job.reality_pricings.all(),
    }

def get_historical_job_pricings(job):
    """Fetch all historical revisions for each section of pricing, excluding the latest."""
    historical_pricings = (
        list(job.estimate_pricings.order_by('-created_at')[1:]) +
        list(job.quote_pricings.order_by('-created_at')[1:]) +
        list(job.reality_pricings.order_by('-created_at')[1:])
    )
    return historical_pricings


# Utility to fetch the latest pricing per stage
def get_latest_job_pricings(job):
    """Fetches the latest revision of each pricing stage for the given job."""
    return {
        "estimate": job.estimate_pricings.order_by('-created_at').first(),
        "quote": job.quote_pricings.order_by('-created_at').first(),
        "reality": job.reality_pricings.order_by('-created_at').first(),
    }
