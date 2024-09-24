import logging

from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from workflow.forms import JobPricingForm
from workflow.models import Job, JobPricing

logger = logging.getLogger(__name__)


class CreateJobPricingView(CreateView):
    model = JobPricing
    template_name = "job_pricing/create_job_pricing.html"
    form_class = JobPricingForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Set the initial job and pricing stage
        form.fields["job"].initial = self.kwargs["job_id"]
        form.fields["pricing_stage"].initial = self.kwargs["pricing_stage"]
        return form

    def form_valid(self, form):
        job = get_object_or_404(Job, pk=self.kwargs["job_id"])
        form.instance.job = job
        form.instance.pricing_stage = self.kwargs["pricing_stage"]
        form.save()

        # Redirect to 'update_job_pricing' with the newly created JobPricing ID
        return redirect("update_job_pricing", pk=form.instance.pk)


class UpdateJobPricingView(UpdateView):
    model = JobPricing
    template_name = "job_pricing/update_job_pricing.html"
    form_class = JobPricingForm
    context_object_name = "job_pricing"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job_pricing = self.get_object()
        logger.debug(f"JobPricing: {job_pricing}, Associated Job: {job_pricing.job}")

        # Related entries
        time_entries = job_pricing.time_entries.all()
        material_entries = job_pricing.material_entries.all()
        adjustment_entries = job_pricing.adjustment_entries.all()

        # Add data to context
        context["time_entries"] = time_entries
        context["material_entries"] = material_entries
        context["adjustment_entries"] = adjustment_entries

        # Total cost and revenue from JobPricing model properties
        context["total_cost"] = job_pricing.total_cost
        context["total_revenue"] = job_pricing.total_revenue

        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        return response

    def get_success_url(self):
        return reverse_lazy("update_job_pricing", kwargs={"pk": self.object.pk})
