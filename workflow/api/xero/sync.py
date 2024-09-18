import logging
import time
from datetime import date, datetime
from uuid import UUID

from django.db import transaction
from django.db.models import Max
from xero_python.accounting import AccountingApi
from xero_python.identity import IdentityApi

from workflow.models.client import Client
from workflow.models.invoice import Bill, Invoice
from workflow.xero.xero import api_client

logger = logging.getLogger(__name__)


def sync_xero_data(
    xero_entity_type,
    xero_api_function,
    sync_function,
    last_modified_time,
    additional_params=None,
):

    logger.info(f"Syncing Xero data... Entity: {xero_entity_type}, since {last_modified_time}")
    identity_api = IdentityApi(api_client)
    connections = identity_api.get_connections()

    if not connections:
        raise Exception("No Xero tenants found.")

    xero_tenant_id = connections[0].tenant_id

    page = 1
    page_size = 500
    while True:
        params = {
            "xero_tenant_id": xero_tenant_id,
            "if_modified_since": last_modified_time,
            "order": "UpdatedDateUTC ASC",
            "page": page,
            "page_size": page_size,
        }

        if additional_params:
            params.update(additional_params)

        entities = xero_api_function(**params)

        if not getattr(entities, xero_entity_type):
            break  # No more entities to process

        sync_function(getattr(entities, xero_entity_type))

        # Check if we've processed all pages
        if page >= entities.pagination.page_count:
            break

        page += 1
        time.sleep(5)  # Respect Xero's rate limits


def get_last_modified_time(model):
    """Fetch the latest 'last_modified' from the given model, or default to a far past date."""
    last_modified_time = model.objects.aggregate(Max("last_modified"))[
        "last_modified__max"
    ]
    return (
        last_modified_time.isoformat() if last_modified_time else "2000-01-01T00:00:00Z"
    )


def serialise_xero_object(obj):
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, (list, tuple)):
        return [serialise_xero_object(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: serialise_xero_object(value) for key, value in obj.items()}
    elif hasattr(obj, "__dict__"):
        return serialise_xero_object(obj.__dict__)
    else:
        return str(obj)


def remove_currency_fields(data):
    """We delete currency fields because they're really bulky and repeated on every invoice"""
    exclude_keys = {"_currency_code", "_currency_rate"}

    if isinstance(data, dict):
        # Recursively remove currency fields from the dictionary
        return {
            key: remove_currency_fields(value)
            for key, value in data.items()
            if key not in exclude_keys
        }
    elif isinstance(data, list):
        # Recursively apply this function for lists of items
        return [remove_currency_fields(item) for item in data]
    else:
        return data  # Base case: return data as-is if it's not a dict or list


def prepare_invoice_or_bill_defaults(doc_data, client):
    """Prepare the default fields for both Invoices and Bills."""
    raw_json_with_currency = serialise_xero_object(doc_data)
    raw_json = remove_currency_fields(raw_json_with_currency)

    defaults = {
        "number": doc_data.invoice_number,
        "client": client,
        "date": doc_data.date,
        "status": doc_data.status,
        "total": doc_data.total,
        "amount_due": doc_data.amount_due,
        "last_modified": doc_data.updated_date_utc,
        "raw_json": raw_json,
    }

    if hasattr(doc_data, "due_date") and doc_data.due_date is not None:
        defaults["due_date"] = doc_data.due_date

    return defaults


def sync_invoices(invoices):
    """Sync Xero invoices (ACCREC)."""
    for invoice in invoices:
        xero_id = getattr(invoice, "invoice_id", None)

        client = Client.objects.filter(
            xero_contact_id=invoice.contact.contact_id
        ).first()

        if not client:
            logger.warning(f"Client not found for invoice {invoice.invoice_number}")
            continue

        defaults = prepare_invoice_or_bill_defaults(invoice, client)

        try:
            with transaction.atomic():
                _, created = Invoice.objects.update_or_create(
                    xero_id=xero_id, defaults=defaults
                )
                # We don't manipulate invoice after upsert

                if created:
                    logger.info(f"New invoice added: {defaults['number']}")
                else:
                    logger.info(f"Updated invoice: {defaults['number']}")

        except Exception as e:
            logger.error(f"Error processing invoice {invoice.invoice_number}: {str(e)}")
            logger.error(f"Invoice data: {defaults['raw_json']}")
            raise


def sync_bills(bills):
    """Sync Xero bills (ACCPAY)."""
    for bill in bills:
        xero_id = getattr(bill, "invoice_id", None)

        client = Client.objects.filter(xero_contact_id=bill.contact.contact_id).first()

        if not client:
            logger.warning(f"Client not found for bill {bill.invoice_number}")
            continue

        defaults = prepare_invoice_or_bill_defaults(bill, client)

        try:
            with transaction.atomic():
                _, created = Bill.objects.update_or_create(
                    xero_id=xero_id, defaults=defaults
                )
                # We don't actually manipulate the bill object after upsert

                if created:
                    logger.info(f"New bill added: {defaults['number']}")
                else:
                    logger.info(f"Updated bill: {defaults['number']}")

        except Exception as e:
            logger.error(f"Error processing bill {bill.invoice_number}: {str(e)}")
            logger.error(f"Bill data: {defaults['raw_json']}")
            raise

def sync_clients(xero_contacts):
    for contact_data in xero_contacts:
        xero_contact_id = getattr(contact_data, "contact_id", None)
        payment_terms = getattr(contact_data, "payment_terms", None)
        is_account_customer = (
            payment_terms is not None
            and getattr(payment_terms, "sales", None) is not None
        )

        raw_json_with_currency = serialise_xero_object(contact_data)
        raw_json = remove_currency_fields(
            raw_json_with_currency
        )  # Client doesn't have any currency fields but kept for consistancy

        phone = contact_data.phones[0].phone_number if contact_data.phones else ""
        address = (
            contact_data.addresses[0].address_line1 if contact_data.addresses else ""
        )

        try:
            client, created = Client.objects.update_or_create(
                xero_contact_id=xero_contact_id,
                defaults={
                    "name": contact_data.name,
                    "email": contact_data.email_address,
                    "phone": phone,
                    "address": address,
                    "is_account_customer": is_account_customer,
                    "raw_json": raw_json,
                },
            )

            if created:
                logger.info(f"New client added: {client.name}")
            else:
                logger.info(f"Updated client: {client.name}")
        except Exception as e:
            logger.error(f"Error processing client {contact_data.name}: {str(e)}")
            logger.error(f"Client data: {raw_json}")
            raise


def sync_all_xero_data():
    accounting_api = AccountingApi(api_client)

    our_latest_contact = get_last_modified_time(Client)
    our_latest_invoice = get_last_modified_time(Invoice)
    our_latest_bill = get_last_modified_time(Bill)

    sync_xero_data(
        xero_entity_type = "contacts",
        xero_api_function = accounting_api.get_contacts,
        sync_function = sync_clients,
        last_modified_time = our_latest_contact,
    )

    sync_xero_data(
        xero_entity_type = "invoices",
        xero_api_function = accounting_api.get_invoices,
        sync_function = sync_invoices,
        last_modified_time = our_latest_invoice,
        additional_params={"where": 'Type=="ACCREC"'},
    )
    sync_xero_data(
        xero_entity_type = "invoices",
        xero_api_function = accounting_api.get_invoices,
        sync_function = sync_bills,
        last_modified_time = our_latest_bill,
        additional_params={"where": 'Type=="ACCPAY"'},
    )
