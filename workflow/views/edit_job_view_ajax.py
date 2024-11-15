import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from workflow.models import Job
from workflow.serializers import JobSerializer, JobPricingSerializer
from workflow.services.job_service import get_job_with_pricings, \
    get_latest_job_pricings, get_historical_job_pricings

from workflow.helpers import get_company_defaults

logger = logging.getLogger(__name__)

def create_job_view(request):
    return render(request, "jobs/create_job_and_redirect.html")


@require_http_methods(["POST"])
def create_job_api(request):
    try:
        # Create the job with default values using the service function
        new_job = Job.objects.create()

        # Log that the job and pricings have been created successfully
        logger.debug(f"New job created with ID: {new_job.id}")

        # Return the job_id as a JSON response
        return JsonResponse({"job_id": str(new_job.id)}, status=201)

    except Exception as e:
        # Log the exception and return a JSON error response in case of unexpected failures
        logger.exception("Error creating job")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_job_api(request):
    job_id = request.GET.get("job_id")

    if not job_id:
        return JsonResponse({"error": "Missing job_id"}, status=400)

    try:
        # Use the service layer to get the job and its related pricings
        job = get_job_with_pricings(job_id)

        # Use the service layer to get the latest pricing for each stage
        latest_pricings = get_latest_job_pricings(job)

        job_client = job.client.name if job.client else "No Client"
        logger.debug(
            f"Retrieving job with Job Number: {job.job_number}, ID: {job.id}, Client Name: {job_client}"
        )

        # Prepare response data with job pricings
        response_data = {
            "id": str(job.id),
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "client": job_client,
            "estimate_pricing": {
                "pricing_stage": latest_pricings["estimate"].pricing_stage if latest_pricings["estimate"] else None,
                "pricing_type": latest_pricings["estimate"].pricing_type if latest_pricings["estimate"] else None,
            },
            "quote_pricing": {
                "pricing_stage": latest_pricings["quote"].pricing_stage if latest_pricings["quote"] else None,
                "pricing_type": latest_pricings["quote"].pricing_type if latest_pricings["quote"] else None,
            },
            "reality_pricing": {
                "pricing_stage": latest_pricings["reality"].pricing_stage if latest_pricings["reality"] else None,
                "pricing_type": latest_pricings["reality"].pricing_type if latest_pricings["reality"] else None,
            },
        }

        return JsonResponse(response_data, safe=False)

    except Job.DoesNotExist:
        return JsonResponse({"error": "Job not found"}, status=404)

    except Exception as e:
        logger.exception("Unexpected error during get_job_api")
        return JsonResponse({"error": "Unexpected error"}, status=500)


@require_http_methods(["GET"])
def fetch_job_pricing_api(request):
    job_id = request.GET.get("job_id")
    pricing_type = request.GET.get("pricing_type")

    if not job_id or not pricing_type:
        return JsonResponse({"error": "Missing job_id or pricing_type"}, status=400)

    try:
        # Retrieve the job with related pricings using the service function
        job = get_job_with_pricings(job_id)

        # Retrieve the pricing data by filtering the job pricings based on pricing_type
        pricing_data = job.pricings.filter(pricing_type=pricing_type).values()

        if not pricing_data.exists():
            return JsonResponse(
                {"error": "No data found for the provided job_id and pricing_type"},
                status=404,
            )

        # Convert pricing data to a list since JsonResponse cannot serialize QuerySets directly
        return JsonResponse(list(pricing_data), safe=False)

    except Job.DoesNotExist:
        return JsonResponse({"error": "Job not found"}, status=404)

    except Exception as e:
        # Log the unexpected error and return an error response
        logger.exception("Unexpected error during fetch_job_pricing_api")
        return JsonResponse({"error": str(e)}, status=500)


def form_to_dict(form):
    if form.is_valid():
        return form.cleaned_data
    else:
        return form.initial

@require_http_methods(["GET", "POST"])
def edit_job_view_ajax(request, job_id=None):
    if job_id:
        # Fetch the existing Job along with pricings
        job = get_job_with_pricings(job_id)
        logger.debug(f"Editing existing job with ID: {job.id}")
    else:
        # Note: I don't think this is ever called because create_job_and_redirect.html creates it first
        # Create a new Job using the service layer function
        job = create_new_job()
        logger.debug(f"Created a new job with ID: {job.id}")

    # Fetch All Job Pricing Revisions for Each Pricing Stage
    historical_job_pricings = get_historical_job_pricings(job)

    # Serialize the historical pricings without sections
    historical_job_pricings_serialized = [
        JobPricingSerializer(pricing).data
        for pricing in historical_job_pricings
    ]

    # Fetch the Latest Revision for Each Pricing Stage
    latest_job_pricings = get_latest_job_pricings(job)


    # Include the Latest Revision Data
    latest_job_pricings_serialized = {
        section_name: JobPricingSerializer(latest_pricing).data
        for section_name, latest_pricing in latest_job_pricings.items()
    }

    # Serialize the job pricings data to JSON
    historical_job_pricings_json = json.dumps(historical_job_pricings_serialized)
    latest_job_pricings_json = json.dumps(latest_job_pricings_serialized)

    # Get company defaults for any shared settings or values
    company_defaults = get_company_defaults()

    # Prepare the context to pass to the template
    context = {
        "job": job,
        "job_id": job.id,
        "company_defaults": company_defaults,
        "historical_job_pricings_json": historical_job_pricings_json,  # Revisions
        "latest_job_pricings_json": latest_job_pricings_json,  # Latest version
    }

    logger.debug(f"Rendering template for job {job.id} with job number {job.job_number}")
    try:
        # Dump the context to JSON for logging
        logger.debug(f"Historical pricing being passed to template: {json.dumps(historical_job_pricings_json)}")
        logger.debug(f"Latest pricing being passed to template: {json.dumps(latest_job_pricings_json)}")
    except Exception as e:
        logger.error(f"Error while dumping context: {e}")

    # Render the Template
    return render(request, "jobs/edit_job_ajax.html", context)



# Note, recommended to remove the exemption in the future
@require_http_methods(["POST"])
def autosave_job_view(request):
    try:
        logger.debug("Autosave request received")

        # Step 1: Parse the incoming JSON data
        data = json.loads(request.body)
        logger.debug(f"Parsed data: {data}")

        # Step 2: Retrieve the job by ID
        job_id = data.get("job_id")
        if not job_id:
            logger.error("Job ID missing in data")
            return JsonResponse({"error": "Job ID missing"}, status=400)

        # Fetch the existing job along with all pricings
        job = get_job_with_pricings(job_id)
        logger.debug(f"Job found: {job}")

        # Step 3: Pass the job and incoming data to a dedicated serializer
        # Add context with request
        serializer = JobSerializer(
            instance=job,
            data=data,
            partial=True,
            context={'request': request}
        )

        logger.debug(f"Initial serializer data: {serializer.initial_data}")

        if serializer.is_valid():
            logger.debug(f"Validated data: {serializer.validated_data}")
            serializer.save()

            # Logging client name for better traceability
            client_name = job.client.name if job.client else "No Client"

            logger.debug(
                f"Job {job_id} successfully autosaved. Current Client: {client_name}, contact_person: {job.contact_person}"
            )
            logger.debug(
                f"job_name={job.name}, order_number={job.order_number}, contact_phone={job.contact_phone}"
            )

            return JsonResponse({"success": True, "job_id": job.id})
        else:
            logger.error(f"Validation errors: {serializer.errors}")
            return JsonResponse({"success": False, "errors": serializer.errors}, status=400)

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON")
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    except Exception as e:
        logger.exception("Unexpected error during autosave")
        return JsonResponse({"error": "Unexpected error"}, status=500)
