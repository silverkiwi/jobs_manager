"""
URL Configuration for Workflow App

URL Structure Patterns:
----------------------

1. Resource-based URL paths:
   - Primary resources have their own root path: /{resource}/
   - Examples: /xero/, /clients/, /invoices/, /job/, /kanban/

2. API Endpoints:
   - All API endpoints are prefixed with /api/
   - Follow pattern: /api/{resource}/{action}/
   - Examples: /api/xero/authenticate/, /api/clients/all/

3. Resource Actions:
   - List view: /{resource}/
   - Detail view: /{resource}/{id}/
   - Create: /{resource}/add/ or /api/{resource}/create/
   - Update: /{resource}/{id}/update/
   - Delete: /api/{resource}/{id}/delete/

4. Nested Resources:
   - Follow pattern: /{parent-resource}/{id}/{child-resource}/
   - Example: /job/{id}/workshop-pdf/

5. URL Names:
   - Use resource_action format
   - Examples: client_detail, job_create, invoice_update

6. Ordering:
   - URLs MUST be kept in strict alphabetical order by path
   - Group URLs logically (api/, resource roots) but maintain alphabetical order within each group
   - Comments may be used to denote logical groupings but do not break alphabetical ordering

Follow these patterns when adding new URLs to maintain consistency.
"""

import debug_toolbar
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView

from workflow.api import server
from workflow.api.reports.pnl import CompanyProfitAndLossReport
from workflow.api.enums import get_enum_choices
from workflow.views import (
    client_view,
    submit_quote_view,
)
from workflow.views.kpi_view import KPICalendarViews
from workflow.views.xero import xero_view
from workflow.views.report_view import CompanyProfitAndLossView, ReportsIndexView
from workflow.views import password_views, stock_view, use_stock_view
from workflow.views.purchase_order_view import (
    PurchaseOrderEmailView,
    PurchaseOrderListView,
    PurchaseOrderCreateView,
    autosave_purchase_order_view,
    delete_purchase_order_view,
    extract_supplier_quote_data_view,
)
from workflow.views.delivery_receipt_view import (
    DeliveryReceiptListView,
    DeliveryReceiptCreateView,
)
from workflow.views.purchase_order_pdf_view import PurchaseOrderPDFView

urlpatterns = [
    # Redirect to Kanban board
    path("", RedirectView.as_view(url="/kanban/"), name="home"),
    
    # API Endpoints
    path(
        "api/autosave-purchase-order/",
        autosave_purchase_order_view,
        name="autosave_purchase_order_api",
    ),
    path(
        "api/client/<uuid:client_id>/contact-persons/",
        client_view.get_client_contact_persons,
        name="api_get_client_contact_persons",
    ),
    path(
        "api/client/<uuid:client_id>/phones/", 
        client_view.get_client_phones,
        name="api_get_client_phones",
    ),
    path("api/clients/all/", client_view.get_all_clients_api, name="api_clients_all"),
    path(
        "api/client-search/",
        client_view.ClientSearch,
        name="client_search_api",
    ),
    path("api/client-detail/", client_view.client_detail, name="client_detail"),
    path(
        "api/extract-supplier-quote/",
        extract_supplier_quote_data_view,
        name="extract_supplier_quote_data",
    ),
    path(
        "api/quote/<uuid:job_id>/pdf-preview/",
        submit_quote_view.generate_quote_pdf,
        name="generate_quote_pdf",
    ),
    path(
        "api/quote/<uuid:job_id>/send-email/",
        submit_quote_view.send_quote_email,
        name="send_quote_email",
    ),
    path("api/get-env-variable/", server.get_env_variable, name="get_env_variable"),
    path("api/enums/<str:enum_name>/", get_enum_choices, name="get_enum_choices"),
    path(
        "api/reports/company-profit-loss/",
        CompanyProfitAndLossReport.as_view(),
        name="api-company-profit-loss",
    ),
    path(
        "api/reports/calendar/",
        KPICalendarViews.KPICalendarAPIView.as_view(),
        name="api_kpi_calendar",
    ),    
    # Stock APIs
    path(
        "api/stock/consume/",
        stock_view.consume_stock_api_view,
        name="consume_stock_api",
    ),
    path(
        "api/stock/create/", stock_view.create_stock_api_view, name="create_stock_api"
    ),
    path(
        "api/stock/<uuid:stock_id>/deactivate/",
        stock_view.deactivate_stock_api_view,
        name="deactivate_stock_api",
    ),
    # Stock Search API (for autocomplete)
    path(
        "api/stock/search/",
        stock_view.search_available_stock_api,
        name="search_stock_api",
    ),
    path(
        "api/xero/authenticate/",
        xero_view.xero_authenticate,
        name="api_xero_authenticate",
    ),
    path(
        "api/xero/oauth/callback/",
        xero_view.xero_oauth_callback,
        name="xero_oauth_callback",
    ),
    path(
        "api/xero/disconnect/",
        xero_view.xero_disconnect,
        name="xero_disconnect",
    ),
    path(
        "api/xero/sync-stream/",
        xero_view.stream_xero_sync,
        name="stream_xero_sync",
    ),
    path(
        "api/xero/create_invoice/<uuid:job_id>",
        xero_view.create_xero_invoice,
        name="create_invoice",
    ),
    path(
        "api/xero/delete_invoice/<uuid:job_id>",
        xero_view.delete_xero_invoice,
        name="delete_invoice",
    ),
    path(
        "api/xero/create_quote/<uuid:job_id>",
        xero_view.create_xero_quote,
        name="create_quote",
    ),
    path(
        "api/xero/delete_quote/<uuid:job_id>",
        xero_view.delete_xero_quote,
        name="delete_quote",
    ),
    path(
        "api/xero/sync-info/",
        xero_view.get_xero_sync_info,
        name="xero_sync_info",
    ),
    path(
        "api/xero/delete_purchase_order/<uuid:purchase_order_id>",
        xero_view.delete_xero_purchase_order,
        name="delete_xero_purchase_order",
    ),
    path(
        "api/xero/sync/",
        xero_view.start_xero_sync,
        name="synchronise_xero_data",
    ),
    path(
        "api/purchase-orders/<uuid:purchase_order_id>/pdf/",
        PurchaseOrderPDFView.as_view(),
        name="purchase-order-pdf",
    ),
    path(
        "api/purchase-orders/<uuid:purchase_order_id>/email/",
        PurchaseOrderEmailView.as_view(),
        name="purchase-order-email",
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
        "clients/unused/",
        client_view.UnusedClientsView.as_view(),
        name="unused_clients",
    ),
    path("reports/", ReportsIndexView.as_view(), name="reports_index"),
    path(
        "reports/company-profit-loss/",
        CompanyProfitAndLossView.as_view(),
        name="company-profit-loss-report",
    ),
    path(
        "reports/calendar/",
        KPICalendarViews.KPICalendarTemplateView.as_view(),
        name="kpi_calendar",
    ),
    path("xero/", xero_view.XeroIndexView.as_view(), name="xero_index"),
    path(
        "xero/sync-progress/",
        xero_view.xero_sync_progress_page,
        name="xero_sync_progress",
    ),
    path(
        "xero/unused-clients/",
        client_view.UnusedClientsView.as_view(),
        name="xero_unused_clients",
    ),
    # Purchase Order URLs with purchases prefix
    path(
        "purchases/purchase-orders/",
        PurchaseOrderListView.as_view(),
        name="purchase_orders",
    ),
    path(
        "purchases/purchase-orders/new/",
        PurchaseOrderCreateView.as_view(),
        name="new_purchase_order",
    ),
    path(
        "purchases/purchase-orders/<uuid:pk>/",
        PurchaseOrderCreateView.as_view(),
        name="edit_purchase_order",
    ),
    path(
        "purchases/purchase-orders/delete/<uuid:pk>/",
        delete_purchase_order_view,
        name="delete_purchase_order",
    ),
    # Delivery Receipt URLs with purchases prefix
    path(
        "purchases/delivery-receipts/",
        DeliveryReceiptListView.as_view(),
        name="delivery_receipts",
    ),
    path(
        "purchases/delivery-receipts/<uuid:pk>/",
        DeliveryReceiptCreateView.as_view(),
        name="edit_delivery_receipt",
    ),
    # Stock Management URLs with purchases prefix
    path("purchases/use-stock/", use_stock_view.use_stock_view, name="use_stock"),
    path("__debug__/", include(debug_toolbar.urls)),
]
