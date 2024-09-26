import json
import logging

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt

from workflow.forms import JobPricingForm, JobForm, TimeEntryForm, MaterialEntryForm, AdjustmentEntryForm
from workflow.models import Job, JobPricing

logger = logging.getLogger(__name__)


def edit_job_view_ajax(request, job_id=None):
    logger.info(f"Entering edit_job_view_ajax with job_id: {job_id}")

    if job_id:
        job = get_object_or_404(Job, id=job_id)
        logger.info(f"Editing existing job {job.job_number}")
    else:
        job = Job.objects.create()
        logger.info(f"Created new job with id: {job.id}")

    # Get or create JobPricing instances for each section
    estimate, est_created = JobPricing.objects.get_or_create(job=job, pricing_stage='estimate')
    quote, quote_created = JobPricing.objects.get_or_create(job=job, pricing_stage='quote')
    reality, real_created = JobPricing.objects.get_or_create(job=job, pricing_stage='reality')
    logger.info(f"JobPricing instances: estimate {'created' if est_created else 'retrieved'}, "
                f"quote {'created' if quote_created else 'retrieved'}, "
                f"reality {'created' if real_created else 'retrieved'}")

    # Create forms
    job_form = JobForm(request.POST or None, instance=job)
    estimate_form = JobPricingForm(request.POST or None, instance=estimate, prefix="estimate")
    quote_form = JobPricingForm(request.POST or None, instance=quote, prefix="quote")
    reality_form = JobPricingForm(request.POST or None, instance=reality, prefix="reality")

    # Create entry forms for each section
    sections = [
        ('estimate', estimate),
        ('quote', quote),
        ('reality', reality)
    ]

    entry_forms = {}
    for section_name, job_pricing in sections:
        entry_forms[section_name] = {
            'time': [TimeEntryForm(request.POST or None, prefix=f"{section_name}_time_{i}", instance=entry)
                     for i, entry in enumerate(job_pricing.time_entries.all())],
            'material': [MaterialEntryForm(request.POST or None, prefix=f"{section_name}_material_{i}", instance=entry)
                         for i, entry in enumerate(job_pricing.material_entries.all())],
            'adjustment': [
                AdjustmentEntryForm(request.POST or None, prefix=f"{section_name}_adjustment_{i}", instance=entry)
                for i, entry in enumerate(job_pricing.adjustment_entries.all())]
        }
        logger.info(f"{section_name.capitalize()} section: {len(entry_forms[section_name]['time'])} time entries, "
                    f"{len(entry_forms[section_name]['material'])} material entries, "
                    f"{len(entry_forms[section_name]['adjustment'])} adjustment entries")

    if request.method == 'POST':
        logger.info(f"Processing POST request for job {job.id}")
        all_valid = all([job_form.is_valid(), estimate_form.is_valid(), quote_form.is_valid(), reality_form.is_valid()])
        logger.info(f"Main forms valid: {all_valid}")

        if all_valid:
            job = job_form.save()
            estimate = estimate_form.save()
            quote = quote_form.save()
            reality = reality_form.save()
            logger.info(f"Saved main forms for job {job.id}")

            for section_name, job_pricing in sections:
                for entry_type in ['time', 'material', 'adjustment']:
                    for i, form in enumerate(entry_forms[section_name][entry_type]):
                        if form.is_valid():
                            entry = form.save(commit=False)
                            entry.job_pricing = job_pricing
                            entry.save()
                            logger.info(f"Saved {entry_type} entry {i} for {section_name} section")
                        else:
                            logger.error(
                                f"Invalid {entry_type} entry form {i} in {section_name} section: {form.errors}")

            logger.info(f"Successfully saved job {job.id} and all related data")
            return redirect('job_list')  # or wherever you want to redirect after saving
        else:
            logger.error("Form validation failed")
            if not job_form.is_valid():
                logger.error(f"Job form errors: {job_form.errors}")
            if not estimate_form.is_valid():
                logger.error(f"Estimate form errors: {estimate_form.errors}")
            if not quote_form.is_valid():
                logger.error(f"Quote form errors: {quote_form.errors}")
            if not reality_form.is_valid():
                logger.error(f"Reality form errors: {reality_form.errors}")

    context = {
        'job_form': job_form,
        'estimate_form': estimate_form,
        'quote_form': quote_form,
        'reality_form': reality_form,
        'entry_forms': entry_forms,
    }

    logger.info(f"Rendering template for job {job.id}")
    return render(request, 'jobs/edit_job_ajax.html', context)


@csrf_exempt
def autosave_job_view(request):
    if request.method == 'POST':
        try:
            # Parse the incoming JSON data
            data = json.loads(request.body)

            # Process the data (save to database, update models, etc.)
            # For example, update job entries based on the data
            # job = Job.objects.get(id=data['job_id'])
            # job.update(...)

            return JsonResponse({'status': 'success'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'Invalid method'}, status=405)
