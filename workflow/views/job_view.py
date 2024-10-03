import logging

from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from workflow.enums import JobPricingStage
from workflow.forms import JobForm
from workflow.models import Job

logger = logging.getLogger(__name__)


class CreateJobViewOriginal(CreateView):
    model = Job
    form_class = JobForm
    template_name = "jobs/create_job.html"  # Ensure this template exists

    def get_success_url(self):
        # Redirect to the job update page after creation
        return reverse_lazy("update_job", kwargs={"pk": self.object.pk})


class UpdateJobView(UpdateView):
    model = Job
    form_class = JobForm
    template_name = ("jobs/update_job.html")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job = self.object

        # Fetch the latest estimate and quote
        latest_estimate = self.get_latest_pricing(job, JobPricingStage.ESTIMATE)
        latest_quote = self.get_latest_pricing(job, JobPricingStage.QUOTE)

        context["latest_estimate"] = latest_estimate
        context["latest_quote"] = latest_quote

        context["other_pricings"] = job.pricings.exclude(
            id__in=[
                pricing.id
                for pricing in [latest_estimate, latest_quote]
                if pricing is not None
            ]
        ).order_by("-created_at")

        # Add job-specific details for display
        context.update(
            {
                "client_name": job.client.name,
                "order_number": job.order_number,
                "contact_person": job.contact_person,
                "contact_phone": job.contact_phone,
                "job_name": job.name,
                "job_number": job.job_number,
                "description": job.description,
                "status": job.get_status_display(),
                "paid": job.paid,
            }
        )

        return context

    def get_latest_pricing(self, job, pricing_stage):
        return (
            job.pricings.filter(pricing_stage=pricing_stage)
            .order_by("-created_at")
            .first()
        )

    def get_success_url(self):
        return "/"


class ListJobView(ListView):
    model = Job
    template_name = "jobs/list_jobs.html"
    context_object_name = "jobs"


def api_fetch_status_values(request):
    status_values = dict(Job.JOB_STATUS_CHOICES)
    return JsonResponse(status_values)
