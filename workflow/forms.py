# workflow/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from workflow.models import (
    AdjustmentEntry,
    Job,
    JobPricing,
    MaterialEntry,
    Staff,
    TimeEntry,
)

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            "client_name",
            "order_number",
            "contact_person",
            "contact_phone",
            "job_number",
            "description",
            "status",
            "paid",
        ]

class JobPricingForm(forms.ModelForm):
    class Meta:
        model = JobPricing
        fields = ["job", "estimate_type"]

class MaterialEntryForm(forms.ModelForm):
    class Meta:
        model = MaterialEntry
        fields = ["job_pricing", "description", "unit_cost", "unit_revenue", "quantity"]

class AdjustmentEntryForm(forms.ModelForm):
    class Meta:
        model = AdjustmentEntry
        fields = ["job_pricing", "description", "cost", "revenue"]

class TimeEntryForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        fields = ["job_pricing", "staff", "date", "minutes", "note", "is_billable"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["job_pricing"].queryset = JobPricing.objects.all()
        self.fields["staff"].queryset = Staff.objects.all()

class StaffCreationForm(UserCreationForm):
    class Meta:
        model = Staff
        fields = (
            "email",
            "first_name",
            "last_name",
            "preferred_name",
            "wage_rate",
            "charge_out_rate",
            "ims_payroll_id",
            "is_staff",
            "is_active",
        )

class StaffChangeForm(UserChangeForm):
    class Meta:
        model = Staff
        fields = (
            "email",
            "first_name",
            "last_name",
            "preferred_name",
            "wage_rate",
            "charge_out_rate",
            "ims_payroll_id",
            "is_staff",
            "is_active",
            "is_superuser",
            "groups",
            "user_permissions",
        )
