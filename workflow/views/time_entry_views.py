import logging
from typing import Type

from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from workflow.forms import TimeEntryForm
from workflow.models import JobPricing, TimeEntry

logger = logging.getLogger(__name__)


class CreateTimeEntryView(CreateView):
    model: Type[TimeEntry] = TimeEntry
    form_class: Type[TimeEntryForm] = TimeEntryForm
    template_name: str = "time_entries/create_time_entry.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add job_pricing to context
        context["job_pricing"] = JobPricing.objects.get(
            pk=self.kwargs["job_pricing_id"]
        )
        return context

    def form_valid(self, form):
        # Retrieve the job_pricing from the URL kwargs
        job_pricing = JobPricing.objects.get(pk=self.kwargs["job_pricing_id"])
        # Set the job_pricing for the time entry
        form.instance.job_pricing = job_pricing

        # Set the wage_rate and charge_out_rate based on the selected staff from the form
        staff = form.instance.staff
        form.instance.wage_rate = staff.wage_rate
        # form.instance.charge_out_rate = staff.charge_out_rate

        # Save the form (calls form.save())
        response = super().form_valid(form)

        # Update the last_updated field of the associated job after saving the TimeEntry
        job = form.instance.job_pricing.job
        job.save(update_fields=["last_updated"])

        return response

    def get_success_url(self):
        # Redirect to the job pricing update page after successful time entry creation
        return reverse_lazy(
            "update_job_pricing", kwargs={"pk": self.object.job_pricing.id}
        )


class UpdateTimeEntryView(UpdateView):
    model: Type[TimeEntry] = TimeEntry
    form_class: Type[TimeEntryForm] = TimeEntryForm
    template_name: str = "workflow/time_entries/update_time_entry.html"  # noqa

    def form_valid(self, form: TimeEntryForm) -> JsonResponse:
        # Update the time entry instance
        response = super().form_valid(form)

        # Update the last_updated field of the associated job
        job = self.object.job_pricing.job
        job.save(update_fields=["last_updated"])

        return response

    def get_success_url(self):  # noqa
        # Redirect to the job pricing update page after successful time entry update
        return reverse_lazy(
            "update_job_pricing", kwargs={"pk": self.object.job_pricing.id}
        )
