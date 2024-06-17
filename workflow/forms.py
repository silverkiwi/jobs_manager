from django import forms
from .models import Job, PricingModel, TimeEntry, MaterialEntry, ManualEntry

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['client_name', 'order_number', 'contact_person', 'contact_phone', 'job_number', 'description', 'status', 'paid']

class PricingModelForm(forms.ModelForm):
    class Meta:
        model = PricingModel
        fields = ['pricing_type', 'cost', 'revenue']

class TimeEntryForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        fields = ['date', 'staff_name', 'hours', 'wage_rate', 'charge_out_rate']

class MaterialEntryForm(forms.ModelForm):
    class Meta:
        model = MaterialEntry
        fields = ['description', 'cost_price', 'sale_price', 'quantity']

class ManualEntryForm(forms.ModelForm):
    class Meta:
        model = ManualEntry
        fields = ['description', 'cost', 'revenue']

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Staff

class StaffCreationForm(UserCreationForm):
    class Meta:
        model = Staff
        fields = ('email', 'first_name', 'last_name', 'pay_rate', 'ims_payroll_id')

class StaffChangeForm(UserChangeForm):
    class Meta:
        model = Staff
        fields = ('email', 'first_name', 'last_name', 'pay_rate', 'ims_payroll_id')
