# Re-export job-related enums from apps.job.enums for backward compatibility
from apps.job.enums import (
    JobPricingMethodology,
    JobPricingStage,
    InvoiceStatus,
    QuoteStatus,
    RateType,
    MetalType,
)

from django.db import models


class AIProviderTypes(models.TextChoices):
    ANTHROPIC = "Claude"
    GOOGLE = "Gemini"
