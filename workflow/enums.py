from django.db import models

from workflow.models import Job


class JobPricingType(models.TextChoices):
    FIXED_PRICE = 'fixed_price', 'Fixed Price'
    TIME_AND_MATERIALS = 'time_materials', 'Time & Materials'

class JobPricingStage(models.TextChoices):
    ESTIMATE = 'estimate', 'Estimate'
    QUOTE = 'quote', 'Quote'
    REALITY = 'reality', 'Reality'

def fetch_job_status_values():
    # Assuming Job.STATUS_CHOICES is a list of tuples like [(status_value, display_name), ...]
    return dict(Job.JOB_STATUS_CHOICES)
