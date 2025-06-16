from django.urls import path
from .views.time_entry_view import TimesheetEntryView, autosave_timesheet_view
from .views.time_overview_view import TimesheetOverviewView, TimesheetDailyView
from .api.daily_timesheet_views import daily_timesheet_summary, staff_daily_detail

app_name = "timesheet"

urlpatterns = [
    # API Endpoints for Vue.js frontend
    path("api/daily/", daily_timesheet_summary, name="api_daily_timesheet_summary"),
    path(
        "api/daily/<str:target_date>/",
        daily_timesheet_summary,
        name="api_daily_timesheet_summary_with_date",
    ),
    path(
        "api/staff/<str:staff_id>/daily/",
        staff_daily_detail,
        name="api_staff_daily_detail",
    ),
    path(
        "api/staff/<str:staff_id>/daily/<str:target_date>/",
        staff_daily_detail,
        name="api_staff_daily_detail_with_date",
    ),
    # Timesheet Overview (Weekly View)
    path("overview/", TimesheetOverviewView.as_view(), name="timesheet_overview"),
    path(
        "overview/<str:start_date>/",
        TimesheetOverviewView.as_view(),
        name="timesheet_overview_with_date",
    ),
    # Export to IMS
    path(
        "export_to_ims/",
        TimesheetOverviewView.as_view(),
        name="timesheet_export_to_ims",
    ),
    # Daily Overview
    path("day/<str:date>/", TimesheetDailyView.as_view(), name="timesheet_daily_view"),
    # Individual Timesheet Entry
    path(
        "day/<str:date>/<uuid:staff_id>/",
        TimesheetEntryView.as_view(),
        name="timesheet_entry",
    ),
    # Autosave endpoint
    path("autosave/", autosave_timesheet_view, name="autosave_timesheet"),
]
