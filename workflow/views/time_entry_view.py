import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.serializers.json import DjangoJSONEncoder
from django.template.loader import render_to_string
from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView
from django.contrib import messages

from workflow.enums import RateType
from workflow.models import Job, JobPricing, Staff, TimeEntry
from workflow.forms import TimeEntryForm, PaidAbsenceForm
from workflow.serializers.time_entry_serializer import TimeEntryForTimeEntryViewSerializer as TimeEntrySerializer
from workflow.utils import extract_messages, get_jobs_data

logger = logging.getLogger(__name__)


class TimesheetEntryView(TemplateView):
    """
    View to manage and display timesheet entries for a specific staff member and date.

    Purpose:
    - Centralizes the logic for rendering the timesheet entry page.
    - Dynamically loads staff, jobs, and timesheet data based on the provided date and staff ID.
    - Ensures access control and context consistency for the user interface.

    Key Features:
    - Excludes specific staff members (e.g., app/system users) from being displayed.
    - Prepares the context with data necessary for rendering the timesheet entry page.
    - Supports navigation between staff members for the same timesheet date.

    Attributes:
    - `template_name` (str): Path to the template used for rendering the view.
    - `EXCLUDED_STAFF_IDS` (list): List of Django staff IDs to be excluded from timesheet views.

    Usage:
    - Accessed via a URL pattern that includes the date and staff ID as parameters.
    - Provides the back-end logic for the `time_entries/timesheet_entry.html` template.
    """

    template_name = "time_entries/timesheet_entry.html"

    # Excluding app users ID's to avoid them being loaded in timesheet views because they do not have entries (Valerie and Corrin included as they are not supposed to enter hours)
    EXCLUDED_STAFF_IDS = [
        "a9bd99fa-c9fb-43e3-8b25-578c35b56fa6",
        "b50dd08a-58ce-4a6c-b41e-c3b71ed1d402",
        "d335acd4-800e-517a-8ff4-ba7aada58d14",
        "e61e2723-26e1-5d5a-bd42-bbd318ddef81",
    ]

    def get(self, request, date, staff_id, *args, **kwargs):
        """
        Handles GET requests to display the timesheet entry page for a given staff member and date.

        Purpose:
        - Retrieves and validates the date and staff member based on URL parameters.
        - Fetches timesheet entries, open jobs, and navigation details for the UI.
        - Ensures the context contains all data needed to render the page.

        Workflow:
        1. Validates the `date` parameter to ensure it is in the correct format (YYYY-MM-DD).
        2. Checks if the `staff_id` is excluded. If so, denies access.
        3. Retrieves the staff member and raises a 404 error if not found.
        4. Queries:
            - Timesheet entries for the specified date and staff member.
            - Open jobs for potential assignment.
        5. Prepares navigation details for moving between staff members.
        6. Constructs the context for rendering the page.

        Parameters:
        - `request`: The HTTP GET request.
        - `date` (str): The target date for the timesheet.
        - `staff_id` (UUID): The ID of the staff member.

        Returns:
        - Rendered HTML template with the context for the timesheet entry page.

        Error Handling:
        - Raises `ValueError` for invalid date formats.
        - Raises `PermissionError` if the staff member is excluded.
        - Raises `Http404` if the staff member is not found.

        Context:
        - Includes data for the staff member, timesheet entries, open jobs, and navigation links.

        Dependencies:
        - `Staff`, `TimeEntry`, and `Job` models for querying database records.
        - `json.dumps` for serializing data to JSON format.
        - `DjangoJSONEncoder` for handling complex data types.
        - Template: `time_entries/timesheet_entry.html`.

        Notes:
        - The `EXCLUDED_STAFF_IDS` attribute should be updated as needed
        to reflect changes in app/system users.
        """
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

        time_entries = TimeEntry.objects.filter(
            date=target_date, staff=staff_member
        ).select_related("job_pricing__latest_reality_for_job__client")

        scheduled_hours = float(staff_member.get_scheduled_hours(target_date))

        staff_data = {
            "id": staff_member.id,
            "name": staff_member.get_display_full_name(),
            "wage_rate": staff_member.wage_rate,
            "scheduled_hours": scheduled_hours,
        }

        timesheet_data = [
            {
                "id": str(entry.id),
                "job_pricing_id": entry.job_pricing_id,
                "job_number": entry.job_pricing.job.job_number,
                "job_name": entry.job_pricing.job.name,
                "client_name": (
                    entry.job_pricing.job.client.name
                    if entry.job_pricing.job.client
                    else "No client!?"
                ),
                "description": entry.description or "",
                "hours": float(
                    entry.hours
                ),  # Implicitly assumes one item, which is correct for reality
                "rate_multiplier": float(entry.wage_rate_multiplier),
                "is_billable": entry.is_billable,
                "notes": entry.note or "",
                "timesheet_date": target_date.strftime("%Y-%m-%d"),
                "staff_id": staff_member.id,
                "scheduled_hours": float(staff_member.get_scheduled_hours(target_date)),
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
                "estimated_hours": job.latest_estimate_pricing.total_hours,
                "hours_spent": job.latest_reality_pricing.total_hours,
                "client_name": job.client.name if job.client else "NO CLIENT!?",
                "charge_out_rate": float(job.charge_out_rate),
                "job_status": job.status,
            }
            for job in open_jobs
        ]

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"time_entries": timesheet_data, "jobs": jobs_data})

        next_staff = (
            Staff.objects.exclude(id__in=self.EXCLUDED_STAFF_IDS)
            .filter(id__gt=staff_member.id)
            .order_by("id")
            .first()
        )

        if not next_staff:
            next_staff = (
                Staff.objects.exclude(id__in=self.EXCLUDED_STAFF_IDS)
                .order_by("id")
                .first()
            )

        prev_staff = (
            Staff.objects.exclude(id__in=self.EXCLUDED_STAFF_IDS)
            .filter(id__lt=staff_member.id)
            .order_by("-id")
            .first()
        )

        if not prev_staff:
            prev_staff = (
                Staff.objects.exclude(id__in=self.EXCLUDED_STAFF_IDS)
                .order_by("-id")
                .first()
            )

        context = {
            "staff_member": staff_member,
            "staff_member_json": json.dumps(staff_data, cls=DjangoJSONEncoder),
            "timesheet_date": target_date.strftime("%Y-%m-%d"),
            "scheduled_hours": scheduled_hours,
            "timesheet_entries_json": json.dumps(timesheet_data, cls=DjangoJSONEncoder),
            "jobs_json": json.dumps(jobs_data, cls=DjangoJSONEncoder),
            "next_staff": next_staff,
            "prev_staff": prev_staff,
        }

        return render(request, self.template_name, context)

    def post(self, request, date, staff_id, *args, **kwargs):
        """
        Handles POST requests to manage timesheet entries and related actions.

        Purpose:
        - Provides centralized logic for managing timesheet-related AJAX operations.
        - Supports dynamic form loading and submission for timesheet entries.
        - Enables actions for managing paid absences.

        Workflow:
        1. Validates and parses the date from the URL.
        2. Ensures the staff member is authorized and exists in the database.
        3. Determines the requested action (`action` parameter) and processes it:
        - `load_paid_absence`: Renders the form for managing paid absences.
        - `add_paid_absence`: Adds paid absence entries to the timesheet.
        - `load_form`: Loads the timesheet entry form dynamically via AJAX.
        - `submit_form`: Validates and saves the timesheet entry data.
        4. Handles both success and failure responses with appropriate messages.

        Parameters:
        - `request`: The HTTP POST request containing action details and data.
        - `date` (str): The target date for the timesheet, extracted from the URL.
        - `staff_id` (UUID): The ID of the staff member, extracted from the URL.

        Responses:
        - Returns JSON responses for all actions:
        - Success: Includes relevant data for UI updates (e.g., form HTML, entry/job data).
        - Failure: Includes error messages to guide the user.

        Error Handling:
        - Raises `ValueError` for invalid date formats.
        - Returns 403 if the staff member is excluded.
        - Returns 404 if the staff member is not found.
        - Handles form validation errors gracefully, returning detailed messages.
        - Handles non-AJAX requests with a general "Invalid request" error.

        Dependencies:
        - Django utilities for JSON and template rendering (`JsonResponse`, `render_to_string`).
        - Custom utilities for extracting messages and formatting rate labels.
        - `TimeEntryForm` and `PaidAbsenceForm` for handling specific actions.

        Usage:
        - Integrated with the timesheet UI to dynamically load forms and process user inputs.
        - Handles backend logic for managing timesheet entries and paid absences.
        """
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid date format. Expected YYYY-MM-DD.")

        if staff_id in self.EXCLUDED_STAFF_IDS:
            messages.error(request, "Access denied for this staff member.")
            return JsonResponse(
                {
                    "error": "Access denied for this staff member",
                    "messages": extract_messages(request),
                },
                status=403,
            )

        try:
            staff_member = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            messages.error(request, "Staff member not found.")
            return JsonResponse(
                {
                    "error": "Staff member not found",
                    "messages": extract_messages(request),
                },
                status=404,
            )

        action = request.POST.get("action")
        if action == "load_paid_absence":
            return self.load_paid_absence(request)

        if action == "add_paid_absence":
            return self.add_paid_absence(request, staff_member)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            if request.POST.get("action") == "load_form":
                form = TimeEntryForm(
                    staff_member=staff_member, timesheet_date=target_date
                )
                form_html = render_to_string(
                    "time_entries/timesheet_form.html",
                    {
                        "form": form,
                        "staff_member": staff_member,
                        "target_date": target_date,
                    },
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
                        "entry": TimeEntrySerializer(time_entry).data,
                        "job": job_data,
                        "action": "add",
                        "messages": extract_messages(request),
                    }, status=200)                    

                messages.error(
                    request,
                    "Please correct the following errors in your time entry submission: "
                    + ", ".join(
                        [f"{field}: {error[0]}" for field, error in form.errors.items()]
                    ),
                )

                return JsonResponse(
                    {
                        "success": False,
                        "errors": form.errors,
                        "messages": extract_messages(request),
                    },
                    status=400,
                )

        # Handle non-AJAX POST requests
        messages.error(request, "Invalid request.")
        return JsonResponse(
            {"error": "Invalid request", "messages": extract_messages(request)},
            status=400,
        )

    def add_paid_absence(self, request, staff_member):
        """
        Adds paid absence entries to the timesheet.

        Purpose:
        - Automates the creation of time entries for a specified date range, excluding weekends.
        - Associates entries with a predefined virtual job for paid absences.
        - Ensures consistency and validation for staff-related absences.

        Workflow:
        1. Validates and parses the start and end dates from the request.
        2. Excludes invalid ranges where the end date is earlier than the start date.
        3. Iterates through each day in the range, skipping Saturdays and Sundays.
        4. Retrieves the `JobPricing` for the virtual paid absence job.
        5. Creates a `TimeEntry` for each valid weekday, linking it to the staff member and job.
        6. Collects data for each entry to be returned to the front-end.
        7. Returns success or error messages based on the outcome of the operation.

        Parameters:
        - `request`: The HTTP POST request containing the date range and staff details.
        - `staff_member`: The `Staff` object representing the staff member for whom the entries are created.

        Responses:
        - Success: Returns a list of created entries, including their details for UI updates.
        - Error: Returns validation or processing errors (e.g., invalid date range, missing job pricing).

        Error Handling:
        - Validates the date range to ensure `end_date >= start_date`.
        - Skips weekends (Saturday and Sunday) during entry creation.
        - Handles cases where `JobPricing` for the paid absence job cannot be found.
        - Catches and reports errors during entry creation, ensuring partial failures don't halt the process entirely.

        Dependencies:
        - Django's models (`JobPricing`, `TimeEntry`) for database operations.
        - Utility functions (`extract_messages`) for consistent error and success messaging.

        Usage:
        - Triggered via the `post` method in `TimesheetEntryView` when the action is `add_paid_absence`.
        - Enables bulk creation of time entries for predefined absence scenarios, improving efficiency and consistency.

        Notes:
        - Weekends are automatically excluded to reflect typical work schedules.
        - The virtual paid absence job ID (`job_id`) is hardcoded to match the Paid Absence Job, but the form can be updated to manage dynamic special jobs for paid leaves/absences
        """
        leave_jobs = {
            "annual": "eecdc751-0207-4f00-a47a-ca025a7cf935",
            "sick": "4dd8ec04-35a0-4c99-915f-813b6b8a3584",
            "other": "cd2085c7-0793-403e-b78d-63b3c134e59d",
        }

        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        leave_type = request.POST.get("leave_type")

        job_id = leave_jobs.get(leave_type, leave_jobs["other"])
        if not job_id:
            messages.error(request, "Invalid leave type provided")
            return JsonResponse(
                {
                    "error": "Invalid leave type provided",
                    "messages": extract_messages(request),
                },
                status=400,
            )

        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        if end_date < start_date:
            error_msg = "End date must be greater than or equal to start date."
            messages.error(request, error_msg)
            return JsonResponse(
                {
                    "error": error_msg,
                    "messages": extract_messages(request),
                },
                status=400
            )

        days = (end_date - start_date).days + 1
        entries = []
        for i in range(days):
            entry_date = start_date + timedelta(days=i)

            # Skipping weekends
            if entry_date.weekday() in [5, 6]:
                continue

            try:
                # Fetching the JobPricing related to the Paid Absence Job
                job_pricing = JobPricing.objects.filter(
                    job_id=job_id
                ).first()  # Maybe there's a better way to do it without having to import another model, but it solves the problem
                if not job_pricing:
                    return JsonResponse(
                        {
                            "error": "Job pricing for paid absence not found.",
                            "messages": [
                                {
                                    "level": "error",
                                    "message": "Job pricing for paid absence not found.",
                                }
                            ],
                        },
                        status=400,
                    )

                entry = TimeEntry.objects.create(
                    job_pricing=job_pricing,
                    staff=staff_member,
                    date=entry_date,
                    hours=8,
                    description=f"{leave_type.capitalize()} Leave",
                    is_billable=False,
                    note="Automatically created leave entry",
                    wage_rate=staff_member.wage_rate,
                    charge_out_rate=job_pricing.job.charge_out_rate,
                    wage_rate_multiplier=1.0,
                )

                job = entry.job_pricing.job
                jobs_data = [{
                    "id": str(job.id),
                    "job_number": job.job_number, 
                    "name": job.name,
                    "job_display_name": str(job),
                    "estimated_hours": job.latest_estimate_pricing.total_hours,
                    "hours_spent": job.latest_reality_pricing.total_hours,
                    "client_name": job.client.name if job.client else "NO CLIENT!?",
                    "charge_out_rate": float(job.charge_out_rate),
                    "job_status": job.job_status
                }]

                entries.append(
                    {
                        "id": str(entry.id),
                        "job_pricing_id": str(entry.job_pricing_id),
                        "job_number": entry.job_pricing.job.job_number,
                        "job_name": entry.job_pricing.job.name,
                        "client": entry.job_pricing.job.client.name,
                        "description": entry.description or "",
                        "hours": float(entry.hours),
                        "rate_multiplier": float(entry.wage_rate_multiplier),
                        "is_billable": entry.is_billable,
                        "notes": entry.note or "",
                        "timesheet_date": entry_date.strftime("%Y-%m-%d"),
                        "staff_id": staff_member.id,
                    }
                )

            except Exception as e:
                messages.error(request, f"Error creating paid absence entry: {str(e)}")
                return JsonResponse(
                    {"error": str(e), "messages": extract_messages(request)}, status=400
                )

        messages.success(request, "Paid absence entries created successfully")
        return JsonResponse(
            {
                "success": True,
                "entries": entries,
                "jobs": jobs_data,
                "messages": extract_messages(request),
            },
            status=200,
        )

    def load_paid_absence(self, request):
        """
        Loads the paid absence form for rendering in the front-end.

        Purpose:
        - Dynamically generates the HTML for the paid absence form.
        - Provides a seamless user experience by enabling form rendering via AJAX.

        Workflow:
        1. Instantiates the `PaidAbsenceForm` with the data from the request.
        2. Renders the form into an HTML string using the `render_to_string` utility.
        3. Returns a JSON response containing:
        - The rendered form HTML.
        - Success status.
        - Any messages to be displayed to the user.

        Parameters:
        - `request`: The HTTP POST request containing the form data.

        Responses:
        - Success:
        - Includes the rendered HTML for the form (`form_html`).
        - Provides feedback messages to the user if necessary.
        - Error Handling: Assumes basic validation at the form level.

        Dependencies:
        - `PaidAbsenceForm`: The Django form used for capturing paid absence details.
        - `render_to_string`: Utility for converting a template and context into HTML.
        - `extract_messages`: Utility for extracting user feedback messages from the request.

        Usage:
        - Triggered via the `post` method in `TimesheetEntryView` when the action is `load_paid_absence`.
        - Enables dynamic loading of the paid absence form in a modal or similar UI component.

        Notes:
        - Optimized for AJAX-based workflows to improve responsiveness and user experience.
        - Any server-side validation should be handled when the form is submitted (at `add_paid_absence`), not at this stage.
        - Includes a dropdown for selecting the type of leave.
        """
        LEAVE_CHOICES = [
            ("annual", "Annual Leave"),
            ("sick", "Sick Leave"),
            ("other", "Other Leave"),
        ]

        form = PaidAbsenceForm(initial={"leave_type": "other"})
        form_html = render_to_string(
            "time_entries/paid_absence_form.html", {"form": form}, request=request
        )

        return JsonResponse(
            {
                "success": True,
                "form_html": form_html,
                "messages": extract_messages(request),
            },
            status=200,
        )


@require_http_methods(["POST"])
def autosave_timesheet_view(request):
    """
    Handles autosave requests for timesheet data.

    Purpose:
    - Automates the saving of timesheet changes, including updates, creations, and deletions.
    - Dynamically updates related jobs and entries in the front-end.
    - Ensures data consistency and prevents duplication during processing.

    Workflow:
    1. Parsing and Validation:
    - Parses the incoming request body as JSON.
    - Separates entries into `time_entries` (to save or update) and `deleted_entries` (to remove).

    2. Deletion Processing:
    - Deletes specified entries by ID if they exist.
    - Removes related jobs from the current job list.
    - Logs any missing entries without causing failures.

    3. Time Entry Processing:
    - Skips incomplete or invalid entries.
    - Updates existing entries or creates new ones while avoiding duplicates.
    - Adds or updates jobs related to new or updated entries.

    4. Response:
    - Returns success responses with related jobs, action type (`add` or `remove`), and feedback messages.
    - Sends error responses for invalid data or unexpected issues.

    Parameters:
    - `request` (HttpRequest): The HTTP POST request containing timesheet data in JSON format.

    Error Handling:
    - Validates JSON format and structure (`time_entries` and `deleted_entries`).
    - Catches invalid data or missing fields gracefully, skipping problematic entries.
    - Logs unexpected exceptions and provides feedback for debugging.

    Dependencies:
    - Django Models (`TimeEntry`, `Job`, `Staff`) for database operations.
    - Utility Functions:
    - `extract_messages`: Extracts feedback messages for the front-end.
    - `get_jobs_data`: Retrieves data for jobs related to the processed entries.
    - `RateType`: Manages wage rate multipliers for time entries.

    Usage:
    - Triggered via AJAX POST requests from the front-end grid.
    - Supports real-time autosaving and deletion of entries with minimal latency.

    Notes:
    - Designed for efficient bulk processing to reduce server load.
    - Ensures traceability with extensive logging.
    - Prevents duplicate entries by verifying existing records with matching attributes.
    """
    try:
        logger.debug("Timesheet autosave request received")
        data = json.loads(request.body)
        time_entries = data.get("time_entries", [])
        deleted_entries = data.get("deleted_entries", [])

        related_jobs = set()

        logger.debug(f"Number of time entries: {len(time_entries)}")
        logger.debug(f"Number of entries to delete: {len(deleted_entries)}")

        if deleted_entries:
            for entry_id in deleted_entries:
                logger.debug(f"Deleting entry with ID: {entry_id}")

                try:
                    entry = TimeEntry.objects.get(id=entry_id)
                    related_jobs.add(entry.job_pricing.job_id)
                    messages.success(request, "Timesheet deleted successfully")
                    entry.delete()
                    logger.debug(f"Entry with ID {entry_id} deleted successfully")

                except TimeEntry.DoesNotExist:
                    logger.error(f"TimeEntry with ID {entry_id} not found for deletion")
            return JsonResponse(
                {
                    "success": True,
                    "jobs": get_jobs_data(related_jobs),
                    "action": "remove",
                    "messages": extract_messages(request),
                },
                status=200,
            )

        if not time_entries and not deleted_entries:
            logger.error("No valid entries to process")
            messages.info(request, "No changes to save.")
            return JsonResponse(
                {
                    "error": "No time entries provided",
                    "messages": extract_messages(request),
                },
                status=400,
            )

        updated_entries = []
        for entry_data in time_entries:
            if not entry_data.get("job_number") or not entry_data.get("hours"):
                logger.debug("Skipping incomplete entry: ", entry_data)
                continue

            entry_id = entry_data.get("id")
            logger.debug(f"Entry: {json.dumps(entry_data, indent=2)}")
            job_data = entry_data.get("job_data") 
            logger.debug(f"Job data: {json.dumps(job_data, indent=2)}")
            job_id = job_data.get("id") if job_data else None
            logger.debug(f"Job ID: {job_id}")

            if not job_id:
                logger.error("Missing job ID in entry data")
                continue

            try:
                hours = Decimal(str(entry_data.get("hours", 0)))
            except (TypeError, ValueError) as e:
                messages.error(request, f"Invalid hours value: {str(e)}")
                return JsonResponse(
                    {
                        "error": f"Invalid hours value: {str(e)}",
                        "messages": extract_messages(request),
                    },
                    status=400,
                )

            try:
                timesheet_date = entry_data.get("timesheet_date", None)
                if not timesheet_date:
                    logger.error("Missing timesheet_date in entry data")
                    continue

                target_date = datetime.strptime(timesheet_date, "%Y-%m-%d").date()
            except (ValueError, TypeError) as e:
                logger.error(
                    f"Invalid timesheet_date format: {entry_data.get("timesheet_date")}"
                )
                continue

            description = entry_data.get("description", "").strip()

            if entry_id and entry_id != "tempId":
                try:
                    logger.debug(f"Processing entry with ID: {entry_id}")
                    entry = TimeEntry.objects.get(id=entry_id)

                    # Identify old job before changing
                    old_job_id = entry.job_pricing.job.id if entry.job_pricing.job else None
                    old_job = Job.objects.get(id=old_job_id) if old_job_id else None

                    if job_id != str(entry.job_pricing.job.id):
                        logger.info(f"Job for entry {entry_id} changed to {job_id}")
                        new_job = Job.objects.get(id=job_id)
                        entry.job_pricing = new_job.latest_reality_pricing

                    # Update existing entry
                    entry.description = description
                    entry.hours = hours
                    entry.is_billable = entry_data.get("is_billable", True)
                    entry.note = entry_data.get("notes", "")
                    entry.wage_rate_multiplier = RateType(entry_data.get("rate_type", "Ord")).multiplier                    
                    entry.charge_out_rate = Decimal(str(job_data.get("charge_out_rate", 0)))

                    related_jobs.add(job_id)
                    entry.save()
                    updated_entries.append(entry)
                    job = entry.job_pricing.job

                    scheduled_hours = entry.staff.get_scheduled_hours(target_date)
                    if scheduled_hours < hours:
                        messages.warning(
                            request,
                            f"Existing timesheet saved successfully, but hours exceed scheduled hours for {target_date}",
                        )
                    elif job.status in ["completed", "quoting"]:
                        messages.error(
                            request,
                            f"Existing timesheet saved successfully, but current job is {job.status}.",
                        )
                    else:
                        messages.success(
                            request, "Existing timesheet saved successfully."
                        )
                    logger.debug("Existing timesheet saved successfully")

                    return JsonResponse({
                        "success": True,
                        "entry": TimeEntrySerializer(entry).data,
                        "jobs": get_jobs_data(related_jobs),
                        "remove_jobs": [get_jobs_data([str(old_job.id)])] if old_job else [],
                        "action": "update",
                        "messages": extract_messages(request)
                    }, status=200)

                except TimeEntry.DoesNotExist:
                    logger.error(f"TimeEntry with ID {entry_id} not found")

            else:
                # Verify if there's already a registry with same data to avoid creating multiple entries
                job = Job.objects.get(id=job_id)
                job_pricing = job.latest_reality_pricing
                staff = Staff.objects.get(id=entry_data.get("staff_id"))

                existing_entry = TimeEntry.objects.filter(
                    job_pricing__job_id=job_id,
                    staff_id=entry_data.get("staff_id"),
                    date=target_date,
                    description=description,
                    hours=hours,
                ).first()

                if existing_entry:
                    logger.info(f"Found duplicated entry: {existing_entry.id}")
                    continue

                date_str = entry_data.get("timesheet_date")
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                entry = TimeEntry.objects.create(
                    job_pricing=job_pricing,
                    staff=staff,
                    date=target_date,
                    description=description,
                    hours=hours,
                    is_billable=entry_data.get("is_billable", True),
                    note=entry_data.get("notes", ""),
                    wage_rate_multiplier=RateType(entry_data["rate_type"]).multiplier,
                    wage_rate=staff.wage_rate,
                    charge_out_rate=Decimal(str(job_data.get("charge_out_rate", 0))),
                )

                updated_entries.append(entry)
                related_jobs.add(job_id)

                scheduled_hours = entry.staff.get_scheduled_hours(target_date)
                if scheduled_hours < hours:
                    messages.warning(
                        request,
                        f"Timesheet created successfully, but hours exceed scheduled hours for today ({target_date})",
                    )
                elif job.status in ["completed", "quoting"]:
                    messages.error(
                        request,
                        f"Timesheet created successfully, but current job is {job.status}.",
                    )
                else:
                    messages.success(request, "Timesheet created successfully.")
                logger.debug("Timesheet created successfully")

                return JsonResponse({
                    "success": True,
                    "messages": extract_messages(request),
                    "entry": TimeEntrySerializer(entry).data,
                    "jobs": get_jobs_data(related_jobs),
                    "action": "add"
                }, status=200)
            
        return JsonResponse({
            "success": True,
            "messages": extract_messages(request),
            "entries": TimeEntrySerializer(updated_entries, many=True).data,
            "jobs": get_jobs_data(related_jobs),
            "remove_jobs": [get_jobs_data([str(old_job.id)])] if old_job else [],
            "action": "update"
        })


    except json.JSONDecodeError:
        logger.error("Failed to parse JSON")
        messages.error(request, "Failed to parse JSON")
        return JsonResponse(
            {"error": "Invalid JSON", "messages": extract_messages(request)}, status=400
        )

    except Exception as e:
        messages.error(request, f"Unexpected error: {str(e)}")
        logger.exception("Unexpected error during timesheet autosave")
        return JsonResponse(
            {"error": str(e), "messages": extract_messages(request)}, status=500
        )
