import json
import logging

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from workflow.forms import (
    JobPricingForm,
    JobForm,
    TimeEntryForm,
    MaterialEntryForm,
    AdjustmentEntryForm,
)
from workflow.helpers import get_company_defaults
from workflow.models import (
    Job,
    JobPricing,
    TimeEntry,
    CompanyDefaults,
    MaterialEntry,
    AdjustmentEntry,
    Client,
)
from workflow.serializers import JobSerializer

logger = logging.getLogger(__name__)


def create_job_view(request):
    return render(request, "jobs/create_job_and_redirect.html")


@require_http_methods(["POST"])
def create_job_api(request):
    try:
        # Create the job with default values
        new_job = Job.objects.create()
        pricings = new_job.pricings.all()
        logger.debug("Pricings before manual creation")
        logger.debug(pricings)  # Should print 3 entries: estimate, quote, reality
        JobPricing.objects.create(job=new_job, pricing_stage="estimate")
        JobPricing.objects.create(job=new_job, pricing_stage="quote")
        JobPricing.objects.create(job=new_job, pricing_stage="reality")
        pricings = new_job.pricings.all()
        logger.debug("Pricings after manual creation")
        logger.debug(pricings)  # Should print 3 entries: estimate, quote, reality

        # Return the job_id as a JSON response
        return JsonResponse({"job_id": str(new_job.id)}, status=201)

    except Exception as e:
        # Return a JSON error response in case of unexpected failures
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_job_api(request):
    job_id = request.GET.get("job_id")

    if not job_id:
        return JsonResponse({"error": "Missing job_id"}, status=400)

    try:
        # Get the job and its related pricings
        job = get_object_or_404(
            Job.objects.select_related(
                "client"
            ).prefetch_related(  # Eagerly load the related client (1-to-1 relationship)
                "pricings__time_entries",  # Prefetch Time Entries related to each JobPricing
                "pricings__material_entries",  # Prefetch Material Entries related to each JobPricing
                "pricings__adjustment_entries",  # Prefetch Adjustment Entries related to each JobPricing
                "pricings__time_entries__staff",  # Prefetch Staff related to each Time Entry
            ),
            id=job_id,
        )

        # Retrieve the existing JobPricing instances for estimate, quote, and reality
        estimate = job.pricings.filter(pricing_stage="estimate").first()
        quote = job.pricings.filter(pricing_stage="quote").first()
        reality = job.pricings.filter(pricing_stage="reality").first()

        if not (estimate and quote and reality):
            return JsonResponse(
                {"error": "One or more job pricing stages are missing."}, status=500
            )

        job_client = job.client.name if job.client else "No Client"
        logger.debug(
            f"Editing existing job with Job Number: {job.job_number}, ID: {job.id}, Client Name: {job_client}"
        )

        # Prepare response data with job pricings
        response_data = {
            "id": str(job.id),
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "client": job_client,
            "estimate_pricing": {
                "pricing_stage": estimate.pricing_stage,
                "pricing_type": estimate.pricing_type,
            },
            "quote_pricing": {
                "pricing_stage": quote.pricing_stage,
                "pricing_type": quote.pricing_type,
            },
            "reality_pricing": {
                "pricing_stage": reality.pricing_stage,
                "pricing_type": reality.pricing_type,
            },
        }

        return JsonResponse(response_data, safe=False)

    except Job.DoesNotExist:
        return JsonResponse({"error": "Job not found"}, status=404)


@require_http_methods(["GET"])
def fetch_job_pricing_api(request):
    job_id = request.GET.get("job_id")
    pricing_type = request.GET.get("pricing_type")

    if not job_id or not pricing_type:
        return JsonResponse({"error": "Missing job_id or pricing_type"}, status=400)

    try:
        job = Job.objects.get(id=job_id)
        pricing_data = JobPricing.objects.filter(
            job=job, pricing_type=pricing_type
        ).values()

        if not pricing_data:
            return JsonResponse(
                {"error": "No data found for the provided job_id and pricing_type"},
                status=404,
            )

        return JsonResponse(list(pricing_data), safe=False)

    except Job.DoesNotExist:
        return JsonResponse({"error": "Job not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def form_to_dict(form):
    if form.is_valid():
        return form.cleaned_data
    else:
        return form.initial


def edit_job_view_ajax(request, job_id=None):
    # Log the job ID and request method for context
    if job_id:
        logger.debug(f"Entering edit_job_view_ajax with job_id: {job_id}")
    else:
        logger.debug("Entering edit_job_view_ajax with no job_id (creating a new job)")

    # logger.debug(f"Request method: {request.method}")
    # logger.debug(f"Request parameters: {request.GET if request.method == 'GET' else request.POST}")

    # Fetch the job or create a new one if job_id is not provided
    if job_id:
        job = get_object_or_404(
            Job.objects.select_related(
                "client"
            ).prefetch_related(  # Eagerly load the related client (1-to-1 relationship)
                "pricings__time_entries",  # Prefetch Time Entries related to each JobPricing
                "pricings__material_entries",  # Prefetch Material Entries related to each JobPricing
                "pricings__adjustment_entries",  # Prefetch Adjustment Entries related to each JobPricing
                "pricings__time_entries__staff",  # Prefetch Staff related to each Time Entry
            ),
            id=job_id,
        )
        job_client = job.client.name if job.client else "No Client"
        logger.debug(
            f"Editing existing job with Job Number: {job.job_number}, ID: {job.id}, Client Name: {job_client}"
        )
    else:
        job = Job.objects.create()
        logger.debug(f"Created a new job with ID: {job.id}")

    # logger.debug(f"Job Details: {job}")

    # Get or create JobPricing instances for the 'estimate', 'quote', and 'reality' sections
    estimate, est_created = JobPricing.objects.get_or_create(
        job=job, pricing_stage="estimate"
    )
    quote, quote_created = JobPricing.objects.get_or_create(
        job=job, pricing_stage="quote"
    )
    reality, real_created = JobPricing.objects.get_or_create(
        job=job, pricing_stage="reality"
    )
    # logger.debug(f"JobPricing instances: estimate {'created' if est_created else 'retrieved'}, "
    #              f"quote {'created' if quote_created else 'retrieved'}, "
    #              f"reality {'created' if real_created else 'retrieved'}")

    # Create forms without handling POST since autosave handles form submissions
    # Create entry forms for each section

    sections = {"estimate": estimate, "quote": quote, "reality": reality}
    entry_forms = {
        section_name: job_pricing.extract_pricing_data()
        for section_name, job_pricing in sections.items()
    }
    entry_forms_json = json.dumps(entry_forms)

    company_defaults = get_company_defaults()

    # Log the entry form counts for each section
    for section_name, forms in entry_forms.items():
        logger.debug(
            f"{section_name.capitalize()} section: "
            f"{len(forms['time'])} time entries, "
            f"{len(forms['material'])} material entries, "
            f"{len(forms['adjustment'])} adjustment entries"
        )

    # Render the job context to the template
    context = {
        "job": job,  # Add the job object to the context
        "job_id": job.id,
        "company_defaults": company_defaults,
        "entry_forms_json": entry_forms_json,
    }

    logger.debug(
        f"Rendering template for job {job.id} with job number {job.job_number}"
    )
    return render(request, "jobs/edit_job_ajax.html", context)


# Note, recommended to remove the exemption in the future
@require_http_methods(["POST"])
def autosave_job_view(request):
    try:
        logger.debug("Autosave request received")

        # Parse the incoming JSON data
        data = json.loads(request.body)
        logger.debug(f"Parsed data: {data}")

        # Retrieve the job by ID
        job_id = data.get("job_id")
        if not job_id:
            logger.error("Job ID missing in data")
            return JsonResponse({"error": "Job ID missing"}, status=400)

        job = get_object_or_404(Job, pk=job_id)
        logger.debug(f"Job found: {job}")

        # Use JobSerializer for validation and updating the job
        serializer = JobSerializer(
            instance=job, data=data
        )  # Note you can add partial=True to allow partial updates.  Not there as the JS sends the whole object.

        if serializer.is_valid():
            serializer.save()
            if job.client:
                client_name = job.client.name
            else:
                client_name = "No Client"

            logger.debug(
                f"Job {job_id} successfully autosaved. Current Client: {client_name}, contact_person: {job.contact_person}"
            )
            logger.debug(
                f"job_name={job.job_name}, order_number={job.order_number}, phone_contact={job.contact_phone}"
            )

            return JsonResponse({"success": True, "job_id": job.id})
        else:
            logger.error(f"Validation errors: {serializer.errors}")
            return JsonResponse(
                {"success": False, "errors": serializer.errors}, status=400
            )

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON")
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    except Job.DoesNotExist:
        logger.error(f"Job with id {job_id} does not exist")
        return JsonResponse({"error": "Job not found"}, status=404)

    except Exception as e:
        logger.exception("Unexpected error during autosave")
        return JsonResponse({"error": "Unexpected error"}, status=500)
