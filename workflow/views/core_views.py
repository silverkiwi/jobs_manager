import logging
from typing import List, Tuple, Type, Dict, Any

from django.contrib.auth import login, authenticate
from django.http import JsonResponse
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    TemplateView,
    FormView,
)
from django.urls import reverse_lazy

from workflow.forms import (
    StaffCreationForm,
    StaffChangeForm,
    StaffForm,
    JobForm,
    #    JobPricingForm,
    TimeEntryForm,
)

from workflow.models import Job, JobPricing, Staff, TimeEntry

logger = logging.getLogger(__name__)


def fetch_job_status_values(request) -> JsonResponse:
    status_choices: List[Tuple[str, str]] = Job.JOB_STATUS_CHOICES
    return JsonResponse({"status_choices": status_choices})


class IndexView(TemplateView):
    template_name: str = "workflow/index.html"


class AboutView(TemplateView):
    template_name: str = "workflow/about.html"


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


class JobDetailView(DetailView):
    model: Type[Job] = Job
    template_name: str = "workflow/job_detail.html"
    context_object_name: str = "job"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        job: Job = self.object

        pricing_models: List[JobPricing] = job.job_pricings.all()
        pricing_data: List[Dict[str, Any]] = []

        for model in pricing_models:
            time_entries: List[TimeEntry] = model.time_entries.all()
            material_entries: List[Any] = model.material_entries.all()
            adjustment_entries: List[Any] = model.adjustment_entries.all()

            total_time_cost: float = sum(entry.cost for entry in time_entries)
            total_time_revenue: float = sum(entry.revenue for entry in time_entries)

            total_material_cost: float = sum(entry.cost for entry in material_entries)
            total_material_revenue: float = sum(
                entry.revenue for entry in material_entries
            )

            total_adjustment_cost: float = sum(
                entry.cost for entry in adjustment_entries
            )
            total_adjustment_revenue: float = sum(
                entry.revenue for entry in adjustment_entries
            )

            total_cost: float = (
                total_time_cost + total_material_cost + total_adjustment_cost
            )
            total_revenue: float = (
                total_time_revenue + total_material_revenue + total_adjustment_revenue
            )

            pricing_data.append(
                {
                    "model": model,
                    "total_time_cost": total_time_cost,
                    "total_time_revenue": total_time_revenue,
                    "total_material_cost": total_material_cost,
                    "total_material_revenue": total_material_revenue,
                    "total_adjustment_cost": total_adjustment_cost,
                    "total_adjustment_revenue": total_adjustment_revenue,
                    "total_cost": total_cost,
                    "total_revenue": total_revenue,
                }
            )

        context["pricing_data"] = pricing_data

        history: List[Any] = job.history.all()
        history_diffs: List[Dict[str, Any]] = []
        for i in range(len(history) - 1):
            new_record = history[i]
            old_record = history[i + 1]
            delta = new_record.diff_against(old_record)
            changes = [
                {"field": change.field, "old": change.old, "new": change.new}
                for change in delta.changes
            ]
            history_diffs.append(
                {
                    "record": new_record,
                    "changes": changes,
                    "changed_by": new_record.history_user_id,
                }
            )

        # Add the initial record with no changes
        if history:
            initial_record = history.last()
            history_diffs.append(
                {
                    "record": initial_record,
                    "changes": [],
                    "changed_by": new_record.history_user_id,
                }
            )

        context["history_diffs"] = history_diffs

        return context


class RegisterView(FormView):
    template_name: str = "workflow/register.html"
    form_class: Type[StaffCreationForm] = StaffCreationForm
    success_url: str = reverse_lazy("job_list")

    def form_valid(self, form: StaffCreationForm) -> JsonResponse:
        form.save()
        email: str = form.cleaned_data.get("email")
        raw_password: str = form.cleaned_data.get("password1")
        user = authenticate(email=email, password=raw_password)
        login(self.request, user)
        return super().form_valid(form)


class ProfileView(UpdateView):
    model: Type[Staff] = Staff
    form_class: Type[StaffChangeForm] = StaffChangeForm
    template_name: str = "workflow/profile.html"
    success_url: str = reverse_lazy("job_list")

    def get_object(self) -> Staff:
        return self.request.user


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
        job_pricing, created = JobPricing.objects.get_or_create(
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


class StaffListView(ListView):
    model: Type[Staff] = Staff
    template_name: str = "workflow/staff_list.html"
    context_object_name: str = "staff_members"


class StaffProfileView(DetailView):
    model: Type[Staff] = Staff
    template_name: str = "workflow/staff_profile.html"
    context_object_name: str = "staff_member"


class JobUpdateView(UpdateView):
    model: Type[Job] = Job
    form_class: Type[JobForm] = JobForm
    template_name: str = "workflow/edit_job.html"

    def get_success_url(self) -> str:
        return reverse_lazy("job_detail", kwargs={"pk": self.object.pk})


class StaffUpdateView(UpdateView):
    model: Type[Staff] = Staff
    form_class: Type[StaffForm] = StaffForm
    template_name: str = "workflow/edit_staff.html"

    def get_success_url(self) -> str:
        return reverse_lazy("staff_profile", kwargs={"pk": self.object.pk})


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


class DashboardView(TemplateView):
    template_name: str = "workflow/dashboard.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        # You can add any additional context data here if needed
        return context
