from django.db import models

class JobPricingType(models.TextChoices):
    FIXED_PRICE = 'fixed_price', 'Fixed Price'
    TIME_AND_MATERIALS = 'time_materials', 'Time & Materials'

class EstimateType(models.TextChoices):
    ESTIMATE = 'estimate', 'Estimate'
    QUOTE = 'quote', 'Quote'
    REALITY = 'reality', 'Reality'
