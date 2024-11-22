import json
import logging
from decimal import Decimal

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView
from django.shortcuts import render
from datetime import datetime

from workflow.enums import RateType
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
                'job_number': entry.job_pricing.job.job_number,
                'job_name': entry.job_pricing.job.name,
                'client_name': entry.job_pricing.job.client.name,
                'description': entry.description or '',
                'hours': float(entry.hours),        # Implicitly assumes one item, which is correct for reality
                'rate_multiplier': float(entry.wage_rate_multiplier),
                'is_billable': entry.is_billable,
                'timesheet_date': target_date.strftime('%Y-%m-%d'),
                'staff_id': staff_member.id,

            }
            for entry in time_entries
        ]


        open_jobs = Job.objects.filter(
            status__in=['quoting', 'approved', 'in_progress','special']
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
        data = json.loads(request.body)
        logger.debug(f"Parsed data: {data}")

        time_entries = data.get("time_entries", [])
        if not time_entries:
            logger.error("No time entries found in request")
            return JsonResponse({"error": "No time entries provided"}, status=400)

        for entry_data in time_entries:
            entry_id = entry_data.get("id")
            hours = Decimal(str(entry_data['hours']))

            if entry_id:
                # Update existing entry
                entry = TimeEntry.objects.get(id=entry_id)
                entry.description = entry_data.get('description', '')
                entry.hours = hours
                entry.is_billable = entry_data.get('is_billable', True)
                entry.note = entry_data.get('notes', '')
                rate_type = entry_data.get('rate_type', RateType.ORDINARY.value)
                entry.wage_rate_multiplier = RateType(rate_type).multiplier
                entry.save()
                logger.debug(f"Updated TimeEntry ID: {entry.id}")
            else:
                # Create new entry - need to get job_pricing
                job_id = entry_data.get('job_data', {}).get('id')
                job = Job.objects.get(id=job_id)
                job_pricing = job.latest_reality_pricing
                staff = Staff.objects.get(id=entry_data.get('staff_id'))

                wage_rate_multiplier = RateType(entry_data['rate_type']).multiplier
                wage_rate = staff.wage_rate  # From the staff member
                charge_out_rate = entry_data['job_data']['charge_out_rate']

                entry = TimeEntry.objects.create(
                    job_pricing=job_pricing,
                    staff_id=entry_data.get('staff_id'),
                    date=entry_data.get('timesheet_date'),
                    description=entry_data.get('description', ''),
                    hours = hours,
                    is_billable=entry_data.get('is_billable', True),
                    note=entry_data.get('notes', ''),
                    wage_rate_multiplier=wage_rate_multiplier,
                    wage_rate=wage_rate,
                    charge_out_rate=charge_out_rate
                )
                logger.debug(f"Created new TimeEntry ID: {entry.id}")

        return JsonResponse({"success": True})

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON")
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.exception("Unexpected error during timesheet autosave")
        return JsonResponse({"error": str(e)}, status=500)