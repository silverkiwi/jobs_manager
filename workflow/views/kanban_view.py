# kanban.py

import json

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from workflow.models import Job


def kanban_view(request: HttpRequest) -> HttpResponse:
    jobs = Job.objects.all()
    context = {
        "jobs": jobs,
        "status_choices": Job.JOB_STATUS_CHOICES,
        "status_tooltips": Job.STATUS_TOOLTIPS,
    }
    return render(request, "workflow/kanban_board.html", context)


@csrf_exempt
def update_job_status(request: HttpRequest, pk: int) -> HttpResponse:
    if request.method == "POST":
        try:
            job = Job.objects.get(pk=pk)
            try:
                payload = json.loads(request.body)
                new_status = payload.get("status")
            except json.JSONDecodeError:
                return JsonResponse({"success": False, "error": "Invalid JSON"})

            if new_status:
                job.status = new_status
                job.save()
                return JsonResponse({"success": True})
            else:
                return JsonResponse({"success": False, "error": "Invalid status"})
        except Job.DoesNotExist:
            return JsonResponse({"success": False, "error": "Job not found"})
    return JsonResponse({"success": False, "error": "Invalid request method"})


def fetch_jobs(request: HttpRequest, status: str) -> JsonResponse:
    max_jobs = int(request.GET.get("max_jobs", 10))  # Default to 10 if not provided
    jobs = Job.objects.filter(status=status)[:max_jobs]
    total_jobs = Job.objects.filter(status=status).count()

    job_data = [
        {
            "id": job.id,
            "name": job.name,
            "description": job.description,
            "job_name": job.job_name,
            "job_number": job.job_number,
            "client_name": job.client_name,  # Add client name
            "contact_person": job.contact_person,  # Add contact person
            "status": job.get_status_display(),  # Human-readable status
            "paid": job.paid,  # Paid status
        }
        for job in jobs
    ]

    return JsonResponse({"jobs": job_data, "total": total_jobs})
