# workflow/job_view.py

from django.views.generic import DetailView, CreateView, ListView, UpdateView
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.urls import reverse_lazy
from typing import List, Tuple, Type

from workflow.models import Job, JobPricing
from workflow.forms import JobForm


class JobView(DetailView):
    model = Job
    template_name = "workflow/job_detail.html"
    context_object_name = "job"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job = self.object

        # Fetch the latest estimate and quote
        latest_estimate = self.get_latest_pricing(job, "estimate")
        latest_quote = self.get_latest_pricing(job, "quote")

        context["latest_estimate"] = latest_estimate
        context["latest_quote"] = latest_quote

        # Add the option to view other pricings if needed
        context["other_pricings"] = job.pricings.exclude(id__in=[latest_estimate.id, latest_quote.id] if latest_estimate and latest_quote else [])

        return context

    def get_latest_pricing(self, job, pricing_type):
        return job.pricings.filter(estimate_type=pricing_type).order_by('-created_at').first()


class JobCreateView(CreateView):
    model: Type[Job] = Job
    form_class: Type[JobForm] = JobForm
    template_name: str = "workflow/job_form.html"
    success_url: str = reverse_lazy("job_list")

    def form_valid(self, form: JobForm) -> JsonResponse:
        form.instance._history_user = self.request.user  # Set user for history tracking
        return super().form_valid(form)


class JobListView(ListView):
    model: Type[Job] = Job
    template_name: str = "workflow/job_list.html"
    context_object_name: str = "jobs"


class JobUpdateView(UpdateView):
    model: Type[Job] = Job
    form_class: Type[JobForm] = JobForm
    template_name: str = "workflow/edit_job.html"

    def get_success_url(self) -> str:
        return reverse_lazy("job_detail", kwargs={"pk": self.object.pk})


def fetch_job_status_values(request) -> JsonResponse:
    status_choices: List[Tuple[str, str]] = Job.JOB_STATUS_CHOICES
    return JsonResponse({"status_choices": status_choices})
