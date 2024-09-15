from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from workflow.forms import (
    TimeEntryForm,
    MaterialEntryForm,
    AdjustmentEntryForm,
    JobPricingForm
)
from workflow.models import Job, JobPricing

import logging

logger = logging.getLogger(__name__)

class JobPricingCreateView(CreateView):
    model = JobPricing
    template_name = "workflow/job_pricing_form.html"
    form_class = JobPricingForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Set the initial job and estimate type
        form.fields['job'].initial = self.kwargs['job_id']
        form.fields['pricing_stage'].initial = self.kwargs['pricing_stage']
        return form

    def form_valid(self, form):
        job = get_object_or_404(Job, pk=self.kwargs['job_id'])
        form.instance.job = job
        form.instance.pricing_stage = self.kwargs['pricing_stage']
        form.save()  # Save the form to create the JobPricing instance

        # Redirect to 'edit_job_pricing' with the newly created JobPricing ID
        return redirect('edit_job_pricing', pk=form.instance.pk)  # Use form.instance.pk


class JobPricingUpdateView(UpdateView):
    model = JobPricing
    template_name = "workflow/job_pricing_detail.html"
    context_object_name = "job_pricing"
    form_class = JobPricingForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job = get_object_or_404(Job, pk=self.kwargs['job_id'])  # Get the job using job_id from URL
        job_pricing = self.get_object()

        # Related entries
        time_entries = job_pricing.time_entries.all()
        material_entries = job_pricing.material_entries.all()
        adjustment_entries = job_pricing.adjustment_entries.all()

        # Total cost and revenue calculations
        total_time_cost = sum(entry.cost for entry in time_entries)
        total_time_revenue = sum(entry.revenue for entry in time_entries)

        total_material_cost = sum(entry.cost for entry in material_entries)
        total_material_revenue = sum(entry.revenue for entry in material_entries)

        total_adjustment_cost = sum(entry.cost for entry in adjustment_entries)
        total_adjustment_revenue = sum(entry.revenue for entry in adjustment_entries)


        # Add data to context
        context['time_entries'] = time_entries
        context['material_entries'] = material_entries
        context['adjustment_entries'] = adjustment_entries

        # These are from the properties on the JobPricing model
        context['total_cost'] = job_pricing.total_cost
        context['total_revenue'] = job_pricing.total_revenue

        # Forms for adding new entries (if you decide to keep them)
        # context['time_entry_form'] = TimeEntryForm()
        # context['material_entry_form'] = MaterialEntryForm()
        # context['adjustment_entry_form'] = AdjustmentEntryForm()

        return context

    def form_valid(self, form):
        # Since this is an UpdateView, the object already exists
        response = super().form_valid(form)
        return response

    def get_success_url(self):
        return reverse_lazy('edit_job_pricing', kwargs={'pk': self.object.pk})
