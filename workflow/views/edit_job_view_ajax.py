# views/ajax_edit_job_view.py
import logging

# This is the prettier view which combines all the forms into one view

from django.shortcuts import render, get_object_or_404, redirect
from workflow.forms import JobPricingForm, JobForm, TimeEntryForm, MaterialEntryForm, AdjustmentEntryForm
from workflow.models import TimeEntry, MaterialEntry, AdjustmentEntry, Job, JobPricing

logger = logging.getLogger(__name__)

def edit_job_view_ajax(request, job_id=None):
    # Fetch the job if updating, or create a new one if job_id is None
    if job_id:
        job = get_object_or_404(Job, id=job_id)
        logger.debug(f"Editing job {job.job_number}")
    else:
        job = Job.objects.create()  # Create a new job
        active_estimate = JobPricing.objects.create(job=job, pricing_stage='estimate')
        active_quote = JobPricing.objects.create(job=job, pricing_stage='quote')
        active_reality = JobPricing.objects.create(job=job, pricing_stage='reality')
        logger.debug(f"New job created: {job.job_number}")

    # For existing jobs, get the latest active entries
    if job_id:
        active_estimate = job.pricings.filter(pricing_stage='estimate').order_by('-created_at').first()
        active_quote = job.pricings.filter(pricing_stage='quote').order_by('-created_at').first()
        active_reality = job.pricings.filter(pricing_stage='reality').order_by('-created_at').first()

    # Initialize the forms for job, estimate, quote, and reality
    job_form = JobForm(request.POST or None, instance=job)
    estimate_form = JobPricingForm(request.POST or None, instance=active_estimate, prefix="estimate")
    quote_form = JobPricingForm(request.POST or None, instance=active_quote, prefix="quote")
    reality_form = JobPricingForm(request.POST or None, instance=active_reality, prefix="reality")

    # Time, materials, and adjustments (related to the active estimate)
    time_entry_forms = [TimeEntryForm(request.POST or None, prefix=str(i), instance=entry) for i, entry in enumerate(active_estimate.time_entries.all())] if active_estimate else []
    material_entry_forms = [MaterialEntryForm(request.POST or None, prefix=str(i), instance=entry) for i, entry in enumerate(active_estimate.material_entries.all())] if active_estimate else []
    adjustment_entry_forms = [AdjustmentEntryForm(request.POST or None, prefix=str(i), instance=entry) for i, entry in enumerate(active_estimate.adjustment_entries.all())] if active_estimate else []

    if request.method == 'POST':
        all_forms_valid = True

        # Validate the job, estimate, quote, and reality forms
        if not job_form.is_valid() or not estimate_form.is_valid() or not quote_form.is_valid() or not reality_form.is_valid():
            all_forms_valid = False

        # Validate time entry forms
        for time_form in time_entry_forms:
            if not time_form.is_valid():
                all_forms_valid = False

        # Validate material entry forms
        for material_form in material_entry_forms:
            if not material_form.is_valid():
                all_forms_valid = False

        # Validate adjustment entry forms
        for adjustment_form in adjustment_entry_forms:
            if not adjustment_form.is_valid():
                all_forms_valid = False

        # If all forms are valid, save everything
        if all_forms_valid:
            job = job_form.save()

            # Save the estimate, quote, and reality
            estimate = estimate_form.save(commit=False)
            estimate.job = job
            estimate.save()

            quote = quote_form.save(commit=False)
            quote.job = job
            quote.save()

            reality = reality_form.save(commit=False)
            reality.job = job
            reality.save()

            # Save time, materials, adjustments related to the estimate
            for time_form in time_entry_forms:
                time_form.save()

            for material_form in material_entry_forms:
                material_form.save()

            for adjustment_form in adjustment_entry_forms:
                adjustment_form.save()

            return redirect('/')
        else:
            logger.error("One or more forms were invalid. Not saving data.")

    context = {
        'job_form': job_form,
        'estimate_form': estimate_form,
        'quote_form': quote_form,
        'reality_form': reality_form,
        'time_entry_forms': time_entry_forms,
        'material_entry_forms': material_entry_forms,
        'adjustment_entry_forms': adjustment_entry_forms,
    }

    return render(request, 'workflow/edit_job_ajax.html', context)
