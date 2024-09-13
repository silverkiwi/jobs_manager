from typing import Dict

from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

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
        fields = ["pricing_type"]


class MaterialEntryForm(forms.ModelForm):
    class Meta:
        model = MaterialEntry
        fields = ["description", "cost_price", "sale_price", "quantity"]


class AdjustmentEntryForm(forms.ModelForm):
    class Meta:
        model = AdjustmentEntry
        fields = ["description", "cost", "revenue"]


class StaffCreationForm(UserCreationForm):
    class Meta:
        model = Staff
        fields = (
            "email",
            "first_name",
            "last_name",
            "preferred_name",
            "wage_rate",
            "ims_payroll_id",
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
            "ims_payroll_id",
        )


class TimeEntryForm(forms.ModelForm):
    job_str_to_id: Dict[str, int] = {}
    staff_str_to_id: Dict[str, int] = {}

    class Meta:
        model = TimeEntry
        fields = ["job", "staff", "date", "minutes", "note", "is_billable"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super(TimeEntryForm, self).__init__(*args, **kwargs)
        self.fields["job"].queryset = Job.objects.all()
        self.fields["staff"].queryset = Staff.objects.all()


class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = [
            "email",
            "first_name",
            "last_name",
            "preferred_name",
            "wage_rate",
            "charge_out_rate",
            "ims_payroll_id",
            "is_active",
            "is_staff",
        ]
