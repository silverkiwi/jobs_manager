# workflow/views/material_entry_views.py

import logging
from typing import Type

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from workflow.forms import MaterialEntryForm
from workflow.models import JobPricing, MaterialEntry

logger = logging.getLogger(__name__)


class CreateMaterialEntryView(CreateView):
    model: Type[MaterialEntry] = MaterialEntry
    form_class: Type[MaterialEntryForm] = MaterialEntryForm
    template_name: str = "workflow/create_material_entry.html"

    def form_valid(self, form: MaterialEntryForm) -> JsonResponse:
        material_entry: MaterialEntry = form.save(commit=False)
        material_entry.job_pricing = get_object_or_404(JobPricing, pk=self.kwargs['job_pricing_id'])
        material_entry.save()

        # Update the last_updated field of the associated job
        job = material_entry.job_pricing.job
        job.save(update_fields=["last_updated"])

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('edit_job_pricing', kwargs={'pk': self.object.job_pricing.pk})

    def form_invalid(self, form: MaterialEntryForm) -> JsonResponse:
        logger.debug("Form errors: %s", form.errors)
        return super().form_invalid(form)


class MaterialEntryUpdateView(UpdateView):
    model: Type[MaterialEntry] = MaterialEntry
    form_class: Type[MaterialEntryForm] = MaterialEntryForm
    template_name: str = "workflow/edit_material_entry.html"

    def form_valid(self, form: MaterialEntryForm) -> JsonResponse:
        material_entry: MaterialEntry = form.save(commit=False)
        material_entry.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('edit_job_pricing', kwargs={'pk': self.object.job_pricing.pk})
