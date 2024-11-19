import json

from django.core.serializers.json import DjangoJSONEncoder
from django.views.generic import TemplateView
from django.shortcuts import render
from django.utils import timezone
from datetime import datetime

from workflow.models import TimeEntry, Staff, Job


class TimesheetEntryView(TemplateView):
    template_name = "time_entries/timesheet_entry.html"  # We'll need to create this

    def get(self, request, date, staff_id, *args, **kwargs):
        # Parse the date or default to today
        try:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            target_date = timezone.now().date()

        # Get the staff member
        staff_member = Staff.objects.get(id=staff_id)

        # Get existing time entries for this staff member on this date
        time_entries = TimeEntry.objects.filter(
            date=target_date,
            staff=staff_member
        ).select_related('job_pricing')

        open_jobs = Job.objects.filter(
            status__in=['quoting', 'approved', 'in_progress']
        ).select_related('client')

        jobs_data = [{
            'id': str(job.id),
            'job_number': job.job_number,
            'name': job.name,
            'client_name': job.client.name if job.client else 'Shop Job',
            'charge_out_rate': float(job.charge_out_rate)
        } for job in open_jobs]

        timesheet_data = {
            'staff_id': str(staff_id),
            'date': target_date.strftime('%Y-%m-%d'),
            'wage_rate': float(staff_member.wage_rate),
            'jobs': jobs_data,
            'time_entries': time_entries  # Let deserializer handle this
        }

        context = {
            "date": target_date.strftime('%Y-%m-%d'),
            "staff_member": staff_member,
            "staff_display_name": staff_member.get_display_name(),
            "timesheet_data_json": json.dumps(timesheet_data, cls=DjangoJSONEncoder)
        }

        context = {
            "date": target_date.strftime('%Y-%m-%d'),
            "staff_member": staff_member,
            "scheduled_hours": staff_member.get_scheduled_hours(target_date),
            "jobs_data": json.dumps(jobs_data, cls=DjangoJSONEncoder),  # Make sure this exists

            "time_entries": time_entries,
            "context_json": json.dumps({
                "date": target_date.strftime('%Y-%m-%d'),
                "staff_id": str(staff_id),
                "staff_name": staff_member.get_display_name(),
                "scheduled_hours": float(staff_member.get_scheduled_hours(target_date))
            }, cls=DjangoJSONEncoder)
        }

        return render(request, self.template_name, context)

    def post(self, request, date, staff_id, *args, **kwargs):
        # Handle saving time entries
        # We'll implement this once we have the template/form structure defined
        pass