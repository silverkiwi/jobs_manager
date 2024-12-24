import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.serializers.json import DjangoJSONEncoder
from django.template.loader import render_to_string
from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.contrib import messages

from workflow.enums import RateType
from workflow.models import Job, JobPricing, Staff, TimeEntry
from workflow.forms import TimeEntryForm, PaidAbsenceForm
from workflow.utils import extract_messages, get_rate_type_label

logger = logging.getLogger(__name__)


class TimesheetEntryView(TemplateView):
    template_name = "time_entries/timesheet_entry.html" 

    # Excluding app users ID's to avoid them being loaded in timesheet views because they do not have entries 
    EXCLUDED_STAFF_IDS = [
        "a9bd99fa-c9fb-43e3-8b25-578c35b56fa6",
        "b50dd08a-58ce-4a6c-b41e-c3b71ed1d402"
    ]

    def get(self, request, date, staff_id, *args, **kwargs):
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid date format. Expected YYYY-MM-DD.")

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
                "notes": entry.note or "",
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
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid date format. Expected YYYY-MM-DD.")

        if staff_id in self.EXCLUDED_STAFF_IDS:
            messages.error(request, "Access denied for this staff member.")
            return JsonResponse({
                "error": "Access denied for this staff member",
                "messages": extract_messages(request)
                }, status=403)
        
        try:
            staff_member = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            messages.error(request, "Staff member not found.")
            return JsonResponse({
                "error": "Staff member not found",
                "messages": extract_messages(request)
                }, status=404)
        
        action = request.POST.get("action")
        if action == "load_paid_absence":
            return self.load_paid_absence(request)

        if action == "add_paid_absence":
            return self.add_paid_absence(request, staff_member)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            if request.POST.get("action") == "load_form":
                form = TimeEntryForm(
                    staff_member=staff_member, 
                    timesheet_date=target_date
                )
                form_html = render_to_string(
                    "time_entries/timesheet_form.html",
                    {"form": form, "staff_member": staff_member, "target_date": target_date},
                    request=request,
                )
                return JsonResponse({"form_html": form_html})

            elif request.POST.get("action") == "submit_form":
                form = TimeEntryForm(request.POST, staff_member=staff_member)
                if form.is_valid():
                    time_entry = form.save(commit=False)
                    time_entry.staff = staff_member
                    time_entry.date = target_date
                    time_entry.save()

                    messages.success(request, "Timesheet saved successfully")

                    
                   # Return the new entry data for AG Grid with job data so the entry will be fully loaded by the grid
                    entry_data = {
                        "id": str(time_entry.id),
                        "description": time_entry.description or "",
                        "hours": float(time_entry.hours),
                        "rate_multiplier": float(time_entry.wage_rate_multiplier),
                        "rate_type": get_rate_type_label(time_entry.wage_rate_multiplier),
                        "is_billable": time_entry.is_billable,
                        "notes": time_entry.note or "",
                        "timesheet_date": target_date.strftime("%Y-%m-%d"),
                        "staff_id": staff_member.id,
                    }
                    logger.debug("Rate multiplier: %s", entry_data["rate_type"])
                    
                    job = time_entry.job_pricing.job
                    job_data = {
                        "id": str(job.id),
                        "job_number": job.job_number, 
                        "name": job.name,
                        "job_display_name": str(job),
                        "client_name": job.client.name if job.client else "NO CLIENT!?",
                        "charge_out_rate": float(job.charge_out_rate),
                    }

                    return JsonResponse({    
                        "success": True, 
                        "entry": entry_data,
                        "job": job_data,
                        "messages": extract_messages(request),
                    }, status=200)                    

                messages.error(
                    request, 
                    "Please correct the following errors in your time entry submission: " + 
                    ", ".join([f"{field}: {error[0]}" for field, error in form.errors.items()])
                )

                return JsonResponse({
                    "success": False, 
                    "errors": form.errors, 
                    "messages": extract_messages(request)
                    }, status=400)                                          

        # Handle non-AJAX POST requests
        messages.error(request, "Invalid request.")
        return JsonResponse({
            "error": "Invalid request", 
            "messages": extract_messages(request)
            }, status=400)    

    def add_paid_absence(self, request, staff_member):
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        job_id = "ce8f9015-2a25-45fe-8441-1749989add05" # Virtual absence job id

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            if end_date < start_date:
                messages.error(request, "End date must be greater than or equal to start date.")
                raise ValueError("End date must be greater than or equal to start date.")
        except ValueError as e:
            return JsonResponse({
                "error": str(e),
                "messages": extract_messages(request)
                }, status=400)
        
        days = (end_date - start_date).days + 1
        entries = []
        for i in range(days):
            entry_date = start_date + timedelta(days=i)

            # Skipping weekends
            if entry_date.weekday() in [5, 6]: 
                continue

            try:
                # Fetching the JobPricing related to the Paid Absence Job
                job_pricing = JobPricing.objects.filter(job_id=job_id).first() # Maybe there's a better way to do it without having to import another model, but it solves the problem
                if not job_pricing:
                            return JsonResponse({
                                "error": "Job pricing for paid absence not found.",
                                "messages": [{"level": "error", "message": "Job pricing for paid absence not found."}]
                            }, status=400)
                
                entry = TimeEntry.objects.create(
                    job_pricing=job_pricing,
                    staff=staff_member,
                    date=entry_date,
                    hours=8,
                    description="Paid Absence",
                    is_billable=False,
                    note="Automatically created leave entry",
                    wage_rate=staff_member.wage_rate,
                    charge_out_rate=job_pricing.job.charge_out_rate,
                    wage_rate_multiplier=1.0
                )

                job = entry.job_pricing.job
                job_data = {
                    "id": str(job.id),
                    "job_number": job.job_number, 
                    "name": job.name,
                    "job_display_name": str(job),
                    "client_name": job.client.name if job.client else "NO CLIENT!?",
                    "charge_out_rate": float(job.charge_out_rate),
                }

                entries.append({
                    "id": str(entry.id),
                    "job_pricing_id": str(entry.job_pricing_id),
                    "job_number": entry.job_pricing.job.job_number,
                    "job_name": entry.job_pricing.job.name,
                    "job_data": job_data,
                    "client": entry.job_pricing.job.client.name if entry.job_pricing.job.client else "Paid Absence",
                    "description": entry.description or "",
                    "hours": float(entry.hours),
                    "rate_multiplier": float(entry.wage_rate_multiplier),
                    "is_billable": entry.is_billable,
                    "notes": entry.note or "",
                    "timesheet_date": entry_date.strftime("%Y-%m-%d"),
                    "staff_id": staff_member.id,
                })

            except Exception as e:
                messages.error(request, f"Error creating paid absence entry: {str(e)}")
                return JsonResponse({
                    "error": str(e),
                    "messages": extract_messages(request)
                    }, status=400)
        
        messages.success(request, "Paid absence entries created successfully")
        return JsonResponse({
            "success": True,
            "entries": entries,
            "messages": extract_messages(request)
            }, status=200)
    
    def load_paid_absence(self, request):
        form = PaidAbsenceForm(request.POST)
        form_html = render_to_string(
            "time_entries/paid_absence_form.html",
            {"form": form},
            request=request
        )

        return JsonResponse({
            "success": True,
            "form_html": form_html,
            "messages": extract_messages(request)
        }, status=200)


@require_http_methods(["POST"])
def autosave_timesheet_view(request):
    try:
        logger.debug("Timesheet autosave request received")
        data = json.loads(request.body)
        time_entries = data.get("time_entries", [])
        deleted_entries = data.get("deleted_entries", [])

        logger.debug(f"Number of time entries: {len(time_entries)}")
        logger.debug(f"Number of entries to delete: {len(deleted_entries)}")

        if deleted_entries:
            for entry_id in deleted_entries:
                logger.debug(f"Deleting entry with ID: {entry_id}")

                try:
                    entry = TimeEntry.objects.get(id=entry_id)
                    messages.success(request, f"Timesheet deleted successfully")
                    entry.delete()
                    logger.debug(f"Entry with ID {entry_id} deleted successfully")
                    return JsonResponse({
                        "success": True,
                        "messages": extract_messages(request)
                    }, status=200)

                except TimeEntry.DoesNotExist:
                    logger.error(f"TimeEntry with ID {entry_id} not found for deletion")

        if not time_entries and not deleted_entries:
            logger.error("No valid entries to process")
            messages.info(request, "No changes to save.")
            return JsonResponse({
                "error": "No time entries provided", 
                "messages": extract_messages(request)
                }, status=400)

        updated_entries = []
        for entry_data in time_entries:
            if not entry_data.get("job_number") or not entry_data.get("hours"):
                logger.debug("Skipping incomplete entry: ", entry_data)
                continue

            entry_id = entry_data.get("id")
            
            try:
                hours = Decimal(str(entry_data.get("hours", 0)))
            except (TypeError, ValueError) as e:
                messages.error(request, f"Invalid hours value: {str(e)}")
                return JsonResponse({
                    "error": f"Invalid hours value: {str(e)}", 
                    "messages": extract_messages(request)
                    }, status=400)

            try:
                timesheet_date = entry_data.get("timesheet_date", None)
                if not timesheet_date:
                    logger.error("Missing timesheet_date in entry data")
                    continue  

                target_date = datetime.strptime(timesheet_date, "%Y-%m-%d").date()
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid timesheet_date format: {entry_data.get("timesheet_date")}")
                continue  

            if entry_id and entry_id != 'tempId':
                try:
                    logger.debug(f"Processing entry with ID: {entry_id}")
                    entry = TimeEntry.objects.get(id=entry_id)

                    # Update existing entry
                    entry = TimeEntry.objects.get(id=entry_id)
                    entry.description = entry_data.get("description", "")
                    entry.hours = hours
                    entry.is_billable = entry_data.get("is_billable", True)
                    entry.note = entry_data.get("notes", "")
                    rate_type = entry_data.get("rate_type", RateType.ORDINARY.value)
                    entry.wage_rate_multiplier = RateType(rate_type).multiplier

                    entry.save()
                    messages.success(request, "Existing timesheet saved successfully.")
                    logger.debug("Existing timesheet saved successfully")

                except TimeEntry.DoesNotExist:
                    logger.error(f"TimeEntry with ID {entry_id} not found")

            else:
                # Verify if there's already a registry with same data to avoid creating multiple entries
                job_id = entry_data.get("job_data", {}).get("id")
                description = entry_data.get("description", "").strip()
                hours = Decimal(str(entry_data.get("hours", 0)))

                existing_entry = TimeEntry.objects.filter(
                    job_pricing__job_id=job_id,
                    staff_id=entry_data.get("staff_id"),
                    date=target_date,
                    description=description,
                    hours=hours
                ).first()

                if existing_entry:
                    logger.info(f"Found duplicated entry: {existing_entry.id}")
                    continue 

                # Create new entry - need to get job_pricing
                job = Job.objects.get(id=job_id)
                job_pricing = job.latest_reality_pricing
                staff = Staff.objects.get(id=entry_data.get("staff_id"))

                date_str = entry_data.get("timesheet_date")
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                wage_rate_multiplier = RateType(entry_data["rate_type"]).multiplier
                wage_rate = staff.wage_rate 
                charge_out_rate = entry_data["job_data"]["charge_out_rate"]

                entry = TimeEntry.objects.create(
                    job_pricing=job_pricing,
                    staff_id=entry_data.get("staff_id"),
                    date=target_date,
                    description=description,
                    hours=hours,
                    is_billable=entry_data.get("is_billable", True),
                    note=entry_data.get("notes", ""),
                    wage_rate_multiplier=wage_rate_multiplier,
                    wage_rate=wage_rate,
                    charge_out_rate=charge_out_rate,
                )
                
                updated_entries.append(entry.id)
                entry.save()

                messages.success(request, "Timesheet created successfully.")
                logger.debug("Timesheet created successfully")
                return JsonResponse({
                    "success": True,
                    "messages": extract_messages(request),
                    "entry_id": entry.id
                }, status=200)

        return JsonResponse({
            "success": True,
            "updated_entries": updated_entries,
            "messages": extract_messages(request)
        }, status=200)

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON")
        messages.error(request, "Failed to parse JSON")
        return JsonResponse({
            "error": "Invalid JSON",
            "messages": extract_messages(request)
            }, status=400)

    except Exception as e:
        messages.error(request, f"Unexpected error: {str(e)}")
        logger.exception("Unexpected error during timesheet autosave")
        return JsonResponse({
            "error": str(e),
            "messages": extract_messages(request)
            }, status=500)
