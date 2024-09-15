from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, UpdateView
from workflow.forms import (
    TimeEntryForm,
    MaterialEntryForm,
    AdjustmentEntryForm,
    JobPricingForm
)
from workflow.models import Job, JobPricing

class JobPricingCreateView(CreateView):
    model = JobPricing
    template_name = "workflow/job_pricing_form.html"
    form_class = JobPricingForm

    def form_valid(self, form):
        form.instance.job = get_object_or_404(Job, pk=self.kwargs['job_id'])
        response = super().form_valid(form)
        return redirect('edit_job_pricing', pk=self.object.pk)

class JobPricingUpdateView(UpdateView):
    model = JobPricing
    template_name = "workflow/job_pricing.html"
    context_object_name = "job_pricing"
    form_class = JobPricingForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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

        total_cost = (
            total_time_cost + total_material_cost + total_adjustment_cost
        )
        total_revenue = (
            total_time_revenue + total_material_revenue + total_adjustment_revenue
        )

        # Add data to context
        context['time_entries'] = time_entries
        context['material_entries'] = material_entries
        context['adjustment_entries'] = adjustment_entries

        # Add totals to context
        context['total_cost'] = total_cost
        context['total_revenue'] = total_revenue

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
        return reverse('edit_job_pricing', kwargs={'pk': self.object.pk})
