from job.models import JobPricing as BaseJobPricing


class JobPricing(BaseJobPricing):
    class Meta:
        proxy = True
