import json
import logging

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from workflow.forms import JobPricingForm, JobForm, TimeEntryForm, MaterialEntryForm, AdjustmentEntryForm
from workflow.helpers import get_company_defaults
from workflow.models import Job, JobPricing, TimeEntry, CompanyDefaults, MaterialEntry, AdjustmentEntry

logger = logging.getLogger(__name__)

def create_job_view(request):
    return render(request, 'jobs/create_job_and_redirect.html')


@require_http_methods(["POST"])
def create_job_api(request):
    try:
        # Create the job with default values
        new_job = Job.objects.create()

        # Return the job_id as a JSON response
        return JsonResponse({'job_id': str(new_job.id)}, status=201)

    except Exception as e:
        # Return a JSON error response in case of unexpected failures
        return JsonResponse({'error': str(e)}, status=500)


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

    company_defaults = get_company_defaults()

    # Log the entry form counts for each section
    for section_name, forms in entry_forms.items():
        logger.debug(f"{section_name.capitalize()} section: "
                     f"{len(forms['time'])} time entries, "
                     f"{len(forms['material'])} material entries, "
                     f"{len(forms['adjustment'])} adjustment entries")

    # Render the job context to the template
    context = {
        'job_form': job_form,
        'job_id': job.id,
        'company_defaults': company_defaults,
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
            logger.debug("Autosave request received")

            # Parse the incoming JSON data
            data = json.loads(request.body)
            logger.debug(f"Parsed data: {data}")

            # Retrieve the job by ID
            job_id = data.get('id')
            if not job_id:
                logger.error("Job ID missing in data")
                return JsonResponse({'error': 'Job ID missing'}, status=400)

            job = Job.objects.get(id=job_id)
            logger.debug(f"Job found: {job}")

            # Update job-level fields (Job fields shown on screen)
            job.name = data.get('name', job.name)
            job.client_id = data.get('client', job.client_id)  # Handle client_id separately
            job.order_number = data.get('order_number', job.order_number)
            job.contact_person = data.get('contact_person', job.contact_person)
            job.contact_phone = data.get('contact_phone', job.contact_phone)
            job.job_number = data.get('job_number', job.job_number)
            job.description = data.get('description', job.description)
            job.paid = data.get('paid', job.paid)  # Handle paid
            job.status = data.get('status', job.status)  # Handle status
            job.quote_acceptance_date = data.get('quote_acceptance_date', job.quote_acceptance_date)  # Workflow Settings
            job.delivery_date = data.get('delivery_date', job.delivery_date)  # Workflow Settings

            # Save the job instance after updating the fields
            job.save()
            logger.debug(f"Job {job.id} updated and saved successfully")

            # Now handle the Job Pricing sections: Estimate, Quote, Reality
            sections = ['estimate', 'quote', 'reality']
            for section in sections:
                section_data = data.get(section, {})
                logger.debug(f"{section.capitalize()} section data: {section_data}")

                # Fetch the pricing stage for the current section
                pricing_stage = job.pricings.filter(pricing_stage=section).order_by('-created_at').first()
                if not pricing_stage:
                    logger.error(f"{section.capitalize()} pricing stage not found")
                    return JsonResponse({'error': f'{section.capitalize()} pricing stage not found'}, status=400)

                # Process the time entries for the current section
                time_entries_data = section_data.get('time', [])
                logger.debug(f"{section.capitalize()} time entries: {time_entries_data}")
                for time_entry_data in time_entries_data:
                    if time_entry_data.get('total', 0) == 0:  # Skip dummy time entries
                        logger.debug(f"Skipping dummy time entry: {time_entry_data}")
                        continue
                    TimeEntry.objects.update_or_create(
                        job_pricing=pricing_stage,
                        defaults={
                            'description': time_entry_data.get('description', ''),
                            'items': time_entry_data.get('items', 0),
                            'mins_per_item': time_entry_data.get('mins_per_item', 0),
                            'charge_out_rate': time_entry_data.get('charge_out_rate', 0),
                            'wage_rate': time_entry_data.get('wage_rate', 0),  # Should look up defaults
                            'staff': time_entry_data.get('staff', None), # Only applies to reality so can be None
                            'date': time_entry_data.get('date', None),  # Only applies to reality so can be None
                        }
                    )

                # Process the material entries for the current section
                material_entries_data = section_data.get('materials', [])
                logger.debug(f"{section.capitalize()} material entries: {material_entries_data}")
                for material_entry_data in material_entries_data:
                    if material_entry_data.get('total', 0) == 0:  # Skip dummy material entries
                        logger.debug(f"Skipping dummy material entry: {material_entry_data}")
                        continue
                    MaterialEntry.objects.update_or_create(
                        job_pricing=pricing_stage,
                        defaults={
                            'item_code': material_entry_data.get('item_code', ''),
                            'description': material_entry_data.get('description', ''),
                            'quantity': material_entry_data.get('quantity', 0),
                            'unit_cost': material_entry_data.get('cost_rate', 0),
                            'unit_revenue': material_entry_data.get('retail_rate', 0),
#                            'total': material_entry_data.get('total', 0),
                            'comments': material_entry_data.get('comments', ''),
                        }
                    )

                # Process the adjustment entries for the current section
                adjustment_entries_data = section_data.get('adjustments', [])
                logger.debug(f"{section.capitalize()} adjustment entries: {adjustment_entries_data}")
                for adjustment_entry_data in adjustment_entries_data:
                    if adjustment_entry_data.get('total', 0) == 0:  # Skip dummy adjustment entries
                        logger.debug(f"Skipping dummy adjustment entry: {adjustment_entry_data}")
                        continue
                    AdjustmentEntry.objects.update_or_create(
                        job_pricing=pricing_stage,
                        defaults={
                            'description': adjustment_entry_data.get('description', ''),
                            'cost_adjustment': adjustment_entry_data.get('cost_adjustment', 0),
                            'price_adjustment': adjustment_entry_data.get('total', 0),
                            'comments': adjustment_entry_data.get('comments', ''),
                        }
                    )

            logger.debug(f"Successfully saved job {job.id} and all related data (Estimate, Quote, Reality)")
            return JsonResponse({'status': 'success'}, status=200)

        except Exception as e:
            logger.error(f"Error occurred: {str(e)}")
            logger.exception(e)  # Log the stack trace for better debugging
            return JsonResponse({'error': str(e)}, status=400)
    else:
        logger.error("Invalid request method")
        return JsonResponse({'error': 'Invalid method'}, status=405)
