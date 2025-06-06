"""
Service layer for Kanban functionality.
Handles all business logic related to job management in the Kanban board.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from django.db import transaction
from django.db.models import Q, Max, QuerySet
from django.http import HttpRequest

from apps.job.models import Job

logger = logging.getLogger(__name__)


class KanbanService:
    """Service class for Kanban business logic."""
    
    @staticmethod
    def get_jobs_by_status(status: str, search_terms: Optional[List[str]] = None, limit: int = 200) -> QuerySet[Job]:
        """
        Get jobs filtered by status and optional search terms.
        
        Args:
            status: Job status to filter by
            search_terms: List of search terms to filter jobs
            limit: Maximum number of jobs to return
            
        Returns:
            QuerySet of filtered jobs
        """
        jobs_query = Job.objects.filter(status=status)
        
        if search_terms:
            query = Q()
            for term in search_terms:
                term_query = (
                    Q(name__icontains=term)
                    | Q(description__icontains=term)
                    | Q(client__name__icontains=term)
                    | Q(contact_person__icontains=term)
                    | Q(created_by__username__icontains=term)
                )
                query &= term_query
            jobs_query = jobs_query.filter(query)

        jobs = jobs_query.order_by("priority", "-created_at")
        
        # Apply different limits based on status
        match status:
            case "archived":
                return jobs[:100]
            case _:
                return jobs[:limit]

    @staticmethod
    def get_all_active_jobs() -> QuerySet[Job]:
        """Get all active (non-archived) jobs."""
        return Job.objects.filter(~Q(status="archived")).order_by("status", "priority")

    @staticmethod
    def get_archived_jobs(limit: int = 50) -> QuerySet[Job]:
        """Get archived jobs with limit."""
        return Job.objects.filter(status="archived").order_by("-created_at")[:limit]

    @staticmethod
    def get_status_choices() -> Dict[str, Any]:
        """Get available status choices and tooltips."""
        status_choices = {
            key: label for key, label in Job.JOB_STATUS_CHOICES if key != "archived"
        }
        
        status_tooltips = {
            key: Job.STATUS_TOOLTIPS.get(key, "")
            for key in status_choices.keys()
            if key in Job.STATUS_TOOLTIPS
        }
        
        return {
            "statuses": status_choices,
            "tooltips": status_tooltips
        }

    @staticmethod
    def serialize_job_for_api(job: Job, request: HttpRequest) -> Dict[str, Any]:
        """
        Serialize a job object for API response.
        
        Args:
            job: Job instance to serialize
            request: HTTP request for building absolute URIs
            
        Returns:
            Dictionary representation of the job
        """
        return {
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
                    "icon": (
                        request.build_absolute_uri(staff.icon.url)
                        if staff.icon
                        else None
                    ),
                }
                for staff in job.people.all()
            ],
            "status": job.get_status_display(),
            "status_key": job.status,
            "paid": job.paid,
            "created_by_id": job.created_by.id if job.created_by else None,
            "created_at": job.created_at.strftime("%d/%m/%Y") if job.created_at else None,
            "priority": job.priority
        }

    @staticmethod
    def update_job_status(job_id: UUID, new_status: str) -> bool:
        """
        Update job status.
        
        Args:
            job_id: UUID of the job to update
            new_status: New status value
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            Job.DoesNotExist: If job not found
        """
        try:
            job = Job.objects.get(pk=job_id)
            job.status = new_status
            job.save(update_fields=["status"])
            return True
        except Job.DoesNotExist:
            logger.error(f"Job {job_id} not found for status update")
            raise

    @staticmethod
    def get_adjacent_priorities(before_id: Optional[str], after_id: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
        """
        Get priorities of adjacent jobs.
        
        Args:
            before_id: ID of job before the target position
            after_id: ID of job after the target position
            
        Returns:
            Tuple of (before_priority, after_priority)
            
        Raises:
            Job.DoesNotExist: If referenced job not found
        """
        before_prio = None
        after_prio = None

        if before_id:
            before_prio = Job.objects.get(pk=before_id).priority
        if after_id:
            after_prio = Job.objects.get(pk=after_id).priority

        return before_prio, after_prio

    @staticmethod
    def rebalance_column(status: str) -> None:
        """
        Rebalance priorities in a status column.
        
        Args:
            status: Status column to rebalance
        """
        increment = Job.PRIORITY_INCREMENT
        jobs = list(Job.objects.filter(status=status).order_by("priority"))

        with transaction.atomic():
            for index, job in enumerate(jobs, start=1):
                job.priority = index * increment
                job.save(update_fields=["priority"])

    @staticmethod
    def calculate_priority(before_prio: Optional[int], after_prio: Optional[int], status: str) -> int:
        """
        Calculate new priority for job positioning.
        
        Args:
            before_prio: Priority of job before target position
            after_prio: Priority of job after target position
            status: Status column for the job
            
        Returns:
            Calculated priority value
        """
        increment = Job.PRIORITY_INCREMENT

        match (before_prio, after_prio):
            case (None, None):
                # No adjacent jobs; place at end
                max_prio = (
                    Job.objects.filter(status=status).aggregate(Max("priority"))["priority__max"]
                    or 0
                )
                return max_prio + increment

            case (None, after) if after is not None:
                # Insert at top: place just above the 'after' job
                new_prio = after - increment
                if new_prio <= 0:
                    KanbanService.rebalance_column(status)
                    # Re-fetch after_prio after rebalance
                    after = Job.objects.get(priority=after, status=status).priority
                    return after - increment
                return new_prio

            case (before, None) if before is not None:
                # Insert at bottom: place just below the 'before' job
                return before + increment

            case (before, after) if before is not None and after is not None:
                # Internal insertion: try to take the average
                gap = after - before
                if gap > 1:
                    return (before + after) // 2
                # Gap too small → rebalance first, then recompute
                KanbanService.rebalance_column(status)
                before = Job.objects.get(priority=before, status=status).priority
                after = Job.objects.get(priority=after, status=status).priority
                return (before + after) // 2

            case _:
                # Fallback: push to end if anything unexpected happens
                max_prio = (
                    Job.objects.filter(status=status).aggregate(Max("priority"))["priority__max"]
                    or 0
                )
                return max_prio + increment

    @staticmethod
    def reorder_job(
        job_id: UUID, 
        before_id: Optional[str] = None, 
        after_id: Optional[str] = None, 
        new_status: Optional[str] = None
    ) -> bool:
        """
        Reorder a job within or between columns.
        
        Args:
            job_id: UUID of job to reorder
            before_id: ID of job before target position
            after_id: ID of job after target position
            new_status: New status if moving between columns
            
        Returns:
            True if successful
            
        Raises:
            Job.DoesNotExist: If job not found
        """
        try:
            job = Job.objects.get(pk=job_id)
        except Job.DoesNotExist:
            logger.error(f"Job {job_id} not found for reordering")
            raise

        try:
            before_prio, after_prio = KanbanService.get_adjacent_priorities(before_id, after_id)
        except Job.DoesNotExist:
            logger.error(f"Adjacent job not found for reordering job {job_id}")
            raise

        # Determine target status for priority calculation
        target_status = new_status if new_status else job.status
        
        # Calculate new priority
        new_priority = KanbanService.calculate_priority(before_prio, after_prio, target_status)
        job.priority = new_priority

        # Update status if needed
        old_status = job.status
        update_fields = ["priority"]
        
        if new_status and new_status != old_status:
            job.status = new_status
            update_fields.insert(0, "status")

        job.save(update_fields=update_fields)
        return True

    @staticmethod
    def perform_advanced_search(filters: Dict[str, Any]) -> QuerySet[Job]:
        """
        Perform advanced search with multiple filters.
        
        Args:
            filters: Dictionary of search filters
            
        Returns:
            QuerySet of filtered jobs
        """
        jobs_query = Job.objects.all()

        # Apply filters with early returns for invalid data
        if number := filters.get("job_number", "").strip():
            jobs_query = jobs_query.filter(job_number=number)

        if name := filters.get("name", "").strip():
            jobs_query = jobs_query.filter(name__icontains=name)

        if description := filters.get("description", "").strip():
            jobs_query = jobs_query.filter(description__icontains=description)

        if client_name := filters.get("client_name", "").strip():
            jobs_query = jobs_query.filter(client__name__icontains=client_name)

        if contact_person := filters.get("contact_person", "").strip():
            jobs_query = jobs_query.filter(contact_person__icontains=contact_person)

        if created_by := filters.get("created_by", "").strip():
            jobs_query = jobs_query.filter(events__staff=created_by)

        if created_after := filters.get("created_after", "").strip():
            jobs_query = jobs_query.filter(created_at__gte=created_after)

        if created_before := filters.get("created_before", "").strip():
            jobs_query = jobs_query.filter(created_at__lte=created_before)

        if statuses := filters.get("status", []):
            jobs_query = jobs_query.filter(status__in=statuses)

        # Handle paid filter with match-case
        paid_filter = filters.get("paid", "")
        match paid_filter:
            case "true":
                jobs_query = jobs_query.filter(paid=True)
            case "false":
                jobs_query = jobs_query.filter(paid=False)

        return jobs_query.order_by("-created_at")
