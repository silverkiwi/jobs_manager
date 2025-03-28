import json
import logging
import re
import traceback
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import timedelta, timezone, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import TemplateView
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.db import transaction

from xero_python.accounting import AccountingApi
from xero_python.accounting.models import Contact
from xero_python.accounting.models import Invoice as XeroInvoice
from xero_python.accounting.models import LineItem
from xero_python.accounting.models import Quote as XeroQuote
from xero_python.accounting.models import PurchaseOrder as XeroPurchaseOrder
from xero_python.api_client import ApiClient
from xero_python.api_client.configuration import Configuration
from xero_python.api_client.oauth2 import OAuth2Token
from xero_python.exceptions import AccountingBadRequestException
from xero_python.identity import IdentityApi

from django.conf import settings
from workflow.templatetags.xero_tags import XERO_ENTITIES
from workflow.api.xero.sync import synchronise_xero_data, delete_clients_from_xero, get_last_modified_time
from workflow.api.xero.xero import (
    api_client,
    exchange_code_for_token,
    get_authentication_url,
    get_tenant_id,
    get_tenant_id_from_connections,
    get_token,
    get_valid_token,
    refresh_token,
)
from workflow.enums import InvoiceStatus, JobPricingType, QuoteStatus
from workflow.models import Invoice, Job, XeroToken, Client, Bill, CreditNote, XeroAccount, XeroJournal, CompanyDefaults
from workflow.models.xero_token import XeroToken
from workflow.models.quote import Quote
from workflow.models.purchase import PurchaseOrder
from workflow.utils import extract_messages

logger = logging.getLogger("xero")


# Xero Authentication (Step 1: Redirect user to Xero OAuth2 login)
def xero_authenticate(request: HttpRequest) -> HttpResponse:
    state = str(uuid.uuid4())
    request.session["oauth_state"] = state

    redirect_after_login = request.GET.get("next", "/")
    request.session["post_login_redirect"] = redirect_after_login

    authorization_url = get_authentication_url(state)
    return redirect(authorization_url)


# OAuth callback
def xero_oauth_callback(request: HttpRequest) -> HttpResponse:
    code = request.GET.get("code")
    state = request.GET.get("state")
    session_state = request.session.get("oauth_state")

    result = exchange_code_for_token(code, state, session_state)

    if "error" in result:
        return render(
            request, "xero/error_xero_auth.html", {"error_message": result["error"]}
        )

    redirect_url = request.session.pop("post_login_redirect", "/")
    return redirect(redirect_url)


# Refresh OAuth token and handle redirects
def refresh_xero_token(request: HttpRequest) -> HttpResponse:
    refreshed_token = refresh_token()

    if not refreshed_token:
        return redirect("api_xero_authenticate")

    return redirect("xero_get_contacts")


# Xero connection success view
def success_xero_connection(request: HttpRequest) -> HttpResponse:
    return render(request, "xero/success_xero_connection.html")


def refresh_xero_data(request):
    """Refresh Xero data, handling authentication properly."""
    try:
        token = get_valid_token()
        if not token:
            logger.info("No valid token found, redirecting to Xero authentication")
            return redirect("api_xero_authenticate")

        # If we have a valid token, proceed with syncing data
        return redirect("xero_sync_progress")

    except Exception as e:
        logger.error(f"Error while refreshing Xero data: {str(e)}")
        if "token" in str(e).lower():
            return redirect("api_xero_authenticate")
        return render(
            request, "general/generic_error.html", {"error_message": str(e)}
        )


def generate_xero_sync_events():
    """Generate SSE events for Xero sync progress."""
    try:
        # Verify we have a valid token before starting sync
        token = get_valid_token()
        if not token:
            yield f"data: {json.dumps({
                'datetime': timezone.now().isoformat(),
                'entity': 'sync',
                'severity': 'error',
                'message': 'No valid Xero token. Please authenticate.',
                'progress': None
            })}\n\n"
            return

        # Send a heartbeat every 15 seconds to keep the connection alive
        last_heartbeat = timezone.now()
        
        # Proceed with sync if we have a valid token
        messages = synchronise_xero_data()
        for message in messages:
            # Check if we need to send a heartbeat
            now = timezone.now()
            if (now - last_heartbeat).total_seconds() > 15:
                heartbeat = {
                    'datetime': now.isoformat(),
                    'entity': 'sync',
                    'severity': 'info',
                    'message': 'Heartbeat',
                    'progress': message.get('progress')
                }
                yield f"data: {json.dumps(heartbeat)}\n\n"
                last_heartbeat = now
                
            data = json.dumps(message)
            yield f"data: {data}\n\n"
    except Exception as e:
        error_message = {
            "datetime": timezone.now().isoformat(),
            "entity": "sync",
            "severity": "error",
            "message": str(e),
            "progress": None
        }
        yield f"data: {json.dumps(error_message)}\n\n"
    finally:
        final_message = {
            "datetime": timezone.now().isoformat(),
            "entity": "sync",
            "severity": "info",
            "message": "Sync stream ended",
            "progress": 1.0
        }
        yield f"data: {json.dumps(final_message)}\n\n"


def stream_xero_sync(request):
    """Stream Xero sync progress events."""
    try:
        response = StreamingHttpResponse(
            generate_xero_sync_events(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
    except Exception as e:
        logger.error(f"Error in stream_xero_sync: {str(e)}")
        raise


def clean_payload(payload):
    """Remove null fields from payload."""
    if isinstance(payload, dict):
        return {k: clean_payload(v) for k, v in payload.items() if v is not None}
    if isinstance(payload, list):
        return [clean_payload(v) for v in payload if v is not None]
    return payload


def format_date(dt):
    return dt.strftime("%Y-%m-%d")


def convert_to_pascal_case(obj):
    """
    Recursively converts dictionary keys from snake_case to PascalCase.
    """
    if isinstance(obj, dict):
        new_dict = {}
        for key, value in obj.items():
            pascal_key = re.sub(r"(?:^|_)(.)", lambda x: x.group(1).upper(), key)
            new_dict[pascal_key] = convert_to_pascal_case(value)
        return new_dict
    elif isinstance(obj, list):
        return [convert_to_pascal_case(item) for item in obj]
    else:
        return obj


class XeroDocumentCreator(ABC):
    """
    Base class for creating Xero Documents (Invoices, Quotes, Contacts).
    Implements common logic and provides abstract methods for customization.
    """

    job: Job
    client: Client
    xero_api: AccountingApi
    xero_tenant_id: str

    def __init__(self, job):
        self.job = job
        self.client = job.client
        self.xero_api = AccountingApi(api_client)
        self.xero_tenant_id = get_tenant_id()

    @abstractmethod
    def get_xero_id(self):
        """
        Returns the Xero ID for the document.
        """
        pass

    @abstractmethod
    def state_valid_for_xero(self):
        """
        Checks if the document is in a valid state to be sent to Xero.
        Returns True if valid, False otherwise.

        For example to invoice a job, it must not already be invoiced.
        To quote a job, it must not already be quoted.
        To create a purchase order, it must be in draft status.
        """
        pass

    @abstractmethod
    def get_line_items(self):
        """
        Returns a list of LineItem objects for the document
        """
        pass

    @abstractmethod
    def get_xero_document(self, type):
        """
        Returns a XeroDocument object for the document
        """
        pass

    @abstractmethod
    def get_local_model(self):
        """
        Returns the local model for the document
        """
        pass

    @abstractmethod
    def get_xero_update_method(self):
        """
        Returns the update method for the document
        """
        pass

    def validate_client(self):
        """
        Ensures the client exists and is synced with Xero
        """
        if not self.client:
            raise ValueError("Job does not have a client")
        if not self.client.validate_for_xero():
            raise ValueError("Client data is not valid for Xero")
        if not self.client.xero_contact_id:
            raise ValueError(
                f"Client {self.client.name} does not have a valid Xero contact ID. Sync the client with Xero first."
            )

    def get_xero_contact(self):
        """
        Returns a Xero Contact object for the client
        """
        return Contact(contact_id=self.client.xero_contact_id, name=self.client.name)

    def create_document(self):
        """
        Handles document creation and API communication with Xero.
        """
        self.validate_client()
        
        if not self.state_valid_for_xero():
            raise ValueError(f"Document is not in a valid state for Xero submission.")

        xero_document = self.get_xero_document(type="create")

        try:
            # Convert to PascalCase to match XeroAPI required format and clean payload
            payload = convert_to_pascal_case(clean_payload(xero_document.to_dict()))
            logger.debug(f"Serialized payload: {json.dumps(payload, indent=4)}")
        except Exception as e:
            logger.error(f"Error serializing XeroDocument: {str(e)}")
            raise

        try:
            if isinstance(self, XeroInvoiceCreator):
                response, http_status, http_headers = self.xero_api.create_invoices(
                    self.xero_tenant_id, invoices=payload, _return_http_data_only=False
                )
            elif isinstance(self, XeroQuoteCreator):
                response, http_status, http_headers = self.xero_api.create_quotes(
                    self.xero_tenant_id, quotes=payload, _return_http_data_only=False
                )
            else:
                raise ValueError("Unknown Xero document type.")

            logger.debug(f"Response Content: {response}")
            logger.debug(f"HTTP Status: {http_status}")
            # logger.debug(f"HTTP Headers: {http_headers}")
        except Exception as e:
            logger.error(f"Error sending document to Xero: {str(e)}")
            if hasattr(e, "body"):
                logger.error(f"Response body: {e.body}")
            raise

        return response
    
    def delete_document(self):
        """
        Handles document deletion and API communication with Xero.
        """
        self.validate_client()
        xero_document = self.get_xero_document(type="delete")

        try:
            payload = convert_to_pascal_case(clean_payload(xero_document.to_dict()))
            logger.debug(f"Serialized payload: {json.dumps(payload, indent=4)}")
        except Exception as e:
            logger.error(f"Error serializing XeroDocument: {str(e)}")
            raise

        try:
            response, http_status, http_headers = self.get_xero_update_method()(
                self.xero_tenant_id, payload, _return_http_data_only=False
            )

            logger.debug(f"Response Content: {response}")
            logger.debug(f"HTTP Status: {http_status}")
        except Exception as e:
            logger.error(f"Error sending document to Xero: {str(e)}")
            if hasattr(e, "body"):
                logger.error(f"Response body: {e.body}")
            raise

        return response


class XeroQuoteCreator(XeroDocumentCreator):
    """
    Handles Quote creation in Xero.
    """

    def get_xero_id(self):
        return str(self.job.quote.xero_id) if hasattr(self.job, "quote") else None

    def get_xero_update_method(self):
        return self.xero_api.update_or_create_quotes

    def get_local_model(self):
        return Quote

    def state_valid_for_xero(self):
        """
        Checks if the job is in a valid state to be quoted in Xero.
        Returns True if valid, False otherwise.
        """
        return not self.job.quoted


class XeroPurchaseOrderCreator(XeroDocumentCreator):
    """
    Handles Purchase Order creation in Xero.
    """
    
    purchase_order = None
    
    def __init__(self, purchase_order):
        self.purchase_order = purchase_order
        self.client = purchase_order.supplier
        self.xero_api = AccountingApi(api_client)
        self.xero_tenant_id = get_tenant_id()
    
    def get_xero_id(self):
        return str(self.purchase_order.xero_id) if self.purchase_order.xero_id else None
    
    def get_xero_update_method(self):
        return self.xero_api.update_or_create_purchase_orders
    
    def get_local_model(self):
        return PurchaseOrder
    
    def state_valid_for_xero(self):
        """
        Checks if the purchase order is in a valid state to be sent to Xero.
        Returns True if valid, False otherwise.
        """
        return self.purchase_order.status == 'draft'
    
    def get_line_items(self):
        """
        Generates purchase order-specific LineItems.
        """
        xero_line_items = []
        
        # Look up the Purchases account
        try:
            purchases_account = XeroAccount.objects.get(account_name__iexact="Purchases")
            account_code = purchases_account.account_code
        except XeroAccount.DoesNotExist:
            account_code = None
            logger.warning("Could not find 'Purchases' account in Xero accounts, omitting account code")
        except XeroAccount.MultipleObjectsReturned:
            # Log all matching accounts to help diagnose the issue
            accounts = XeroAccount.objects.filter(account_name__iexact="Purchases")
            logger.warning(f"Found multiple 'Purchases' accounts: {[(a.account_name, a.account_code, a.xero_id) for a in accounts]}")
            raise  # Re-raise the error after logging
        
        for line in self.purchase_order.lines.all():
            description = line.description
            if line.job:
                description = f"{line.job.job_number} - {description}"
            
            # Skip lines with TBC unit cost
            if line.unit_cost == 'TBC':
                continue
                
            # Create line item with account code only if we found it
            line_item_data = {
                "description": description,
                "quantity": float(line.quantity),
                "unit_amount": float(line.unit_cost)
            }
            
            if account_code:
                line_item_data["account_code"] = account_code
                
            xero_line_items.append(LineItem(**line_item_data))
        
        return xero_line_items
    
    def get_xero_document(self, type="create"):
        """
        Returns a Xero PurchaseOrder object.
        """
        if type == "create":
            # Only include delivery_date if it exists
            document_data = {
                "contact": self.get_xero_contact(),
                "date": format_date(self.purchase_order.order_date),
                "line_items": self.get_line_items(),
                "status": "SUBMITTED"
            }
            
            # Add delivery_date only if it exists
            if self.purchase_order.expected_delivery:
                document_data["delivery_date"] = format_date(self.purchase_order.expected_delivery)
            
            return XeroPurchaseOrder(**document_data)
        elif type == "delete":
            return XeroPurchaseOrder(
                purchase_order_id=self.get_xero_id(),
                status="DELETED"
            )
        else:
            raise ValueError(f"Unknown document type: {type}")
    
    def create_document(self):
        """
        Override to handle purchase order-specific creation.
        """
        self.validate_client()
        
        if not self.state_valid_for_xero():
            raise ValueError(f"Purchase order {self.purchase_order.id} is not in draft status.")
        
        xero_document = self.get_xero_document(type="create")
        
        try:
            # Convert to PascalCase to match XeroAPI required format and clean payload
            payload = convert_to_pascal_case(clean_payload(xero_document.to_dict()))
            logger.debug(f"Serialized payload: {json.dumps(payload, indent=4)}")
        except Exception as e:
            logger.error(f"Error serializing XeroDocument: {str(e)}")
            raise
        
        try:
            response, http_status, http_headers = self.xero_api.create_purchase_orders(
                self.xero_tenant_id, purchase_orders=payload, _return_http_data_only=False
            )
            
            logger.debug(f"Response Content: {response}")
            logger.debug(f"HTTP Status: {http_status}")
            
            # Update the purchase order status
            if response and response.purchase_orders:
                xero_po = response.purchase_orders[0]
                self.purchase_order.xero_id = xero_po.purchase_order_id
                self.purchase_order.status = 'submitted'
                self.purchase_order.save()
                
                return JsonResponse({
                    "success": True,
                    "xero_id": str(self.purchase_order.xero_id),
                    "status": self.purchase_order.status,
                    "messages": [],
                })
            else:
                return JsonResponse({
                    "success": False,
                    "error": "No purchase orders found in the response.",
                    "messages": [],
                }, status=400)
                
        except Exception as e:
            logger.error(f"Error sending document to Xero: {str(e)}")
            if hasattr(e, "body"):
                logger.error(f"Response body: {e.body}")
            
            return JsonResponse({
                "success": False,
                "error": str(e),
                "messages": [],
            }, status=500)

    def validate_job(self):
        """
        Ensures the job is valid for quote creation.
        """
        if self.job.quoted:
            raise ValueError(f"Job {self.job.id} is already quoted.")

    def get_line_items(self):
        """
        Generate quote-specific LineItems.
        """
        line_items = [
            LineItem(
                description=f"Quote for job: {self.job.job_number}{(" - " + self.job.description) if self.job.description else ''}",
                quantity=1,
                unit_amount=float(self.job.latest_quote_pricing.total_revenue)
                or 0.00,
                account_code=200,
            )
        ]

        return line_items

    def get_xero_document(self, type: str) -> XeroQuote:
        """
        Creates a quote object for Xero creation or deletion.
        """
        match (type):
            case "create":
                if self.job.order_number:
                    return XeroQuote(
                        contact=self.get_xero_contact(),
                        line_items=self.get_line_items(),
                        date=format_date(timezone.now()),
                        expiry_date=format_date(timezone.now() + timedelta(days=30)),
                        line_amount_types="Exclusive",
                        reference=self.job.order_number,
                        currency_code="NZD",
                        status="DRAFT",
                    )
                
                # If not order number, create quote without reference
                return XeroQuote(
                    contact=self.get_xero_contact(),
                    line_items=self.get_line_items(),
                    date=format_date(timezone.now()),
                    expiry_date=format_date(timezone.now() + timedelta(days=30)),
                    line_amount_types="Exclusive",
                    currency_code="NZD",
                    status="DRAFT",
                )
            case "delete":
                return XeroQuote(
                    quote_id=self.get_xero_id(),
                    contact=self.get_xero_contact(),
                    line_items=self.get_line_items(),
                    date=format_date(timezone.now()),
                    expiry_date=format_date(timezone.now() + timedelta(days=30)),
                    line_amount_types="Exclusive",
                    reference=f"Quote for job {self.job.job_number}",
                    currency_code="NZD",
                    status="DELETED",
                )

    def create_document(self):
        """Creates a quote and returns the quote URL."""
        response = super().create_document()

        if response and response.quotes:
            xero_quote_data = response.quotes[0]
            xero_quote_id = xero_quote_data.quote_id

            quote_url = f"https://go.xero.com/app/quotes/edit/{xero_quote_id}"

            quote = Quote.objects.create(
                xero_id=xero_quote_id,
                job=self.job,
                client=self.client,
                date=timezone.now().date(),
                status=QuoteStatus.DRAFT,
                total_excl_tax=Decimal(xero_quote_data.sub_total),
                total_incl_tax=Decimal(xero_quote_data.total),
                xero_last_modified=timezone.now(),
                xero_last_synced=timezone.now(),
                online_url=quote_url,
                raw_json=json.dumps(response.to_dict(), default=str),
            )

            logger.info(f"Quote {quote.id} created successfully for job {self.job.id}")

            return JsonResponse(
                {
                    "success": True,
                    "xero_id": xero_quote_id,
                    "client": self.client.name,
                    "quote_url": quote_url,
                }
            )
        else:
            logger.error("No quotes found in the response or failed to create quote.")
            return JsonResponse(
                {"success": False, "error": "No quotes found in the response."},
                status=400,
            )
        
    def delete_document(self):
        response = super().delete_document()
        if response and response.quotes:
            self.job.quote.delete()
            logger.info(f"Quote {self.job.quote.id} deleted successfully for job {self.job.id}")
            return JsonResponse({"success": True})
        else:
            logger.error("No quotes found in the response or failed to delete quote.")
            return JsonResponse({"success": False, "error": "No quotes found in the response."}, status=400)


class XeroInvoiceCreator(XeroDocumentCreator):
    """
    Handles invoice creation in Xero.
    """

    def get_xero_id(self):
        return str(self.job.invoice.xero_id) if hasattr(self.job, "invoice") else None

    def get_xero_update_method(self):
        return self.xero_api.update_or_create_invoices
    
    def get_local_model(self):
        return Invoice
    
    def state_valid_for_xero(self):
        """
        Checks if the job is in a valid state to be invoiced in Xero.
        Returns True if valid, False otherwise.
        """
        return not self.job.invoiced

    def get_line_items(self):
        """
        Generates invoice-specific LineItems.
        """
        pricing_type: JobPricingType = self.job.pricing_type

        match pricing_type:
            case JobPricingType.TIME_AND_MATERIALS:
                return self.get_time_and_materials_line_items()
            case JobPricingType.FIXED_PRICE:
                return self.get_fixed_price_line_items()
            case _:
                raise ValueError(f"Unknown pricing type: {pricing_type}")
    
    def get_time_and_materials_line_items(self):
        """
        Generates LineItems for time and materials pricing.
        """
        xero_line_items = []
        xero_line_items.append(
            LineItem(
                description=f"Invoice for job: {self.job.job_number}{(" - " + self.job.description) if self.job.description else ''}",
                quantity=1,
                unit_amount=float(self.job.latest_reality_pricing.total_revenue) or 0.00,
                account_code=200,
            ),
        )
        return xero_line_items
    
    def get_fixed_price_line_items(self):
        xero_line_items: list[LineItem] = []
        xero_line_items.extend([
            LineItem(
                description="Price as quoted"
            ),
            LineItem(
                description=f"Invoice for job: {self.job.job_number}{(" - " + self.job.description) if self.job.description else ''}",
                quantity=1,
                unit_amount=float(self.job.latest_quote_pricing.total_revenue)
                or 0.00,
                account_code=200,
            )
        ])

        return xero_line_items

    def get_xero_document(self, type):
        """
        Creates an invoice object for Xero.
        """
        match (type):
            case "create":
                if self.job.order_number:
                    return XeroInvoice(
                        type="ACCREC",
                        contact=self.get_xero_contact(),
                        line_items=self.get_line_items(),
                        date=format_date(timezone.now()),
                        due_date=format_date(timezone.now() + timedelta(days=30)),
                        line_amount_types="Exclusive",
                        reference=self.job.order_number,
                        currency_code="NZD",
                        status="DRAFT",
                    )
                
                # If not order number, create invoice without reference
                return XeroInvoice(
                        type="ACCREC",
                        contact=self.get_xero_contact(),
                        line_items=self.get_line_items(),
                        date=format_date(timezone.now()),
                        due_date=format_date(timezone.now() + timedelta(days=30)),
                        line_amount_types="Exclusive",
                        currency_code="NZD",
                        status="DRAFT",
                    )
            case "delete":
                return XeroInvoice(
                    invoice_id=self.get_xero_id(),
                    type="ACCREC",
                    contact=self.get_xero_contact(),
                    line_items=self.get_line_items(),
                    date=format_date(timezone.now()),
                    due_date=format_date(timezone.now() + timedelta(days=30)),
                    line_amount_types="Exclusive",
                    reference=f"Invoice for job {self.job.job_number}",
                    currency_code="NZD",
                    status="DELETED",
                )

    def create_document(self):
        """Creates an invoice, processes response, and stores it in the database."""
        response = super().create_document()

        if response and response.invoices:
            xero_invoice_data = response.invoices[0]
            xero_invoice_id = xero_invoice_data.invoice_id

            invoice_url = f"https://invoicing.xero.com/edit/{xero_invoice_id}"

            invoice_json = json.dumps(response.to_dict(), default=str)

            invoice = Invoice.objects.create(
                xero_id=xero_invoice_id,
                job=self.job,
                client=self.client,
                number=xero_invoice_data.invoice_number,
                date=timezone.now().date(),
                due_date=(timezone.now().date() + timedelta(days=30)),
                status=InvoiceStatus.SUBMITTED,
                total_excl_tax=Decimal(xero_invoice_data.total),
                tax=Decimal(xero_invoice_data.total_tax),
                total_incl_tax=Decimal(xero_invoice_data.total)
                + Decimal(xero_invoice_data.total_tax),
                amount_due=Decimal(xero_invoice_data.amount_due),
                xero_last_synced=timezone.now(),
                xero_last_modified=timezone.now(),
                online_url=invoice_url,
                raw_json=invoice_json,
            )

            logger.info(
                f"Invoice {invoice.id} created successfully for job {self.job.id}"
            )

            return JsonResponse(
                {
                    "success": True,
                    "invoice_id": invoice.id,
                    "xero_id": xero_invoice_id,
                    "client": invoice.client.name,
                    "total_excl_tax": str(invoice.total_excl_tax),
                    "total_incl_tax": str(invoice.total_incl_tax),
                    "invoice_url": invoice_url,
                }
            )
        else:
            logger.error(
                "No invoices found in the response or failed to update invoice."
            )
            return JsonResponse(
                {"success": False, "error": "No invoices found in the response."},
                status=400,
            )
        
    def delete_document(self):
        response = super().delete_document()

        if response and response.invoices:
            self.job.invoice.delete()
            logger.info(f"Invoice {self.job.invoice.id} deleted successfully for job {self.job.id}")
            return JsonResponse({"success": True})
        else:
            logger.error("No invoices found in the response or failed to delete invoice.")
            return JsonResponse({"success": False, "error": "No invoices found in the response."}, status=400)


def ensure_xero_authentication():
    """
    Ensure the user is authenticated with Xero and retrieves the tenand ID.
    If authentication is missing, it returns a JSON response prompting login.
    """
    token = get_valid_token()
    if not token:
        return JsonResponse(
            {
                "success": False,
                "redirect_to_auth": True,
                "message": "Your Xero session has expired. Please log in again.",
            },
            status=401,
        )

    tenant_id = cache.get("tenant_id")
    if not tenant_id:
        try:
            tenant_id = get_tenant_id_from_connections()
            cache.set("xero_tenant_id", tenant_id, timeout=1800)
        except Exception as e:
            logger.error(f"Error retrieving tenant ID: {e}")
            return JsonResponse(
                {
                    "success": False,
                    "redirect_to_auth": True,
                    "message": "Unable to fetch Xero tenant ID. Please log in Xero again.",
                },
                status=401,
            )
    return tenant_id


def create_xero_invoice(request, job_id):
    """
    Creates an Invoice in Xero for a given job.
    """
    tenant_id = ensure_xero_authentication()
    if isinstance(
        tenant_id, JsonResponse
    ):  # If the tenant ID is an error message, return it directly
        return tenant_id

    try:
        job = Job.objects.get(id=job_id)
        creator = XeroInvoiceCreator(job)
        response = json.loads(creator.create_document().content.decode())

        if not response.get("success"):
            messages.error(
                request, f"Failed to create invoice: {response.get('error')}"
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": response.get("error"),
                    "messages": extract_messages(request),
                }
            )

        messages.success(request, "Invoice created successfully")
        return JsonResponse(
            {
                "success": True,
                "xero_id": response.get("xero_id"),
                "client": response.get("client"),
                "total_excl_tax": response.get("total_excl_tax"),
                "total_incl_tax": response.get("total_incl_tax"),
                "invoice_url": response.get("invoice_url"),
                "messages": extract_messages(request),
            }
        )
    
    except Exception as e:
        logger.error(f"Error in create_invoice_job: {str(e)}")
        messages.error(request, "An error occurred while creating the invoice")
        return JsonResponse(
            {"success": False, "messages": extract_messages(request)}, status=500
        )


def create_xero_purchase_order(request, purchase_order_id):
    """
    Creates a Purchase Order in Xero for a given purchase order.
    """
    tenant_id = ensure_xero_authentication()
    if isinstance(tenant_id, JsonResponse):  # If the tenant ID is an error message, return it directly
        return tenant_id

    try:
        purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)
        creator = XeroPurchaseOrderCreator(purchase_order)
        response = creator.create_document()
        
        if not response.get("success"):
            messages.error(request, f"Failed to create purchase order: {response.get('error')}")
            return JsonResponse({
                "success": False,
                "error": response.get("error"),
                "messages": extract_messages(request),
            })
        
        messages.success(request, "Purchase order submitted to Xero successfully")
        return JsonResponse({
            "success": True,
            "xero_id": response.get("xero_id"),
            "status": response.get("status"),
            "messages": extract_messages(request),
        })
        
    except Exception as e:
        logger.error(f"Error in create_xero_purchase_order: {str(e)}")
        messages.error(request, "An error occurred while creating the purchase order in Xero")
        return JsonResponse({
            "success": False,
            "error": str(e),
            "messages": extract_messages(request)
        }, status=500)


def create_xero_quote(request: HttpRequest, job_id) -> HttpResponse:
    """
    Creates a quote in Xero for a given job.
    """
    tenant_id = ensure_xero_authentication()
    if isinstance(
        tenant_id, JsonResponse
    ):  # If the tenant ID is an error message, return it directly
        return tenant_id

    try:
        job = Job.objects.get(id=job_id)
        creator = XeroQuoteCreator(job)
        response = json.loads(creator.create_document().content.decode())

        if not response.get("success"):
            messages.error(request, f"Failed to create quote: {response.get('error')}")
            return JsonResponse(
                {
                    "success": False,
                    "error": response.get("error"),
                    "messages": extract_messages(request),
                }
            )
        
        messages.success(request, "Quote created successfully")
        return JsonResponse(
            {
                "success": True,
                "xero_id": response.get("xero_id"),
                "client": response.get("client"),
                "quote_url": response.get("quote_url"),
                "messages": extract_messages(request),
            }
        )

    except Exception as e:
        logger.error(f"Error in create_xero_quote: {str(e)}")
        messages.error(request, f"An error occurred while creating the quote: {str(e)}")
        return JsonResponse(
            {"success": False, "messages": extract_messages(request)}, status=500
        )


def delete_xero_invoice(request: HttpRequest, job_id) -> HttpResponse:
    """
    Deletes an invoice in Xero for a given job.
    """
    tenant_id = ensure_xero_authentication()
    if isinstance(
        tenant_id, JsonResponse
    ):  # If the tenant ID is an error message, return it directly
        return tenant_id

    try:
        job = Job.objects.get(id=job_id)
        creator = XeroInvoiceCreator(job)
        response = json.loads(creator.delete_document().content.decode())
        if not response.get("success"):
            messages.error(
                request, f"Failed to delete invoice: {response.get("error")}"
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": response.get("error"),
                    "messages": extract_messages(request),
                },
                status=400,
            )

        messages.success(request, "Invoice deleted successfully")
        return JsonResponse({"success": True, "messages": extract_messages(request)})

    except Exception as e:
        logger.error(f"Error in delete_xero_invoice: {str(e)}")
        messages.error(
            request, f"An error occurred while deleting the invoice: {str(e)}"
        )
        return JsonResponse(
            {"success": False, "messages": extract_messages(request)}, status=500
        )


def delete_xero_quote(request: HttpRequest, job_id: uuid) -> HttpResponse:
    """
    Deletes a quote in Xero for a given job.
    """
    tenant_id = ensure_xero_authentication()
    if isinstance(
        tenant_id, JsonResponse
    ):  # If the tenant ID is an error message, return it directly
        return tenant_id

    try:
        job = Job.objects.get(id=job_id)
        creator = XeroQuoteCreator(job)
        response = json.loads(creator.delete_document().content.decode())

        if not response.get("success"):
            messages.error(request, f"Failed to delete quote: {response.get("error")}")
            return JsonResponse(
                {"success": False, "error": response.get("error"), "messages": extract_messages(request)},
                status=400,
            )

        messages.success(request, "Quote deleted successfully")
        return JsonResponse({"success": True, "messages": extract_messages(request)})

    except Exception as e:
        logger.error(f"Error in delete_xero_quote: {str(e)}")
        messages.error(request, f"An error occurred while deleting the quote: {str(e)}")
        return JsonResponse(
            {"success": False, "messages": extract_messages(request)}, status=500
        )


def xero_disconnect(request):
    """
    Disconnects from Xero by clearing the token from cache and database.
    """
    try:
        # Clear from cache
        cache.delete('xero_token')
        cache.delete('xero_tenant_id')
        
        # Clear from database
        XeroToken.objects.all().delete()
        
        messages.success(request, "Successfully disconnected from Xero")
    except Exception as e:
        logger.error(f"Error disconnecting from Xero: {str(e)}")
        messages.error(request, "Failed to disconnect from Xero")
    
    return redirect("/")


class XeroIndexView(TemplateView):
    """Note this page is currently inaccessible.  We are using a dropdown menu instead.
    Kept as of 2025-01-07 in case we change our mind"""

    template_name = "xero_index.html"


def xero_sync_progress_page(request):
    """Render the Xero sync progress page."""
    try:
        # First try to get a valid token
        token = get_valid_token()
        if not token:
            logger.info("No valid token found, redirecting to Xero authentication")
            return redirect("api_xero_authenticate")
            
        # Get entities list from xero_tags
        from workflow.templatetags.xero_tags import XERO_ENTITIES
            
        # Render the progress page with entities data
        return render(request, "xero/xero_sync_progress.html", {
            'XERO_ENTITIES': XERO_ENTITIES
        })
    except Exception as e:
        logger.error(f"Error accessing sync progress page: {str(e)}")
        if "token" in str(e).lower():
            return redirect("api_xero_authenticate")
        return render(request, "general/generic_error.html", {"error_message": str(e)})


def get_xero_sync_info(request):
    """Get current sync status and last sync times."""
    try:
        # First verify we have a valid token
        token = get_valid_token()
        if not token:
            return JsonResponse({
                'error': 'No valid Xero token. Please authenticate.',
                'redirect_to_auth': True
            }, status=401)

        # Get last sync times for each entity in the order we sync them
        last_syncs = {
            'accounts': XeroAccount.objects.order_by('-xero_last_synced').first().xero_last_synced if XeroAccount.objects.exists() else None,
            'contacts': Client.objects.order_by('-xero_last_synced').first().xero_last_synced if Client.objects.exists() else None,
            'invoices': Invoice.objects.order_by('-xero_last_synced').first().xero_last_synced if Invoice.objects.exists() else None,
            'bills': Bill.objects.order_by('-xero_last_synced').first().xero_last_synced if Bill.objects.exists() else None,
            'quotes': Quote.objects.order_by('-xero_last_synced').first().xero_last_synced if Quote.objects.exists() else None,
            'purchase_orders': PurchaseOrder.objects.order_by('-xero_last_synced').first().xero_last_synced if PurchaseOrder.objects.exists() else None,
            'credit_notes': CreditNote.objects.order_by('-xero_last_synced').first().xero_last_synced if CreditNote.objects.exists() else None,
            'journals': XeroJournal.objects.order_by('-xero_last_synced').first().xero_last_synced if XeroJournal.objects.exists() else None,
        }

        # Get sync range message
        sync_range = "Syncing data since last successful sync"

        # Check if a sync is in progress using the lock
        sync_in_progress = cache.get('xero_sync_lock', False)

        return JsonResponse({
            'last_syncs': last_syncs,
            'sync_range': sync_range,
            'sync_in_progress': sync_in_progress
        })
    except Exception as e:
        logger.error(f"Error getting sync info: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def start_xero_sync(request):
    """View function to handle Xero sync requests"""
    try:
        # Start the sync process
        sync_generator = synchronise_xero_data()
        # Return success response
        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.error(f"Error starting Xero sync: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
