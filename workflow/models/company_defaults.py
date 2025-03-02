from django.core.exceptions import ValidationError
from django.db import models, transaction


class CompanyDefaults(models.Model):
    company_name = models.CharField(max_length=255, primary_key=True)
    time_markup = models.DecimalField(max_digits=5, decimal_places=2, default=0.3)
    materials_markup = models.DecimalField(max_digits=5, decimal_places=2, default=0.2)
    charge_out_rate = models.DecimalField(
        max_digits=6, decimal_places=2, default=105.00
    )  # rate per hour
    wage_rate = models.DecimalField(
        max_digits=6, decimal_places=2, default=32.00
    )  # rate per hour

    # Default working hours (Mon-Fri, 7am - 3pm)
    mon_start = models.TimeField(default="07:00")
    mon_end = models.TimeField(default="15:00")
    tue_start = models.TimeField(default="07:00")
    tue_end = models.TimeField(default="15:00")
    wed_start = models.TimeField(default="07:00")
    wed_end = models.TimeField(default="15:00")
    thu_start = models.TimeField(default="07:00")
    thu_end = models.TimeField(default="15:00")
    fri_start = models.TimeField(default="07:00")
    fri_end = models.TimeField(default="15:00")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_xero_sync = models.DateTimeField(null=True, blank=True, help_text="The last time Xero data was synchronized")
    last_xero_deep_sync = models.DateTimeField(null=True, blank=True, help_text="The last time a deep Xero sync was performed (looking back 90 days)")

    class Meta:
        verbose_name = "Company Defaults"
        verbose_name_plural = "Company Defaults"

    @classmethod
    def get_instance(cls):
        """
        Get or create the singleton instance.
        This is the preferred way to get the CompanyDefaults instance.
        """
        with transaction.atomic():
            # Get the first record or create one if none exists
            instance, _ = cls.objects.get_or_create()
            return instance

    def __str__(self):
        return self.company_name
