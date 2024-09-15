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
        exclude = ['job', 'pricing_stage']

class MaterialEntryForm(forms.ModelForm):
    class Meta:
        model = MaterialEntry
        exclude = ['job_pricing']

class AdjustmentEntryForm(forms.ModelForm):
    class Meta:
        model = AdjustmentEntry
        exclude = ['job_pricing']

class TimeEntryForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }
        exclude = ['job_pricing']

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
