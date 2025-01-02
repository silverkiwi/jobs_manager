import json
from datetime import datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.generic import TemplateView
from decimal import Decimal

from workflow.models import Job, Staff, TimeEntry

import logging

logger = logging.getLogger(__name__)


# Excluding app users ID's to avoid them being loaded in timesheet views because they do not have entries (Valerie and Corrin included as they are not supposed to enter hours)
EXCLUDED_STAFF_IDS = [
    "a9bd99fa-c9fb-43e3-8b25-578c35b56fa6",
    "b50dd08a-58ce-4a6c-b41e-c3b71ed1d402",
    "d335acd4-800e-517a-8ff4-ba7aada58d14",
    "e61e2723-26e1-5d5a-bd42-bbd318ddef81"
]

class TimesheetOverviewView(TemplateView):
    template_name = "time_entries/timesheet_overview.html"

    def get(self, request, start_date=None, *args, **kwargs):
        # Step 1: Determine the start date
        if start_date:
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
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

            if staff_member.is_staff is True or str(staff_member.id) in EXCLUDED_STAFF_IDS:
                continue
            
            staff_hours = []
            for day in last_seven_days:
                scheduled_hours = staff_member.get_scheduled_hours(
                    day
                )  # Hours they're rostered to work
                staff_hours.append(
                    {
                        "date": day.strftime("%Y-%m-%d"),
                        "scheduled_hours": scheduled_hours,
                    }
                )
            staff_data.append(
                {
                    "staff_id": staff_member.id,
                    "staff_name": staff_member.get_display_name(),
                    "hours_by_day": staff_hours,
                }
            )

        # Step 4: Get all open jobs and their hours
        job_data = []
        open_jobs = Job.objects.filter(
            status__in=["quoting", "approved", "in_progress", "special"]
        )

        for job in open_jobs:
            # Get estimated hours, quoted hours, and actual hours
            reality = job.latest_reality_pricing
            estimated_hours = job.latest_estimate_pricing.total_hours
            quoted_hours = job.latest_quote_pricing.total_hours
            actual_entries = job.latest_reality_pricing.time_entries.all()
            actual_total_hours = sum(entry.hours for entry in actual_entries)
            actual_billable_hours = sum(
                entry.hours for entry in actual_entries if entry.is_billable
            )
            job_data.append(
                {
                    "job_id": job.id,
                    "job_name": job.name,
                    "estimated_hours": estimated_hours,
                    "quoted_hours": quoted_hours,
                    "actual_hours_to_date": actual_total_hours,
                    "actual_billable_hours_to_date": actual_billable_hours,
                    "actual_time_revenue_to_date": reality.total_time_revenue,
                    "actual_time_cost_to_date": reality.total_time_cost,
                    "actual_total_revenue_to_date": reality.total_revenue,
                    "actual_total_cost_to_date": reality.total_cost,
                    "shop_job": job.shop_job,
                }
            )

        # Step 5: Get all timesheets in that week
        timesheet_entries = []
        time_entries = TimeEntry.objects.filter(
            date__in=last_seven_days
        ).select_related("staff", "job_pricing")
        for entry in time_entries:
            timesheet_entries.append(
                {
                    "date": entry.date.strftime("%Y-%m-%d"),
                    "staff_member": (
                        entry.staff.get_display_name() if entry.staff else "Unknown"
                    ),
                    "job_name": entry.job_pricing.job.name,
                    "hours_worked": entry.hours,
                    "is_billable": entry.is_billable,
                    "wage_rate": entry.wage_rate,
                    "charge_out_rate": entry.charge_out_rate,
                }
            )

        # Prepare context for rendering
        context = {
            "start_date": start_date,
            "staff_data": staff_data,
            "job_data": job_data,
            "timesheet_entries": timesheet_entries,
            "last_seven_days": last_seven_days,
            "context_json": json.dumps(
                {
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "staff_data": staff_data,
                    "job_data": job_data,
                    "timesheet_entries": timesheet_entries,
                    "last_seven_days": [
                        day.strftime("%Y-%m-%d") for day in last_seven_days
                    ],
                },
                indent=2,
                cls=DjangoJSONEncoder,
            ),  # Pretty-print for readability
        }

        return render(request, self.template_name, context)


class TimesheetDailyView(TemplateView):
    template_name = "time_entries/timesheet_daily_view.html"

    def get(self, request, date=None, *args, **kwargs):
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                target_date = timezone.now().date()
        else:
            target_date = timezone.now().date()

        leave_jobs = {
            "annual": "eecdc751-0207-4f00-a47a-ca025a7cf935", 
            "sick": "4dd8ec04-35a0-4c99-915f-813b6b8a3584", 
            "other": "cd2085c7-0793-403e-b78d-63b3c134e59d"
        }

        staff_data = []
        total_expected_hours = 0
        total_actual_hours = 0
        total_billable_hours = 0
        total_shop_hours = 0
        total_missing_hours = 0

        for staff_member in Staff.objects.all():

            if staff_member.is_staff is True or str(staff_member.id) in EXCLUDED_STAFF_IDS:
                continue
            
            scheduled_hours = staff_member.get_scheduled_hours(target_date)
            decimal_scheduled_hours = Decimal(scheduled_hours)
            
            time_entries = TimeEntry.objects.filter(
                date=target_date, staff=staff_member
            ).select_related("job_pricing")

            paid_leave_entries = time_entries.filter(
                job_pricing__job_id__in=leave_jobs.values()
            )

            has_paid_leave = paid_leave_entries.exists()

            actual_hours = sum(entry.hours for entry in time_entries)
            
            billable_hours = sum(
                entry.hours for entry in time_entries if entry.is_billable
            )
            
            shop_hours = sum(
                entry.hours
                for entry in time_entries
                if entry.job_pricing.job.shop_job
            )

            missing_hours = decimal_scheduled_hours - actual_hours if decimal_scheduled_hours > actual_hours else 0

            total_expected_hours += scheduled_hours
            total_actual_hours += actual_hours
            total_billable_hours += billable_hours
            total_shop_hours += shop_hours
            total_missing_hours += missing_hours
            
            if has_paid_leave:
                status = "Off Today"
                alert = "-"
            elif scheduled_hours == 0:
                status = "Off Today"
                alert = "-"
            elif actual_hours == 0:
                status = "⚠️ Missing"
                alert = f"{decimal_scheduled_hours}hrs needed"
            elif actual_hours < decimal_scheduled_hours and decimal_scheduled_hours > 0:
                status = "⚠️ Missing"
                alert = f"{decimal_scheduled_hours - actual_hours:.1f}hrs needed"
            elif actual_hours > decimal_scheduled_hours:
                status = "⚠️ Overtime"
                alert = f"{actual_hours - decimal_scheduled_hours:.1f}hrs extra"
            else:
                status = "Complete"
                alert = "-"

            staff_data.append(
                {
                    "staff_id": staff_member.id,
                    "name": staff_member.preferred_name if staff_member.preferred_name else staff_member.get_display_name(),
                    "last_name": staff_member.last_name,
                    "scheduled_hours": scheduled_hours,
                    "actual_hours": actual_hours,
                    "status": status,
                    "alert": alert,
                    "entries": [
                        {
                            "job_name": entry.job_pricing.job.name,
                            "hours": entry.hours,
                            "is_billable": entry.is_billable,
                        }
                        for entry in time_entries
                    ],
                }
            )

        total_hours = total_actual_hours or 1
        billable_percentage = (total_billable_hours / total_hours) * 100
        shop_percentage = (total_shop_hours / total_hours) * 100

        context = {
            "date": target_date.strftime("%Y-%m-%d"),
            "staff_data": staff_data,
            "daily_summary": {
                "total_expected_hours": total_expected_hours,
                "total_actual_hours": total_actual_hours,
                "total_missing_hours": total_missing_hours,
                "billable_percentage": round(billable_percentage, 1),
                "shop_percentage": round(shop_percentage, 1),
            },
            "context_json": json.dumps(
                {"date": target_date.strftime("%Y-%m-%d"), "staff_data": staff_data},
                cls=DjangoJSONEncoder,
            ),
        }

        return render(request, self.template_name, context)
