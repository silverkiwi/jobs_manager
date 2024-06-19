import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

class Job(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
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
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.client_name} - {self.name} - {self.job_number or self.order_number} - ({self.status})"

class JobPricing(models.Model):
    PRICING_TYPE_CHOICES = [
        ('estimate', 'Estimate'),
        ('actual', 'Actual'),
        ('quote', 'Quote'),
        ('invoice', 'Invoice')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='job_pricings')
    pricing_type = models.CharField(max_length=10, choices=PRICING_TYPE_CHOICES)
    cost = models.FloatField(default=0.0)
    revenue = models.FloatField(default=0.0)

    @property
    def profit(self):
        return self.revenue - self.cost

    def __str__(self):
        return f"{self.job} - {self.pricing_type}"

class MaterialEntry(models.Model):
    """Materials, e.g. sheets"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_pricing = models.ForeignKey(JobPricing, on_delete=models.CASCADE)
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

class AdjustmentEntry(models.Model):
    """For when costs are manually added to a job"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_pricing = models.ForeignKey(JobPricing, on_delete=models.CASCADE)
    description = models.CharField(max_length=200, null=True, blank=True)
    cost = models.FloatField(default=0.0)
    revenue = models.FloatField(default=0.0)

class StaffManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('wage_rate', 0)
        extra_fields.setdefault('charge_out_rate', 0)

        return self.create_user(email, password, **extra_fields)

class Staff(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    preferred_name = models.CharField(max_length=30, blank=True, null=True)
    wage_rate = models.DecimalField(max_digits=10, decimal_places=2)
    charge_out_rate = models.DecimalField(max_digits=10, decimal_places=2)
    ims_payroll_id = models.CharField(max_length=100,unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()

    objects = StaffManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'wage_rate', 'charge_out_rate', 'ims_payroll_id']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_display_name(self):
        return self.preferred_name or self.first_name

class TimeEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='time_entries')
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='time_entries')
    date = models.DateField()
    duration = models.DecimalField(max_digits=5, decimal_places=2)  # Duration in hours
    note = models.TextField(blank=True, null=True)
    is_billable = models.BooleanField(default=True)
    wage_rate = models.FloatField()
    charge_out_rate = models.FloatField()

    def __str__(self):
        return f"{self.staff.get_display_name()} {self.job.name} on {self.date}"