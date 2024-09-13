from typing import Type

from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView, UpdateView

from workflow.forms import StaffCreationForm, StaffForm
from workflow.models import Staff


class StaffListView(ListView):
    model: Type[Staff] = Staff
    template_name: str = "workflow/staff_list.html"
    context_object_name: str = "staff_members"


class StaffProfileView(DetailView):
    model: Type[Staff] = Staff
    template_name: str = "workflow/staff_profile.html"
    context_object_name: str = "staff_member"


class StaffUpdateView(UpdateView):
    model: Type[Staff] = Staff
    form_class: Type[StaffForm] = StaffForm
    template_name: str = "workflow/edit_staff.html"

    def get_success_url(self) -> str:
        return reverse_lazy("staff_profile", kwargs={"pk": self.object.pk})


class RegisterStaffView(FormView):
    template_name: str = "workflow/register_staff.html"
    form_class: Type[StaffCreationForm] = StaffCreationForm
    success_url: str = reverse_lazy("job_list")

    def form_valid(self, form: StaffCreationForm) -> JsonResponse:
        form.save()
        email: str = form.cleaned_data.get("email")
        raw_password: str = form.cleaned_data.get("password1")
        user = authenticate(email=email, password=raw_password)
        login(self.request, user)
        return super().form_valid(form)
