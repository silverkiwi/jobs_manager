import uuid
from django import forms
from .models import Job, JobPricing, TimeEntry, MaterialEntry, AdjustmentEntry, Staff

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['client_name', 'order_number', 'contact_person', 'contact_phone', 'job_number', 'description', 'status', 'paid']

class JobPricingForm(forms.ModelForm):
    class Meta:
        model = JobPricing
        fields = ['pricing_type']

class TimeEntryForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        fields = ['job', 'staff', 'date', 'duration', 'note', 'is_billable']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class MaterialEntryForm(forms.ModelForm):
    class Meta:
        model = MaterialEntry
        fields = ['description', 'cost_price', 'sale_price', 'quantity']

class AdjustmentEntryForm(forms.ModelForm):
    class Meta:
        model = AdjustmentEntry
        fields = ['description', 'cost', 'revenue']

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Staff

class StaffCreationForm(UserCreationForm):
    class Meta:
        model = Staff
        fields = ('email', 'first_name', 'last_name', 'preferred_name', 'wage_rate', 'ims_payroll_id')

class StaffChangeForm(UserChangeForm):
    class Meta:
        model = Staff
        fields = ('email', 'first_name', 'last_name', 'preferred_name', 'wage_rate', 'ims_payroll_id')


class TimeEntryForm(forms.ModelForm):
    job_str_to_id = {}
    staff_str_to_id = {}

    class Meta:
        model = TimeEntry
        fields = ['job', 'staff', 'date', 'duration', 'note', 'is_billable']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(TimeEntryForm, self).__init__(*args, **kwargs)
        self.fields['job'].queryset = Job.objects.all()
        self.fields['staff'].queryset = Staff.objects.all()


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['client_name', 'order_number', 'contact_person', 'contact_phone', 'job_number', 'description', 'status', 'paid']

class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = ['email', 'first_name', 'last_name', 'preferred_name', 'wage_rate', 'charge_out_rate', 'ims_payroll_id', 'is_active', 'is_staff']
