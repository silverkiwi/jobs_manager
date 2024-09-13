from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from workflow.views import (
    job_detail_view,
    job_views,
    kanban_view,
    staff_views,
    time_entry_views,
    xero_view,
)

#    path('', views.DashboardView.as_view(), name='dashboard'),

urlpatterns = [
    path("", RedirectView.as_view(url="/kanban/"), name="dashboard"),
    path(
        "api/fetch_status_values/",
        job_views.fetch_job_status_values,
        name="fetch_status_values",
    ),
    path(
        "api/xero/authenticate/", xero_view.xero_authenticate, name="xero_authenticate"
    ),
    path(
        "api/xero/oauth/callback/",
        xero_view.xero_oauth_callback,
        name="xero_oauth_callback",
    ),
    path(
        "api/xero/success/",
        xero_view.xero_connection_success,
        name="xero_connection_success",
    ),
    path(
        "api/xero/error/", xero_view.xero_auth_error, name="xero_auth_error"
    ),  # Add this line
    path("api/xero/contacts/", xero_view.get_xero_contacts, name="xero_get_contacts"),
    path(
        "api/xero/refresh_token/",
        xero_view.refresh_xero_token,
        name="xero_refresh_token",
    ),
    path("jobs/create/", job_views.JobCreateView.as_view(), name="create_job"),
    path("jobs/", job_views.JobListView.as_view(), name="job_list"),
    path("jobs/<uuid:pk>/", job_detail_view.JobDetailView.as_view(), name="job_detail"),
    path("jobs/<uuid:pk>/edit/", job_views.JobUpdateView.as_view(), name="edit_job"),
    path(
        "jobs/<uuid:pk>/update_status/",
        kanban_view.update_job_status,
        name="update_job_status",
    ),
    path("kanban/", kanban_view.kanban_view, name="kanban"),
    path("kanban/fetch_jobs/<str:status>/", kanban_view.fetch_jobs, name="fetch_jobs"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("staff/", staff_views.StaffListView.as_view(), name="staff_list"),
    path("staff/register/", staff_views.RegisterStaffView.as_view(), name="register"),
    path(
        "staff/<uuid:pk>/", staff_views.StaffProfileView.as_view(), name="staff_profile"
    ),
    path(
        "staff/<uuid:pk>/edit/",
        staff_views.StaffUpdateView.as_view(),
        name="edit_staff",
    ),
    path(
        "time_entries/create/",
        time_entry_views.CreateTimeEntryView.as_view(),
        name="create_time_entry",
    ),
    path(
        "time_entries/<uuid:pk>/edit/",
        time_entry_views.TimeEntryUpdateView.as_view(),
        name="edit_time_entry",
    ),
    path(
        "time_entries/success/",
        time_entry_views.TimeEntrySuccessView.as_view(),
        name="time_entry_success",
    ),
]
