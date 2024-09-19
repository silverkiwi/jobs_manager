from django.db import models


class JobPricingType(models.TextChoices):
    FIXED_PRICE = "fixed_price", "Fixed Price"
    TIME_AND_MATERIALS = "time_materials", "Time & Materials"


class JobPricingStage(models.TextChoices):
    ESTIMATE = "estimate", "Estimate"
    QUOTE = "quote", "Quote"
    REALITY = "reality", "Reality"

class InvoiceStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    AUTHORISED = "AUTHORISED", "Authorised"
    DELETED = "DELETED", "Deleted"
    VOIDED = "VOIDED", "Voided"
    PAID = "PAID", "Paid"