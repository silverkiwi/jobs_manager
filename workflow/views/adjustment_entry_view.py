# workflow/views/adjustment_entry_views.py

import logging
from typing import Type

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from workflow.forms import AdjustmentEntryForm
from workflow.models import JobPricing, AdjustmentEntry

logger = logging.getLogger(__name__)


class CreateAdjustmentEntryView(CreateView):
    model: Type[AdjustmentEntry] = AdjustmentEntry
    form_class: Type[AdjustmentEntryForm] = AdjustmentEntryForm
    template_name: str = "workflow/create_adjustment_entry.html"

    def form_valid(self, form: AdjustmentEntryForm) -> JsonResponse:
        adjustment_entry: AdjustmentEntry = form.save(commit=False)
        adjustment_entry.job_pricing = get_object_or_404(JobPricing, pk=self.kwargs['job_pricing_id'])
        adjustment_entry.save()

        # Update the last_updated field of the associated job
        job = adjustment_entry.job_pricing.job
        job.save(update_fields=["last_updated"])

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('edit_job_pricing', kwargs={'pk': self.object.job_pricing.pk})

    def form_invalid(self, form: AdjustmentEntryForm) -> JsonResponse:
        logger.debug("Form errors: %s", form.errors)
        return super().form_invalid(form)


class AdjustmentEntryUpdateView(UpdateView):
    model: Type[AdjustmentEntry] = AdjustmentEntry
    form_class: Type[AdjustmentEntryForm] = AdjustmentEntryForm
    template_name: str = "workflow/edit_adjustment_entry.html"

    def form_valid(self, form: AdjustmentEntryForm) -> JsonResponse:
        adjustment_entry: AdjustmentEntry = form.save(commit=False)
        adjustment_entry.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('edit_job_pricing', kwargs={'pk': self.object.job_pricing.pk})
