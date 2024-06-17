from django.db import models
from django.utils import timezone

class Job(models.Model):
    STATUS_CHOICES = [
        ('quoting', 'Quoting'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('archived', 'Archived')
    ]

    client_name = models.CharField(max_length=100)
    order_number = models.CharField(max_length=100, null=True, blank=True)
    contact_person = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=15)
    job_number = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField()
    date_created = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='quoting')
    parent = models.ForeignKey('self', null=True, blank=True, related_name='revisions', on_delete=models.SET_NULL)
    paid = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.client_name} - {self.status} - {self.job_number or self.order_number}"

class PricingModel(models.Model):
    PRICING_TYPE_CHOICES = [
        ('estimate', 'Estimate'),
        ('actual', 'Actual'),
        ('quote', 'Quote'),
        ('invoice', 'Invoice')
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='pricing_models')
    pricing_type = models.CharField(max_length=10, choices=PRICING_TYPE_CHOICES)
    cost = models.FloatField(default=0.0)
    revenue = models.FloatField(default=0.0)

    @property
    def profit(self):
        return self.revenue - self.cost

    def __str__(self):
        return f"{self.job} - {self.pricing_type}"

class TimeEntry(models.Model):
    pricing_model = models.ForeignKey(PricingModel, on_delete=models.CASCADE)
    date = models.DateField()
    staff_name = models.CharField(max_length=100)
    hours = models.FloatField()
    wage_rate = models.FloatField()
    charge_out_rate = models.FloatField()

    @property
    def cost(self):
        return self.hours * self.wage_rate

    @property
    def revenue(self):
        return self.hours * self.charge_out_rate

class MaterialEntry(models.Model):
    pricing_model = models.ForeignKey(PricingModel, on_delete=models.CASCADE)
    description = models.CharField(max_length=200)
    cost_price = models.FloatField()
    sale_price = models.FloatField()
    quantity = models.FloatField()

    @property
    def cost(self):
        return self.cost_price * self.quantity

    @property
    def revenue(self):
        return self.sale_price * self.quantity

class ManualEntry(models.Model):
    pricing_model = models.ForeignKey(PricingModel, on_delete=models.CASCADE)
    description = models.CharField(max_length=200, null=True, blank=True)
    cost = models.FloatField(default=0.0)
    revenue = models.FloatField(default=0.0)
