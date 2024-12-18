# workflow/forms.py
import logging

from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from workflow.models import (
    AdjustmentEntry,
    Client,
    Invoice,
    Job,
    JobPricing,
    MaterialEntry,
    Staff,
    TimeEntry,
)

logger = logging.getLogger(__name__)
DEBUG_FORM = False  # Toggle form debugging


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = "__all__"  # Include all fields from the model

    class JobForm(forms.ModelForm):
        class Meta:
            model = Job
            fields = "__all__"  # Include all fields from the model

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Ensure that the 'id' field is included as a hidden input
            self.fields["id"].widget = forms.HiddenInput()
            # Disable 'date_created' as read-only
            self.fields["date_created"].disabled = True
            if "last_updated" in self.fields:
                self.fields["last_updated"].disabled = True


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


class TimeEntryForm(forms.ModelForm):                                                                      # Form for creating and editing TimeEntry instances
    class Meta:
        model = TimeEntry
        
        widgets = {                                                                                        # Configure form widgets for better user interface
            "date": forms.DateInput(attrs={"type": "date"}),                                               # Use HTML5 date picker for better date selection
            'description': forms.Textarea(attrs={'rows':3})                                                # Provide a larger text area for descriptions
        }

        fields = (
            "staff",
            "job_pricing",
            "date",
            "hours",
            "items",
            "minutes_per_item",
            "description",
            "wage_rate",
            "charge_out_rate",
        )

    def __init__(self, *args, staff_member=None, **kwargs):                                                # Initialize the form with optional staff_member paramete
        super().__init__(*args, **kwargs)
        if staff_member:
            # Handle case when staff_member is provided
            self.fields["staff"].initial = staff_member                                                    # Pre-select the staff field with provided staff member
            self.fields["staff"].widget.attrs['disabled'] = True                                           # Disable staff field to prevent changes
            self.fields["staff"].required = False                                                          # Make staff field not required as it's set automatically

            # Pre-populate rate fields
            self.fields["wage_rate"].initial = staff_member.wage_rate                                      # Set initial wage rate from staff member
            # self.fields["charge_out_rate"].initial = staff_member.charge_out_rate                        # Set initial charge-out rate from staff member - currently not working because TimeEntry model has not charge_out_rate property
        else:
            # Handle case when no staff_member is provided
            self.fields["staff"].queryset = Staff.objects.all()                                            # Load all staff members for selection

            # Handle rate population for existing instances
            if "instance" in kwargs and kwargs["instance"] and kwargs["instance"].staff:                   # Check if editing existing TimeEntry
                staff = kwargs["instance"].staff
                self.fields["wage_rate"].initial = staff.wage_rate                                         # Set wage rate from existing entry's staff
                '''try:                                                                                    # Safely handle charge_out_rate for existing instances
                    self.fields["charge_out_rate"].initial = (
                        staff.charge_out_rate 
                        if hasattr(staff, 'charge_out_rate') 
                        else staff.wage_rate
                    )
                except AttributeError:
                    self.fields["charge_out_rate"].initial = 0'''



class StaffCreationForm(UserCreationForm):
    class Meta:
        model = Staff
        fields = (
            "email",
            "first_name",
            "last_name",
            "preferred_name",
            "wage_rate",
            # "charge_out_rate",
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
            # "charge_out_rate",
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
        fields = [
            "name",
            "email",
            "phone",
            "address",
            "is_account_customer",
            "raw_json",
        ]
        widgets = {
            "raw_json": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["raw_json"].widget.attrs["readonly"] = True

        if DEBUG_FORM:
            logger.debug(
                "ClientForm init - args: %(args)s, kwargs: %(kwargs)s",
                {
                    "args": args,
                    "kwargs": kwargs,
                },
            )
            logger.debug(
                "ClientForm instance: %(instance)s",
                {"instance": self.instance.__dict__},
            )

            for field_name, field in self.fields.items():
                logger.debug(
                    "Field %(name)s: initial=%(initial)s, value=%(value)s",
                    {
                        "name": field_name,
                        "initial": field.initial,
                        "value": self.initial.get(field_name),
                    },
                )

    def clean(self):
        cleaned_data = super().clean()
        # logger.debug(f"ClientForm cleaned data: {cleaned_data}")
        return cleaned_data


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            "number",
            "client",
            "date",
            "total_excl_tax",
            "status",
            "raw_json",
        ]
        widgets = {
            "raw_json": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["raw_json"].widget.attrs["readonly"] = True
