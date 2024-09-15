from django.views.generic import DetailView
from django.shortcuts import get_object_or_404
from workflow.models import Job, JobPricing

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
