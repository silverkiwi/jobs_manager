"""
API URLs for timesheet endpoints.
Provides REST API routes for the Vue.js frontend.
"""
from django.urls import path
from .views.api import (
    StaffListAPIView,
    TimeEntriesAPIView,
    JobsAPIView,
    WeeklyOverviewAPIView,
    autosave_timesheet_api
)
from .views.ims_export_view import IMSExportView

app_name = "timesheet_api"

urlpatterns = [
    # Staff endpoints
    path("staff/", StaffListAPIView.as_view(), name="staff_list"),
    
    # Time entries endpoints
    path("entries/", TimeEntriesAPIView.as_view(), name="time_entries"),
    path("entries/<uuid:entry_id>/", TimeEntriesAPIView.as_view(), name="time_entry_detail"),
    
    # Jobs endpoints
    path("jobs/", JobsAPIView.as_view(), name="jobs_list"),
      # Weekly overview
    path("weekly-overview/", WeeklyOverviewAPIView.as_view(), name="weekly_overview"),
    
    # IMS Export
    path("ims-export/", IMSExportView.as_view(), name="ims_export"),
    
    # Autosave
    path("autosave/", autosave_timesheet_api, name="autosave"),
]
