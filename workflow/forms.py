# workflow/forms.py
import logging

from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

logger = logging.getLogger(__name__)

from workflow.models import (
    AdjustmentEntry,
    Job,
    JobPricing,
    MaterialEntry,
    Staff,
    TimeEntry, Client,
)


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            "job_name",
            "client_name",
            "order_number",
            "contact_person",
            "contact_phone",
            "description",
            "status",
            "paid",
        ]


class JobPricingForm(forms.ModelForm):
    class Meta:
        model = JobPricing
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["job"].disabled = True  # Make job read-only
        self.fields["pricing_stage"].disabled = True  # Make pricing_stage read-only


class MaterialEntryForm(forms.ModelForm):
    class Meta:
        model = MaterialEntry
        exclude = ["job_pricing"]


class AdjustmentEntryForm(forms.ModelForm):
    class Meta:
        model = AdjustmentEntry
        exclude = ["job_pricing"]


class TimeEntryForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),  # Keeps the date picker
        }
        exclude = [
            "job_pricing"
        ]  # Exclude job_pricing because it's set programmatically

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Drop-down for staff
        self.fields["staff"].queryset = Staff.objects.all()

        # Pre-populate wage_rate and charge_out_rate based on selected staff
        if "instance" in kwargs and kwargs["instance"] and kwargs["instance"].staff:
            staff = kwargs["instance"].staff
            self.fields["wage_rate"].initial = staff.wage_rate
            self.fields["charge_out_rate"].initial = staff.charge_out_rate


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


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'email', 'phone', 'address', 'is_account_customer', 'raw_json']
        widgets = {
            'raw_json': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['raw_json'].widget.attrs['readonly'] = True

        # Log the initial data
        logger.debug(f"ClientForm initialized with data: {self.initial}")

    def clean(self):
        cleaned_data = super().clean()
        logger.debug(f"ClientForm cleaned data: {cleaned_data}")
        return cleaned_data
