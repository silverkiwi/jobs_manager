from decimal import Decimal

# Re-export job-related enums from job.enums for backward compatibility
from job.enums import (
    JobPricingType,
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

# Note: After all code has been updated to import from job.enums,
# this re-exporting can be removed.
