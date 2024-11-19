import json

from django.views.generic import TemplateView
from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder

from django.shortcuts import render
from django.utils import timezone
from datetime import datetime

from workflow.models import TimeEntry, Job, Staff


class TimesheetOverviewView(TemplateView):
    template_name = "time_entries/timesheet_overview.html"

    def get(self, request, start_date=None, *args, **kwargs):
        # Step 1: Determine the start date
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                # If the date format is incorrect, default to today minus 7 days
                start_date = timezone.now().date() - timezone.timedelta(days=7)
        else:
            # Default to showing the last 7 days ending yesterday
            start_date = timezone.now().date() - timezone.timedelta(days=7)

        # Step 2: Calculate the last 7 days starting from the start date
        last_seven_days = [start_date - timezone.timedelta(days=i) for i in range(7)]

        # Step 3: Get all staff members and their hours by day
        staff_data = []
        all_staff = Staff.objects.all()
        for staff_member in all_staff:
            staff_hours = []
            for day in last_seven_days:
                scheduled_hours = staff_member.get_scheduled_hours(day) # Hours they're rostered to work
                staff_hours.append({
                    "date": day.strftime("%Y-%m-%d"),
                    "scheduled_hours": scheduled_hours
                })
            staff_data.append({
                "staff_id": staff_member.id,
                "staff_name": staff_member.get_display_name(),
                "hours_by_day": staff_hours
            })

        # Step 4: Get all open jobs and their hours
        job_data = []
        open_jobs = Job.objects.filter(status='open')
        for job in open_jobs:
            # Get estimated hours, quoted hours, and actual hours
            estimated_hours = job.estimate_pricing.get('hours', None)  # Assuming estimate_pricing contains hours estimate
            quoted_hours = job.quote_pricing.get('hours', None)  # Assuming quote_pricing contains quoted hours
            actual_entries = TimeEntry.objects.filter(job_pricing=job.jobpricing_set.first())
            actual_hours = [entry.hours() for entry in actual_entries]
            is_billable = any(entry.is_billable for entry in actual_entries)
            charge_out_rates = [entry.charge_out_rate for entry in actual_entries]
            wage_rates = [entry.wage_rate for entry in actual_entries]
            job_data.append({
                "job_id": job.id,
                "job_name": job.name,
                "estimated_hours": estimated_hours,
                "quoted_hours": quoted_hours,
                "actual_hours_to_date": actual_hours,  # Provide all hours without implying sequential order
                "is_billable": is_billable,
                "charge_out_rates": charge_out_rates,
                "wage_rates": wage_rates,
                "shop_job": job.shop_job  # Include flag to determine if this is a shop job
            })

        # Step 5: Get all timesheets in that week
        timesheet_entries = []
        time_entries = TimeEntry.objects.filter(date__in=last_seven_days).select_related('staff', 'job_pricing')
        for entry in time_entries:
            timesheet_entries.append({
                "date": entry.date.strftime("%Y-%m-%d"),
                "staff_member": entry.staff.get_display_name() if entry.staff else "Unknown",
                "job_name": entry.job_pricing.job.name,
                "hours_worked": entry.hours(),  # Use the decorator to get minutes and convert to hours
                "is_billable": entry.is_billable,
                "wage_rate": entry.wage_rate,
                "charge_out_rate": entry.charge_out_rate
            })

        # Prepare context for rendering
        context = {
            "start_date": start_date,
            "staff_data": staff_data,
            "job_data": job_data,
            "timesheet_entries": timesheet_entries,
            "last_seven_days": last_seven_days,
            "context_json": json.dumps({
                "start_date": start_date.strftime('%Y-%m-%d'),
                "staff_data": staff_data,
                "job_data": job_data,
                "timesheet_entries": timesheet_entries,
                "last_seven_days": [day.strftime('%Y-%m-%d') for day in last_seven_days]
            }, indent=2, cls=DjangoJSONEncoder)  # Pretty-print for readability

        }

        return render(request, self.template_name, context)


class TimesheetDailyView(TemplateView):
    template_name = "time_entries/timesheet_daily_view.html"

    def get_estimated_hours(self, job):
        # Sum the hours based on the job's estimate_pricing property
        if job.estimate_pricing:
            return sum([entry.hours for entry in job.estimate_pricing.time_entries.all()])
        return 0

    def get(self, request, date=None, *args, **kwargs):
        # Step 1: Determine the date
        if date:
            try:
                target_date = datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError:
                # If the date format is incorrect, default to today
                target_date = timezone.now().date()
        else:
            # Default to today
            target_date = timezone.now().date()


        # Step 2: Retrieve all time entries for the given date
        time_entries = TimeEntry.objects.filter(date=target_date).select_related('staff', 'job_pricing')
        data = []

        for entry in time_entries:
            # Use reality_pricing for actual work done during time entry
            reality_pricing = entry.job_pricing.reality_pricing

            data.append({
                "staff_member": entry.staff.get_display_name(),
                "date": entry.date.strftime("%Y-%m-%d"),
                "job_name": reality_pricing.job.name,
                "hours_worked": entry.hours_worked,
                "billable": entry.billable,
                "job_type": reality_pricing.job.type,
                "estimated_hours": self.get_estimated_hours(reality_pricing.job),
                "is_closed": reality_pricing.job.is_closed,
            })

            # Step 3: Check if it is an AJAX request
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax'):
            # Return the raw data as JSON
                return JsonResponse(data, safe=False)

        # Step 4: Normal request, render the HTML template
        context = {"date": target_date.strftime('%Y-%m-%d')}
        return render(request, self.template_name, context)
