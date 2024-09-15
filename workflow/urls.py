from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from workflow.views import (
    job_detail_view,
    job_views,
    kanban_view,
    time_entry_views,
    material_entry_view,
    adjustment_entry_view,
    xero_view,
)

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
        "api/xero/oauth/callback",
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
    ),
    path("api/xero/contacts/", xero_view.get_xero_contacts, name="xero_get_contacts"),
    path(
        "api/xero/refresh_token/",
        xero_view.refresh_xero_token,
        name="xero_refresh_token",
    ),
    path("jobs/create/", job_views.JobCreateView.as_view(), name="create_job"),
    path("jobs/", job_views.JobListView.as_view(), name="job_list"),
    path("jobs/<uuid:pk>/", job_view.JobView.as_view(), name="job"),
    path("jobs/<uuid:pk>/edit/", job_views.JobUpdateView.as_view(), name="edit_job"),
    path(
        "jobs/<uuid:pk>/update_status/",
        kanban_view.update_job_status,
        name="update_job_status",
    ),

    # Job Pricing Create
    path(
        "jobs/<uuid:job_id>/create_pricing/",
        job_pricing_view.JobPricingCreateView.as_view(),
        name="create_job_pricing"
    ),

    # Job Pricing Update
    path(
        "job_pricing/<uuid:pk>/edit/",
        job_pricing_view.JobPricingUpdateView.as_view(),
        name="edit_job_pricing"
    ),

    # Entry URLs
    path(
        "job_pricing/<uuid:job_pricing_id>/time_entry/create/",
        time_entry_views.CreateTimeEntryView.as_view(),
        name="create_time_entry"
    ),
    path(
        "job_pricing/<uuid:job_pricing_id>/material_entry/create/",
        material_entry_view.CreateMaterialEntryView.as_view(),
        name="create_material_entry"
    ),
    path(
        "job_pricing/<uuid:job_pricing_id>/adjustment_entry/create/",
        adjustment_entry_view.CreateAdjustmentEntryView.as_view(),
        name="create_adjustment_entry"
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

    # Kanban views
    path("kanban/", kanban_view.kanban_view, name="kanban"),
    path("kanban/fetch_jobs/<str:status>/", kanban_view.fetch_jobs, name="fetch_jobs"),

    # Login/Logout views
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
