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
