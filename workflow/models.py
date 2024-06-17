from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

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
    history = HistoricalRecords()

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

        return self.create_user(email, password, **extra_fields)

class Staff(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    pay_rate = models.DecimalField(max_digits=10, decimal_places=2)
    ims_payroll_id = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()

    objects = StaffManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'pay_rate', 'ims_payroll_id']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

