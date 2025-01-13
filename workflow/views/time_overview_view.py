import json
from datetime import datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.contrib import messages
from django.views.generic import TemplateView
from decimal import Decimal

from workflow.models import JobPricing, Staff, TimeEntry
from workflow.forms import PaidAbsenceForm
from workflow.utils import extract_messages

import logging
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


# Excluding app users ID's to avoid them being loaded in timesheet views because they do not have entries (Valerie and Corrin included as they are not supposed to enter hours)
EXCLUDED_STAFF_IDS = [
    "a9bd99fa-c9fb-43e3-8b25-578c35b56fa6",
    "b50dd08a-58ce-4a6c-b41e-c3b71ed1d402",
    "d335acd4-800e-517a-8ff4-ba7aada58d14",
    "e61e2723-26e1-5d5a-bd42-bbd318ddef81",
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

        week_days = [
            start_date + timezone.timedelta(days=i)
            for i in range(-start_date.weekday(), 5 - start_date.weekday())
        ]

        staff_data = []
        total_hours = 0
        total_billable_hours = 0
        total_shop_hours = 0
        total_leave_hours = 0

        for staff_member in Staff.objects.all():
            if (
                staff_member.is_staff is True
                or str(staff_member.id) in EXCLUDED_STAFF_IDS
            ):
                continue

            weekly_hours = []
            total_staff_hours = 0
            billable_hours = 0

            for day in week_days:
                scheduled_hours = staff_member.get_scheduled_hours(day)
                time_entries = TimeEntry.objects.filter(
                    staff=staff_member, date=day
                ).select_related("job_pricing")

                daily_hours = sum(entry.hours for entry in time_entries)
                daily_billable_hours = sum(
                    entry.hours for entry in time_entries if entry.is_billable
                )
                has_paid_leave = time_entries.filter(
                    job_pricing__job__name__icontains="Leave"
                ).exists()

                weekly_hours.append(
                    {
                        "day": day,
                        "hours": daily_hours,
                        "status": (
                            "Leave"
                            if has_paid_leave
                            else ("✓" if daily_hours >= scheduled_hours else "⚠")
                        ),
                    }
                )

                total_staff_hours += daily_hours
                billable_hours += daily_billable_hours

            staff_data.append(
                {
                    "staff_id": staff_member.id,
                    "name": staff_member.get_display_name(),
                    "weekly_hours": weekly_hours,
                    "total_hours": total_staff_hours,
                    "billable_percentage": (
                        round((billable_hours / total_staff_hours) * 100, 1)
                        if total_staff_hours > 0
                        else 0
                    ),
                }
            )

            total_hours += total_staff_hours
            total_billable_hours += billable_hours

        billable_percentage = (
            (total_billable_hours / total_hours) * 100 if total_hours > 0 else 0
        )

        # Prepare context for rendering
        context = {
            "week_days": week_days,
            "staff_data": staff_data,
            "weekly_summary": {
                "total_hours": total_hours,
                "billable_percentage": round(billable_percentage, 1),
            },
        }

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        if action == "load_paid_absence_form":
            return self.load_paid_absence_form(request)
        if action == "submit_paid_absence":
            return self.submit_paid_absence(request)
        messages.error(request, "Invalid action.")
        return JsonResponse(
            {"error": "Invalid action.", "messages": extract_messages(request)},
            status=400,
        )

    def load_paid_absence_form(self, request):
        staff_members = Staff.objects.exclude(id__in=EXCLUDED_STAFF_IDS)
        form = PaidAbsenceForm()
        form_html = render_to_string(
            "time_entries/paid_absence_form.html",
            {"form": form, "staff_members": staff_members},
            request=request,
        )
        return JsonResponse(
            {
                "form_html": form_html,
                "success": True,
            }
        )

    def submit_paid_absence(self, request):
        form = PaidAbsenceForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Form validation failed.")
            return JsonResponse(
                {
                    "success": False,
                    "errors": form.errors,
                    "messages": extract_messages(request),
                },
                status=400,
            )

        staff_member = form.cleaned_data["staff"]
        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]
        leave_type = form.cleaned_data["leave_type"]

        if end_date < start_date:
            messages.error(request, "End date must be after start date.")
            return JsonResponse(
                {"success": False, "messages": extract_messages(request)}, status=400
            )

        leave_jobs = {
            "annual": "eecdc751-0207-4f00-a47a-ca025a7cf935",
            "sick": "4dd8ec04-35a0-4c99-915f-813b6b8a3584",
            "other": "cd2085c7-0793-403e-b78d-63b3c134e59d",
        }

        job_pricing = JobPricing.objects.filter(job_id=leave_jobs[leave_type]).first()
        if not job_pricing:
            messages.error(request, "Invalid leave type selected.")
            return JsonResponse(
                {"success": False, "messages": extract_messages(request)}, status=400
            )

        for day in range((end_date - start_date).days + 1):
            date = start_date + timezone.timedelta(days=day)
            if date.weekday() >= 5:  # Skip weekends
                continue

            TimeEntry.objects.create(
                job_pricing=job_pricing,
                staff=staff_member,
                date=date,
                hours=8,
                description=f"{leave_type.capitalize()} Leave",
                is_billable=False,
                note="Automatically created leave entry",
                wage_rate=staff_member.wage_rate,
                charge_out_rate=job_pricing.job.charge_out_rate,
                wage_rate_multiplier=1.0,
            )

        messages.success(request, "Paid absence entries created successfully.")
        return JsonResponse({"success": True, "messages": extract_messages(request)})


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
            "other": "cd2085c7-0793-403e-b78d-63b3c134e59d",
        }

        staff_data = []
        total_expected_hours = 0
        total_actual_hours = 0
        total_billable_hours = 0
        total_shop_hours = 0
        total_missing_hours = 0

        for staff_member in Staff.objects.all():

            if (
                staff_member.is_staff is True
                or str(staff_member.id) in EXCLUDED_STAFF_IDS
            ):
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
                entry.hours for entry in time_entries if entry.job_pricing.job.shop_job
            )

            missing_hours = (
                decimal_scheduled_hours - actual_hours
                if decimal_scheduled_hours > actual_hours
                else 0
            )

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
                    "name": (
                        staff_member.preferred_name
                        if staff_member.preferred_name
                        else staff_member.get_display_name()
                    ),
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
