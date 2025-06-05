import logging
import json
from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.db import transaction
from django.db.models import Q, Max
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from apps.job.models import Job

logger = logging.getLogger(__name__)


def kanban_view(request: HttpRequest) -> HttpResponse:
    active_jobs = Job.objects.filter(~Q(status="archived")).order_by("status", "priority")

    archived_jobs = Job.objects.filter(status="archived").order_by("-created_at")[:50]

    active_status_choices = [(key, label) for key, label in Job.JOB_STATUS_CHOICES if key != "archived"]
    active_status_tooltips = {key: Job.STATUS_TOOLTIPS[key] for key in Job.STATUS_TOOLTIPS if key != "archived"}
    context = {
        "jobs": active_jobs,
        "latest_archived_jobs": archived_jobs,
        "status_choices": active_status_choices,
        "status_tooltips": active_status_tooltips,
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


def _get_adjacent_priorities(before_id: str, after_id: str) -> tuple[int | None, int | None]:
    """
    Return (before_priority, after_priority), fetching from DB if IDs are provided.
    If an ID is invalid or the job does not exist, raises Job.DoesNotExist.
    """
    before_prio = None
    after_prio = None

    if before_id:
        before_prio = Job.objects.get(pk=before_id).priority
    if after_id:
        after_prio = Job.objects.get(pk=after_id).priority

    return before_prio, after_prio


def _rebalance_column(status: str) -> None:
    """
    Renumber all jobs in the given status so that priorities become:
    1 * INCREMENT, 2 * INCREMENT, 3 * INCREMENT, … in ascending order.
    """
    increment = Job.PRIORITY_INCREMENT
    jobs = list(Job.objects.filter(status=status).order_by("priority"))

    with transaction.atomic():
        for index, job in enumerate(jobs, start=1):
            job.priority = index * increment
            job.save(update_fields=["priority"])


def _calculate_priority(before_prio: int | None, after_prio: int | None, status: str) -> int:
    """
    Determine the new priority given before_prio and after_prio.
    Cases:
      - (None, None): empty column or invalid payload → push to end
      - (None, after): top insertion
      - (before, None): bottom insertion
      - (before, after): internal insertion (average or rebalance if gap ≤ 1)
    """
    increment = Job.PRIORITY_INCREMENT

    match (before_prio, after_prio):
        case (None, None):
            # No adjacent jobs; place at end
            max_prio = Job.objects.filter(status=status).aggregate(Max("priority"))["priority__max"] or 0
            return max_prio + increment

        case (None, after) if after is not None:
            # Insert at top: place just above the ‘after’ job
            new_prio = after - increment
            if new_prio <= 0:
                _rebalance_column(status)
                # Re-fetch after_prio after rebalance
                after = Job.objects.get(priority=after, status=status).priority
                return after - increment
            return new_prio

        case (before, None) if before is not None:
            # Insert at bottom: place just below the ‘before’ job
            return before + increment

        case (before, after) if before is not None and after is not None:
            # Internal insertion: try to take the average
            gap = after - before
            if gap > 1:
                return (before + after) // 2
            # Gap too small → rebalance first, then recompute
            _rebalance_column(status)
            before = Job.objects.get(priority=before, status=status).priority
            after = Job.objects.get(priority=after, status=status).priority
            return (before + after) // 2

        case _:
            # Fallback: push to end if anything unexpected happens
            max_prio = Job.objects.filter(status=status).aggregate(Max("priority"))["priority__max"] or 0
            return max_prio + increment


@csrf_exempt
def reorder_job(request: HttpRequest, job_id: UUID) -> HttpResponse:
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method"})

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"})

    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        return JsonResponse({"success": False, "error": "Job not found"})

    before_id = payload.get("before_id")
    after_id = payload.get("after_id")
    new_status = payload.get("status")

    try:
        before_prio, after_prio = _get_adjacent_priorities(before_id, after_id)
    except Job.DoesNotExist:
        return JsonResponse({"success": False, "error": "Adjacent job not found"})

    # Determine and assign new priority (handles all edge cases internally)
    new_priority = _calculate_priority(before_prio, after_prio, job.status)
    job.priority = new_priority

    old_status = job.status 

    if new_status and new_status != job.status:
        job.status = new_status

    update_fields = ["priority"]
    if new_status and new_status != old_status:
        update_fields.insert(0, "status")

    job.save(update_fields=update_fields)
    return JsonResponse({"success": True, "message": "Job reordered successfully."})


def fetch_jobs(request: HttpRequest, status: str) -> JsonResponse:
    try:
        search_term = request.GET.get("search", "").strip()
        search_terms = search_term.split() if search_term else []

        jobs_query = Job.objects.filter(status=status)
        if search_terms:
            query = Q()
            for term in search_terms:
                # Each term should correspond to at least one field
                term_query = (
                    Q(name__icontains=term) |
                    Q(description__icontains=term) |
                    Q(client__name__icontains=term) |
                    Q(contact_person__icontains=term) |
                    Q(created_by__username__icontains=term)
                )
                query &= term_query
            jobs_query = jobs_query.filter(query)

        jobs = jobs_query.order_by("priority", "-created_at")

        total_jobs = Job.objects.filter(status=status).count()
        
        match status:
            case "archived":
                jobs = jobs[:100]
            case _:
                jobs = jobs[:200]
            
        total_filtered = jobs.count()

        logger.info(f"Found {total_jobs} jobs, returning {total_filtered} jobs")
        job_data = [
            {
                "id": job.id,
                "name": job.name,
                "description": job.description,
                "job_number": job.job_number,
                "client_name": job.client.name if job.client else "",
                "contact_person": job.contact_person,
                "people": [
                    {
                        "id": staff.id,
                        "display_name": staff.get_display_full_name(),
                        "icon": request.build_absolute_uri(staff.icon.url) if staff.icon else None,
                    }
                    for staff in job.people.all()
                ],
                "status": job.get_status_display(),
                "paid": job.paid,
                "created_by_id": job.created_by.id if job.created_by else None,
            }
            for job in jobs
        ]

        return JsonResponse({
            "success": True,
            "jobs": job_data,
            "total": total_jobs,
            "filtered_count": total_filtered,
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
    

def fetch_status_values(request: HttpRequest) -> JsonResponse:
    """Return available status values for Kanban"""
    try:
        status_choices = {key: label for key, label in Job.JOB_STATUS_CHOICES if key != "archived"}

        status_tooltips = {key: Job.STATUS_TOOLTIPS.get(key, "")
                           for key in status_choices.keys() if key in Job.STATUS_TOOLTIPS}
        
        return JsonResponse({
            "success": True,
            "statuses": status_choices,
            "tooltips": status_tooltips
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        })
    

def advanced_search(request: HttpRequest) -> JsonResponse:
    """Endpoint for advanced job search"""
    try:
        number = request.GET.get("job_number", "").strip()
        name = request.GET.get("name", "").strip()
        description = request.GET.get("description", "").strip()
        client_name = request.GET.get("client_name", "").strip()
        contact_person = request.GET.get("contact_person", "").strip()
        created_by = request.GET.get("created_by", "").strip()
        created_after = request.GET.get("created_after", "").strip()
        created_before = request.GET.get("created_before", "").strip()
        statuses = request.GET.getlist("status")
        paid = request.GET.get("paid")

        jobs_query = Job.objects.all()

        if number:
            jobs_query = jobs_query.filter(job_number=number)

        if name:
            jobs_query = jobs_query.filter(name__icontains=name)
        
        if description:
            jobs_query = jobs_query.filter(description__icontains=description)

        if client_name:
            jobs_query = jobs_query.filter(client__name__icontains=client_name)

        if contact_person:
            jobs_query = jobs_query.filter(contact_person__icontains=contact_person)
        
        if created_by:
            jobs_query = jobs_query.filter(events__staff=created_by)
            
        if created_after:
            jobs_query = jobs_query.filter(created_at__gte=created_after)
        
        if created_before:
            jobs_query = jobs_query.filter(created_at__lte=created_before)

        if statuses:
            jobs_query = jobs_query.filter(status__in=statuses)
        
        match paid:
            case "true":
                jobs_query = jobs_query.filter(paid=True)
            case "false":
                jobs_query = jobs_query.filter(paid=False)
        
        jobs = jobs_query.order_by("-created_at")

        job_data = [
            {
                "id": job.id,
                "name": job.name,
                "description": job.description,
                "job_number": job.job_number,
                "client_name": job.client.name if job.client else "",
                "people": [(staff.get_display_name(), staff.icon) for staff in job.people.all()],
                "contact_person": job.contact_person,
                "status": job.get_status_display(),
                "status_key": job.status,
                "created_by": job.created_by.get_display_name() if job.created_by else "",
                "created_at": job.created_at.strftime("%d/%m/%Y"),
                "paid": job.paid,
            }
            for job in jobs
        ]

        return JsonResponse({
            "success": True,
            "jobs": job_data,
            "total": len(job_data),
        })
    except Exception as e:
        logger.error(f"Error in advanced search: {e}")
        return JsonResponse({
            "success": False,
            "error": str(e)
        })
