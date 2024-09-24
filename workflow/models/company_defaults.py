from django.db import models
from django.core.exceptions import ValidationError

class CompanyDefaults(models.Model):
    time_markup = models.DecimalField(max_digits=5, decimal_places=2, default=0.3)
    materials_markup = models.DecimalField(max_digits=5, decimal_places=2, default=0.2)
    charge_out_rate = models.DecimalField(max_digits=6, decimal_places=2, default=105.00)
    cost_rate_without_staff = models.DecimalField(max_digits=6, decimal_places=2, default=32.00)

    # Default working hours (Mon-Fri, 7am - 3pm)
    mon_start = models.TimeField(default='07:00')
    mon_end = models.TimeField(default='15:00')
    tue_start = models.TimeField(default='07:00')
    tue_end = models.TimeField(default='15:00')
    wed_start = models.TimeField(default='07:00')
    wed_end = models.TimeField(default='15:00')
    thu_start = models.TimeField(default='07:00')
    thu_end = models.TimeField(default='15:00')
    fri_start = models.TimeField(default='07:00')
    fri_end = models.TimeField(default='15:00')

    class Meta:
        verbose_name = "Company Defaults"
        verbose_name_plural = "Company Defaults"

    def save(self, *args, **kwargs):
        if not self.pk and CompanyDefaults.objects.exists():
            raise ValidationError("There can only be one CompanyDefaults instance.")
        return super(CompanyDefaults, self).save(*args, **kwargs)

    def __str__(self):
        return f"Charge-out Rate: {self.charge_out_rate}/hr"
