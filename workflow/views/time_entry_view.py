import json
import logging

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView
from django.shortcuts import render
from django.utils import timezone
from datetime import datetime

from workflow.models import TimeEntry, Staff, Job

logger = logging.getLogger(__name__)

class TimesheetEntryView(TemplateView):
    template_name = "time_entries/timesheet_entry.html"  # We'll need to create this

    def get(self, request, date, staff_id, *args, **kwargs):
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("Invalid date format. Expected YYYY-MM-DD.")

        # Get the staff member
        staff_member = Staff.objects.get(id=staff_id)
        staff_data = {
            'id': staff_member.id,
            'name': staff_member.get_display_full_name(),
            'wage_rate': staff_member.wage_rate
        }

        # Get existing time entries for this staff member on this date
        time_entries = TimeEntry.objects.filter(
            date=target_date,
            staff=staff_member
        ).select_related('job_pricing__latest_reality_for_job__client')


        timesheet_data = [
            {
                'id': str(entry.id),
                'job_pricing_id': entry.job_pricing_id,
                'job_number': entry.job_pricing.related_job.job_number,
                'job_name': entry.job_pricing.related_job.name,
                'client_name': entry.job_pricing.related_job.client.name,
                'description': entry.description or '',
                'hours': float(entry.hours),
                'rate_multiplier': float(entry.wage_rate_multiplier),
                'is_billable': entry.is_billable,
                'timesheet_date': target_date.strftime('%Y-%m-%d'),
                'staff_id': staff_member.id,

            }
            for entry in time_entries
        ]


        open_jobs = Job.objects.filter(
            status__in=['quoting', 'approved', 'in_progress']
        ).select_related('client')

        jobs_data = [{
            'id': str(job.id),
            'job_number': job.job_number,
            'name': job.name,
            'job_display_name': str(job),
            'client_name': job.client.name if job.client else 'NO CLIENT!?',
            'charge_out_rate': float(job.charge_out_rate)
        } for job in open_jobs]


        context = {
            "staff_member": staff_member,
            "staff_member_json": json.dumps(staff_data,cls=DjangoJSONEncoder),
            "timesheet_date": target_date.strftime('%Y-%m-%d'),
            "scheduled_hours": float(staff_member.get_scheduled_hours(target_date)),
            "timesheet_entries_json": json.dumps(timesheet_data, cls=DjangoJSONEncoder),
            "jobs_json": json.dumps(jobs_data, cls=DjangoJSONEncoder),
        }

        return render(request, self.template_name, context)

    def post(self, request, date, staff_id, *args, **kwargs):
        # Handle saving time entries
        # We'll implement this once we have the template/form structure defined
        pass


@require_http_methods(["POST"])
def autosave_timesheet_view(request):
    try:
        logger.debug("Timesheet autosave request received")

        # Parse incoming JSON data
        data = json.loads(request.body)
        logger.debug(f"Parsed data: {data}")

        # Validate the presence of time entries
        time_entries = data.get("time_entries", [])
        if not time_entries:
            logger.error("No time entries found in request")
            return JsonResponse({"error": "No time entries provided"}, status=400)

        for entry_data in time_entries:
            entry_id = entry_data.get("id")
            if entry_id:
                # Update existing entry
                try:
                    entry = TimeEntry.objects.get(id=entry_id)
                    for field, value in entry_data.items():
                        setattr(entry, field, value)
                    entry.save()
                    logger.debug(f"Updated TimeEntry ID: {entry.id}")
                except TimeEntry.DoesNotExist:
                    logger.warning(f"TimeEntry with ID {entry_id} not found; skipping.")
            else:
                # Create new entry
                entry = TimeEntry.objects.create(**entry_data)
                logger.debug(f"Created new TimeEntry ID: {entry.id}")

        return JsonResponse({"success": True})

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON")
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    except Exception as e:
        logger.exception("Unexpected error during timesheet autosave")
        return JsonResponse({"error": "Unexpected error occurred"}, status=500)
