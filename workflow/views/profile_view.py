from typing import Type

from django.urls import reverse_lazy
from django.views.generic import UpdateView

from workflow.forms import StaffChangeForm
from workflow.models import Staff


class ProfileView(UpdateView):
    model: Type[Staff] = Staff
    form_class: Type[StaffChangeForm] = StaffChangeForm
    template_name: str = "workflow/profile.html"
    success_url: str = reverse_lazy("job_list")

    def get_object(self) -> Staff:
        return self.request.user
