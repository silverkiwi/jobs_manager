from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from workflow.views import (
    edit_job_view_ajax,
    adjustment_entry_view,
    client_view,
    debug_view,
    invoice_view,
    job_pricing_view,
    job_view,
    kanban_view,
    material_entry_view,
    staff_view,
    time_entry_views,
    xero_view,
)

from workflow.views.report_view import (
    ReportCompanyProfitAndLoss,
    CompanyProfitAndLossView,
)

urlpatterns = [
    # Redirect to Kanban board
    path("", RedirectView.as_view(url="/kanban/"), name="home"),
    path(
        "api/autosave-job/",
        edit_job_view_ajax.autosave_job_view,
        name="autosave_job_api",
    ),
    path("api/client-search/", client_view.ClientSearch, name="client_search_api"),
    path("api/get-job/", edit_job_view_ajax.get_job_api, name="get_job_api"),
    path("api/create-job/", edit_job_view_ajax.create_job_api, name="create_job_api"),
    path(
        "api/fetch_job_pricing/",
        edit_job_view_ajax.fetch_job_pricing_api,
        name="fetch_job_pricing_api",
    ),
    # API URLs
    path(
        "api/report/company-profit-and-loss/",
        ReportCompanyProfitAndLoss.as_view(),
        name="report_company_profit_and_loss",
    ),
    path(
        "api/fetch_status_values/",
        job_view.api_fetch_status_values,
        name="fetch_status_values",
    ),
    path(
        "api/xero/authenticate/",
        xero_view.xero_authenticate,
        name="authenticate_xero",
    ),
    path(
        "api/xero/oauth/callback/",
        xero_view.xero_oauth_callback,
        name="oauth_callback_xero",
    ),
    path(
        "api/xero/success/",
        xero_view.success_xero_connection,
        name="success_xero_connection",
    ),
    path(
        "api/xero/refresh/",
        xero_view.refresh_xero_data,
        name="refresh_xero_data",
    ),
    path(
        "api/xero/contacts/",
        xero_view.get_xero_contacts,
        name="list_xero_contacts",
    ),
    path(
        "api/xero/refresh_token/",
        xero_view.refresh_xero_token,
        name="refresh_token_xero",
    ),
    # Other URL patterns
    path("clients/", client_view.ClientListView.as_view(), name="list_clients"),
    path(
        "client/<uuid:pk>/",
        client_view.ClientUpdateView.as_view(),
        name="update_client",
    ),
    path("client/add/", client_view.AddClient, name="add_client"),
    path(
        "debug/sync-invoice/",
        debug_view.debug_sync_invoice_form,
        name="debug_sync_invoice_form",
    ),  # Form for input
    path(
        "debug/sync-invoice/<str:invoice_number>/",
        debug_view.debug_sync_invoice_view,
        name="debug_sync_invoice_view",
    ),  # Process the sync
    path("invoices/", invoice_view.InvoiceListView.as_view(), name="list_invoices"),
    path(
        "invoices/<uuid:pk>",
        invoice_view.InvoiceUpdateView.as_view(),
        name="update_invoice",
    ),
    # Job URLs
    # path(
    #     "old_jobs/create/", job_view.CreateJobViewOriginal.as_view(), name="create_job"
    # ),
    # path("old_jobs/", job_view.ListJobView.as_view(), name="list_jobs"),
    # path("old_jobs/<uuid:pk>/", job_view.UpdateJobView.as_view(), name="update_job"),
    # path(
    #     "old_jobs/<uuid:pk>/update_status/",
    #     kanban_view.update_job_status,
    #     name="update_job_status",
    # ),
    # Job Pricing URLs
    # path(
    #     "old_jobs/<uuid:job_id>/create_pricing/<str:pricing_stage>/",
    #     job_pricing_view.CreateJobPricingView.as_view(),
    #     name="create_job_pricing",
    # ),
    # path(
    #     "old_job_pricing/<uuid:pk>/",
    #     job_pricing_view.UpdateJobPricingView.as_view(),
    #     name="update_job_pricing",
    # ),
    # Entry URLs
    # path(
    #     "old_job_pricing/<uuid:job_pricing_id>/time_entry/create/",
    #     time_entry_views.CreateTimeEntryView.as_view(),
    #     name="create_time_entry",
    # ),
    # path(
    #     "old_job_pricing/<uuid:job_pricing_id>/material_entry/create/",
    #     material_entry_view.CreateMaterialEntryView.as_view(),
    #     name="create_material_entry",
    # ),
    # path(
    #     "old_job_pricing/<uuid:job_pricing_id>/adjustment_entry/create/",
    #     adjustment_entry_view.CreateAdjustmentEntryView.as_view(),
    #     name="create_adjustment_entry",
    # ),
    path("job/", edit_job_view_ajax.create_job_view, name="create_job"),
    path("job/<uuid:job_id>/", edit_job_view_ajax.edit_job_view_ajax, name="edit_job"),
    path(
        "time_entries/<uuid:pk>/",
        time_entry_views.UpdateTimeEntryView.as_view(),
        name="update_time_entry",
    ),
    # Kanban views
    path("kanban/", kanban_view.kanban_view, name="view_kanban"),
    path(
        "kanban/fetch_jobs/<str:status>/",
        kanban_view.fetch_jobs,
        name="fetch_jobs",
    ),
    path(
        "reports/company-profit-and-loss/",
        CompanyProfitAndLossView.as_view(),
        name="company_profit_and_loss_view",
    ),
    # Login/Logout views
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "staff/<uuid:staff_id>/get_rates/",
        staff_view.get_staff_rates,
        name="get_staff_rates",
    ),
]
