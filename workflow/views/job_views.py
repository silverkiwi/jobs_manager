from typing import List, Tuple, Type

from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from workflow.forms import JobForm
from workflow.models import Job


class JobCreateView(CreateView):
    model: Type[Job] = Job
    form_class: Type[JobForm] = JobForm
    template_name: str = "workflow/job_form.html"
    success_url: str = reverse_lazy("job_list")

    def form_valid(self, form: JobForm) -> JsonResponse:
        form.instance._history_user = self.request.user
        return super().form_valid(form)


class JobListView(ListView):
    model: Type[Job] = Job
    template_name: str = "workflow/job_list.html"
    context_object_name: str = "jobs"


def fetch_job_status_values(request) -> JsonResponse:
    status_choices: List[Tuple[str, str]] = Job.JOB_STATUS_CHOICES
    return JsonResponse({"status_choices": status_choices})


class JobUpdateView(UpdateView):
    model: Type[Job] = Job
    form_class: Type[JobForm] = JobForm
    template_name: str = "workflow/edit_job.html"

    def get_success_url(self) -> str:
        return reverse_lazy("job_detail", kwargs={"pk": self.object.pk})
