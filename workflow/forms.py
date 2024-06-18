from django import forms
from .models import Job, JobPricing, TimeEntry, MaterialEntry, AdjustmentEntry

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['client_name', 'order_number', 'contact_person', 'contact_phone', 'job_number', 'description', 'status', 'paid']

class JobPricingForm(forms.ModelForm):
    class Meta:
        model = JobPricing
        fields = ['pricing_type', 'cost', 'revenue']

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
    class Meta:
        model = TimeEntry
        fields = ['job', 'staff', 'date', 'duration', 'note', 'is_billable']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }
