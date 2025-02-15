# kanban.py

import json
from uuid import UUID

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
    return render(request, "jobs/kanban_board.html", context)


@csrf_exempt
def update_job_status(request: HttpRequest, job_id: UUID) -> HttpResponse:
    if request.method == "POST":
        try:
            job = Job.objects.get(pk=job_id)
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
    try:
        page = int(request.GET.get("page", 1))
        page_size = min(
            int(request.GET.get("page_size", 10)), 100
        )  # Limits to maximum 100 jobs per page
        offset = (page - 1) * page_size

        total_jobs = Job.objects.filter(status=status).count()  # Total counter
        jobs = Job.objects.filter(status=status).order_by("-created_at")[
            offset : offset + page_size
        ]

        job_data = [
            {
                "id": job.id,
                "name": job.name,
                "description": job.description,
                "job_number": job.job_number,
                "client_name": job.client.name if job.client else "",
                "contact_person": job.contact_person,
                "status": job.get_status_display(),
                "paid": job.paid,
            }
            for job in jobs
        ]

        return JsonResponse(
            {
                "jobs": job_data,
                "total_jobs": total_jobs,
                "current_page": page,
                "page_size": page_size,
                "has_next": (offset + page_size)
                < total_jobs,  # Indicates if there are more jobs to load
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
