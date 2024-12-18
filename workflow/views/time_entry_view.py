import json
import logging
from datetime import datetime
from decimal import Decimal

from django.core.serializers.json import DjangoJSONEncoder
from django.template.loader import render_to_string
from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from workflow.enums import RateType
from workflow.models import Job, Staff, TimeEntry
from workflow.forms import TimeEntryForm

logger = logging.getLogger(__name__)


class TimesheetEntryView(TemplateView):
    template_name = "time_entries/timesheet_entry.html"  # We'll need to create this

    EXCLUDED_STAFF_IDS = [
        "a9bd99fa-c9fb-43e3-8b25-578c35b56fa6",
        "b50dd08a-58ce-4a6c-b41e-c3b71ed1d402"
    ]

    def get(self, request, date, staff_id, *args, **kwargs):
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid date format. Expected YYYY-MM-DD.")

        # Check if staff_id is in excluded list
        if staff_id in self.EXCLUDED_STAFF_IDS:
            raise PermissionError("Access denied for this staff member")

        try:
            staff_member = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            raise Http404("Staff member not found")

        staff_data = {
            "id": staff_member.id,
            "name": staff_member.get_display_full_name(),
            "wage_rate": staff_member.wage_rate,
        }

        timesheet_entries = TimeEntry.objects.filter(
            staff=staff_member,
            date=target_date
        )

        # Get existing time entries for this staff member on this date
        time_entries = TimeEntry.objects.filter(
            date=target_date, staff=staff_member
        ).select_related("job_pricing__latest_reality_for_job__client")

        timesheet_data = [
            {
                "id": str(entry.id),
                "job_pricing_id": entry.job_pricing_id,
                "job_number": entry.job_pricing.job.job_number,
                "job_name": entry.job_pricing.job.name,
                "client_name": entry.job_pricing.job.client.name if entry.job_pricing.job.client else "No client!?",
                "description": entry.description or "",
                "hours": float(
                    entry.hours
                ),  # Implicitly assumes one item, which is correct for reality
                "rate_multiplier": float(entry.wage_rate_multiplier),
                "is_billable": entry.is_billable,
                "timesheet_date": target_date.strftime("%Y-%m-%d"),
                "staff_id": staff_member.id,
            }
            for entry in time_entries
        ]

        open_jobs = Job.objects.filter(
            status__in=["quoting", "approved", "in_progress", "special"]
        ).select_related("client")

        jobs_data = [
            {
                "id": str(job.id),
                "job_number": job.job_number,
                "name": job.name,
                "job_display_name": str(job),
                "client_name": job.client.name if job.client else "NO CLIENT!?",
                "charge_out_rate": float(job.charge_out_rate),
            }
            for job in open_jobs
        ]

        next_staff = Staff.objects.exclude(
            id__in=self.EXCLUDED_STAFF_IDS
        ).filter(
            id__gt=staff_member.id
        ).order_by("id").first()

        if not next_staff:
            next_staff = Staff.objects.exclude(
                id__in=self.EXCLUDED_STAFF_IDS
            ).order_by("id").first()
        
        prev_staff = Staff.objects.exclude(
            id__in=self.EXCLUDED_STAFF_IDS
        ).filter(
            id__lt=staff_member.id
        ).order_by("-id").first()

        if not prev_staff:
            prev_staff = Staff.objects.exclude(
                id__in=self.EXCLUDED_STAFF_IDS
            ).order_by("-id").first()   

        context = {
            "staff_member": staff_member,
            "staff_member_json": json.dumps(staff_data, cls=DjangoJSONEncoder),
            "timesheet_date": target_date.strftime("%Y-%m-%d"),
            "scheduled_hours": float(staff_member.get_scheduled_hours(target_date)),
            "timesheet_entries_json": json.dumps(timesheet_data, cls=DjangoJSONEncoder),
            "jobs_json": json.dumps(jobs_data, cls=DjangoJSONEncoder),
            "next_staff": next_staff,
            "prev_staff": prev_staff,
        }

        return render(request, self.template_name, context)

    def post(self, request, date, staff_id, *args, **kwargs):
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()                                              # Convert string date to datetime object
        except ValueError:
            raise ValueError("Invalid date format. Expected YYYY-MM-DD.")                                         # Return error if date format is invalid

        try:
            staff_member = Staff.objects.get(id=staff_id)                                                         # Get staff member instance
        except Staff.DoesNotExist:
            return JsonResponse({"error": "Staff member not found"}, status=404)                                  # Return error if staff not found

        if staff_id in self.EXCLUDED_STAFF_IDS:                                                                   # Check if staff is in excluded list
            return JsonResponse({"error": "Access denied"}, status=403)

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':                                           # Handle AJAX requests for modal form
            if request.POST.get('action') == 'load_form':
                # Return the form HTML for the modal
                form = TimeEntryForm(staff_member=staff_member)                                                   # Create form instance with staff member
                form_html = render_to_string(
                    'time_entries/timesheet_form.html',                                                           # Template for the form
                    {'form': form, 'staff_member': staff_member, 'target_date': target_date},
                    request=request
                )
                return JsonResponse({'form_html': form_html})                                                     # Return form HTML for modal

            elif request.POST.get('action') == 'submit_form':
                # Handle form submission
                form = TimeEntryForm(request.POST, staff_member=staff_member)                                     # Create form with POST data
                if form.is_valid():
                    time_entry = form.save(commit=False)                                                          # Create but don't save the instance yet
                    time_entry.staff = staff_member                                                               # Set the staff member
                    time_entry.date = target_date                                                                 # Set the date
                    time_entry.save()                                                                             # Save the time entry

                    # Return the new entry data for AG Grid
                    entry_data = {
                        "id": str(time_entry.id),
                        "job_pricing_id": time_entry.job_pricing_id,
                        "description": time_entry.description or "",
                        "hours": float(time_entry.hours),
                        "rate_multiplier": float(time_entry.wage_rate_multiplier),
                        "is_billable": time_entry.is_billable,
                        "timesheet_date": target_date.strftime("%Y-%m-%d"),
                        "staff_id": staff_member.id,
                    }
                    return JsonResponse({"success": True, "entry": entry_data})                                   # Return success response with entry data
                else:
                    return JsonResponse({"success": False, "errors": form.errors}, status=400)                    # Return form errors if invalid

        # Handle non-AJAX POST requests
        return JsonResponse({"error": "Invalid request"}, status=400)        


@require_http_methods(["POST"])
def autosave_timesheet_view(request):
    try:
        logger.debug("Timesheet autosave request received")
        data = json.loads(request.body)
        time_entries = data.get("time_entries", [])

        if not time_entries:
            logger.error("No time entries found in request")
            return JsonResponse({"error": "No time entries provided"}, status=400)

        updated_entries = []
        for entry_data in time_entries:
            entry_id = entry_data.get("id")
            logger.debug(f"Processing entry with ID: {entry_id}")
            
            try:
                hours = Decimal(str(entry_data.get("hours", 0)))
            except (TypeError, ValueError) as e:
                return JsonResponse({"error": f"Invalid hours value: {str(e)}"}, status=400)

            if entry_id:
                try:
                    entry = TimeEntry.objects.get(id=entry_id)
                    
                    # Store old values for logging
                    old_hours = entry.hours

                    # Update existing entry
                    entry = TimeEntry.objects.get(id=entry_id)
                    entry.description = entry_data.get("description", "")
                    entry.hours = hours
                    entry.is_billable = entry_data.get("is_billable", True)
                    entry.note = entry_data.get("notes", "")
                    rate_type = entry_data.get("rate_type", RateType.ORDINARY.value)
                    entry.wage_rate_multiplier = RateType(rate_type).multiplier
                    entry.save()
                    
                except TimeEntry.DoesNotExist:
                    logger.error(f"TimeEntry with ID {entry_id} not found")
                    return JsonResponse({"error": f"TimeEntry with ID {entry_id} not found"}, status=404)
            else:
                # Create new entry - need to get job_pricing
                job_id = entry_data.get("job_data", {}).get("id")
                job = Job.objects.get(id=job_id)
                job_pricing = job.latest_reality_pricing
                staff = Staff.objects.get(id=entry_data.get("staff_id"))

                date_str = entry_data.get("timesheet_date")
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                wage_rate_multiplier = RateType(entry_data["rate_type"]).multiplier
                wage_rate = staff.wage_rate  # From the staff member
                charge_out_rate = entry_data["job_data"]["charge_out_rate"]

                entry = TimeEntry.objects.create(
                    job_pricing=job_pricing,
                    staff_id=entry_data.get("staff_id"),
                    date=target_date,
                    description=entry_data.get("description", ""),
                    hours=hours,
                    is_billable=entry_data.get("is_billable", True),
                    note=entry_data.get("notes", ""),
                    wage_rate_multiplier=wage_rate_multiplier,
                    wage_rate=wage_rate,
                    charge_out_rate=charge_out_rate,
                )
                
                entry.save()

        return JsonResponse({
            "success": True,
            "updated_entries": updated_entries
        })

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON")
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.exception("Unexpected error during timesheet autosave")
        return JsonResponse({"error": str(e)}, status=500)
