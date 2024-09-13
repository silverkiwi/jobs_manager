import logging
from typing import Type

from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, UpdateView

from workflow.forms import TimeEntryForm
from workflow.models import Job, JobPricingType, Staff, TimeEntry

logger = logging.getLogger(__name__)


class CreateTimeEntryView(CreateView):
    model: Type[TimeEntry] = TimeEntry
    form_class: Type[TimeEntryForm] = TimeEntryForm
    template_name: str = "workflow/create_time_entry.html"
    success_url: str = reverse_lazy("time_entry_success")

    def form_valid(self, form: TimeEntryForm) -> JsonResponse:
        time_entry: TimeEntry = form.save(commit=False)
        staff: Staff = time_entry.staff
        time_entry.wage_rate = staff.wage_rate
        time_entry.charge_out_rate = staff.charge_out_rate

        job: Job = time_entry.job
        job_pricing, created = JobPricingType.objects.get_or_create(
            job=job, pricing_type="actual"
        )

        time_entry.job_pricing = job_pricing
        time_entry.save()

        job.save(update_fields=["last_updated"])

        return super().form_valid(form)

    def form_invalid(self, form: TimeEntryForm) -> JsonResponse:
        logger.debug("Form errors: %s", form.errors)
        return super().form_invalid(form)


class TimeEntrySuccessView(TemplateView):
    template_name: str = "workflow/time_entry_success.html"


class TimeEntryUpdateView(UpdateView):
    model: Type[TimeEntry] = TimeEntry
    form_class: Type[TimeEntryForm] = TimeEntryForm
    template_name: str = "workflow/edit_time_entry.html"
    success_url: str = reverse_lazy("time_entry_success")

    def form_valid(self, form: TimeEntryForm) -> JsonResponse:
        time_entry: TimeEntry = form.save(commit=False)
        time_entry.save(
            update_fields=["date", "minutes", "note", "is_billable", "job", "staff"]
        )
        return super().form_valid(form)
