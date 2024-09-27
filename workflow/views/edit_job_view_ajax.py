import json
import logging

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt

from workflow.forms import JobPricingForm, JobForm, TimeEntryForm, MaterialEntryForm, AdjustmentEntryForm
from workflow.models import Job, JobPricing, TimeEntry

logger = logging.getLogger(__name__)


def edit_job_view_ajax(request, job_id=None):
    # Log the job ID and request method for context
    if job_id:
        logger.debug(f"Entering edit_job_view_ajax with job_id: {job_id}")
    else:
        logger.debug("Entering edit_job_view_ajax with no job_id (creating a new job)")

    logger.debug(f"Request method: {request.method}")
    logger.debug(f"Request parameters: {request.GET if request.method == 'GET' else request.POST}")

    # Fetch the job or create a new one if job_id is not provided
    if job_id:
        job = get_object_or_404(Job, id=job_id)
        logger.debug(f"Editing existing job with Job Number: {job.job_number}, ID: {job.id}")
    else:
        job = Job.objects.create()
        logger.debug(f"Created a new job with ID: {job.id}")

    logger.debug(f"Job Details: {job}")

    # Get or create JobPricing instances for the 'estimate', 'quote', and 'reality' sections
    estimate, est_created = JobPricing.objects.get_or_create(job=job, pricing_stage='estimate')
    quote, quote_created = JobPricing.objects.get_or_create(job=job, pricing_stage='quote')
    reality, real_created = JobPricing.objects.get_or_create(job=job, pricing_stage='reality')
    logger.debug(f"JobPricing instances: estimate {'created' if est_created else 'retrieved'}, "
                 f"quote {'created' if quote_created else 'retrieved'}, "
                 f"reality {'created' if real_created else 'retrieved'}")

    # Create forms without handling POST since autosave handles form submissions
    job_form = JobForm(instance=job)
    estimate_form = JobPricingForm(instance=estimate, prefix="estimate")
    quote_form = JobPricingForm(instance=quote, prefix="quote")
    reality_form = JobPricingForm(instance=reality, prefix="reality")

    # Create entry forms for each section
    def create_entry_forms(section_name, job_pricing):
        return {
            'time': [TimeEntryForm(prefix=f"{section_name}_time_{i}", instance=entry)
                     for i, entry in enumerate(job_pricing.time_entries.all())],
            'material': [MaterialEntryForm(prefix=f"{section_name}_material_{i}", instance=entry)
                         for i, entry in enumerate(job_pricing.material_entries.all())],
            'adjustment': [AdjustmentEntryForm(prefix=f"{section_name}_adjustment_{i}", instance=entry)
                           for i, entry in enumerate(job_pricing.adjustment_entries.all())]
        }

    sections = {'estimate': estimate, 'quote': quote, 'reality': reality}
    entry_forms = {section_name: create_entry_forms(section_name, job_pricing) for section_name, job_pricing in sections.items()}

    # Log the entry form counts for each section
    for section_name, forms in entry_forms.items():
        logger.debug(f"{section_name.capitalize()} section: "
                     f"{len(forms['time'])} time entries, "
                     f"{len(forms['material'])} material entries, "
                     f"{len(forms['adjustment'])} adjustment entries")

    # Render the job context to the template
    context = {
        'job_form': job_form,
        'estimate_form': estimate_form,
        'quote_form': quote_form,
        'reality_form': reality_form,
        'entry_forms': entry_forms,
    }

    logger.debug(f"Rendering template for job {job.id} with job number {job.job_number}")
    return render(request, 'jobs/edit_job_ajax.html', context)


@csrf_exempt
def autosave_job_view(request):
    if request.method == 'POST':
        try:
            # Old logic follows
            #     if request.method == 'POST':
            #         logger.info(f"Processing POST request for job {job.id}")
            #         all_valid = all([job_form.is_valid(), estimate_form.is_valid(), quote_form.is_valid(), reality_form.is_valid()])
            #         logger.info(f"Main forms valid: {all_valid}")
            #
            #         if all_valid:
            #             job = job_form.save()
            #             estimate = estimate_form.save()
            #             quote = quote_form.save()
            #             reality = reality_form.save()
            #             logger.info(f"Saved main forms for job {job.id}")
            #
            #             for section_name, job_pricing in sections:
            #                 for entry_type in ['time', 'material', 'adjustment']:
            #                     for i, form in enumerate(entry_forms[section_name][entry_type]):
            #                         if form.is_valid():
            #                             entry = form.save(commit=False)
            #                             entry.job_pricing = job_pricing
            #                             entry.save()
            #                             logger.info(f"Saved {entry_type} entry {i} for {section_name} section")
            #                         else:
            #                             logger.error(
            #                                 f"Invalid {entry_type} entry form {i} in {section_name} section: {form.errors}")
            #
            #             logger.info(f"Successfully saved job {job.id} and all related data")
            #             return redirect('job_list')  # or wherever you want to redirect after saving
            #         else:
            #             logger.error("Form validation failed")
            #             if not job_form.is_valid():
            #                 logger.error(f"Job form errors: {job_form.errors}")
            #             if not estimate_form.is_valid():
            #                 logger.error(f"Estimate form errors: {estimate_form.errors}")
            #             if not quote_form.is_valid():
            #                 logger.error(f"Quote form errors: {quote_form.errors}")
            #             if not reality_form.is_valid():
            #                 logger.error(f"Reality form errors: {reality_form.errors}")
            # Log incoming request
            logger.debug("Autosave request received")

            # Parse the incoming JSON data
            data = json.loads(request.body)
            logger.debug(f"Parsed data: {data}")

            # Retrieve the job by ID
            job_id = data.get('job_id')
            if not job_id:
                logger.error("Job ID missing in data")
                return JsonResponse({'error': 'Job ID missing'}, status=400)

            job = Job.objects.get(id=job_id)
            logger.debug(f"Job found: {job}")

            # Update or create related entries like pricing, time entries, etc.
            estimate_data = data.get('estimate', {})
            logger.debug(f"Estimate data: {estimate_data}")

            # Fetch the estimate pricing stage for the job
            estimate = job.pricings.filter(pricing_stage='estimate').order_by('-created_at').first()
            if not estimate:
                logger.error("Estimate pricing stage not found")
                return JsonResponse({'error': 'Estimate pricing stage not found'}, status=400)

            # Update time entries
            time_entries_data = estimate_data.get('time', [])
            logger.debug(f"Time entries to update: {time_entries_data}")

            for time_entry_data in time_entries_data:
                TimeEntry.objects.update_or_create(
                    job_pricing=estimate,
                    defaults={
                        'description': time_entry_data.get('description', ''),
                        'items': time_entry_data.get('items', 0),
                        'mins_per_item': time_entry_data.get('minsPerItem', 0),
                        'rate': time_entry_data.get('rate', 0),
                        'total': time_entry_data.get('total', 0),
                    }
                )
                logger.debug(f"Updated/created time entry: {time_entry_data}")

            logger.debug(f"Successfully saved job {job.id} and all related data")
            return JsonResponse({'status': 'success'}, status=200)

        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
    else:
        logger.error("Invalid request method")
        return JsonResponse({'error': 'Invalid method'}, status=405)
