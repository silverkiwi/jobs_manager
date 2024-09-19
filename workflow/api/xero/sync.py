import logging
import time
from datetime import date, datetime
from uuid import UUID

from django.db import transaction
from django.db.models import Max
from xero_python.accounting import AccountingApi

from workflow.models import BillLineItem
from workflow.models.client import Client
from workflow.models.invoice import Bill, Invoice, InvoiceLineItem
from workflow.api.xero.xero import api_client, get_tenant_id
from workflow.models.xero_account import XeroAccount


logger = logging.getLogger(__name__)


def sync_xero_data(
    xero_entity_type,
    xero_api_function,
    sync_function,
    last_modified_time,
    additional_params=None,
    supports_pagination=True
):

    logger.info(f"Syncing Xero data... Entity: {xero_entity_type}, since {last_modified_time}")

    xero_tenant_id = get_tenant_id()

    page = 1
    page_size = 100
    while True:
        params = {
            "xero_tenant_id": xero_tenant_id,
            "if_modified_since": last_modified_time,
            "order": "UpdatedDateUTC ASC",
        }

        if supports_pagination:
            params.update({
                "page": page,
                "page_size": page_size,
            })

        if additional_params:
            params.update(additional_params)

        entities = xero_api_function(**params)

        if not getattr(entities, xero_entity_type):
            break  # No more entities to process

        sync_function(getattr(entities, xero_entity_type))

        if not supports_pagination:
            break

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
#        last_modified_time.isoformat() if last_modified_time else "2024-01-01T00:00:00Z"
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
    for inv in invoices:
        xero_id = getattr(inv, "invoice_id", None)

        client = Client.objects.filter(
            xero_contact_id=inv.contact.contact_id
        ).first()

        if not client:
            logger.warning(f"Client not found for invoice {inv.invoice_number}")
            continue

        defaults = prepare_invoice_or_bill_defaults(inv, client)

        try:
            with transaction.atomic():
                invoice, created = Invoice.objects.update_or_create(
                    xero_id=xero_id, defaults=defaults
                )
                invoice_status = getattr(inv, "status", None)
                if invoice_status not in ("DELETED", "VOIDED"):
                    # Now sync the line items
                    line_items_data = getattr(inv,'line_items', [])

                    for line_item_data in line_items_data:
                        description = getattr(line_item_data, "description",None)
                        quantity = getattr(line_item_data, "quantity", 1)
                        unit_price = getattr(line_item_data, "unit_amount", None)
                        account_code = getattr(line_item_data, "account_code", None)
                        tax_amount = getattr(line_item_data, "tax_amount", None)
                        line_amount = getattr(line_item_data, "line_amount", None)

                        # Find the related XeroAccount
                        account = XeroAccount.objects.filter(account_code=account_code).first()

                        # Sync the line item
                        InvoiceLineItem.objects.update_or_create(
                            invoice=invoice,
                            description=description,
                            defaults={
                                "quantity": quantity,
                                "unit_price": unit_price,
                                "account": account,
                                "tax_amount": tax_amount,
                                "line_amount": line_amount,
                            },
                        )

                if created:
                    logger.info(f"New invoice added: {defaults['number']}")
                else:
                    logger.info(f"Updated invoice: {defaults['number']}")

        except Exception as e:
            logger.error(f"Error processing invoice {inv.invoice_number}: {str(e)}")
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
                bill_obj, created = Bill.objects.update_or_create(
                    xero_id=xero_id, defaults=defaults
                )
                # Now sync the line items
                line_items_data = defaults['raw_json'].get('line_items', [])

                for line_item_data in line_items_data:
                    description = getattr(line_item_data, "description",None)
                    quantity = getattr(line_item_data, "quantity", 1)
                    unit_price = getattr(line_item_data, "unit_amount", None)
                    account_code = getattr(line_item_data, "account_code", None)
                    tax_amount = getattr(line_item_data, "tax_amount", None)
                    line_amount = getattr(line_item_data, "line_amount", None)


                    # Find the related XeroAccount
                    account = XeroAccount.objects.filter(account_code=account_code).first()

                    # Sync the line item
                    BillLineItem.objects.update_or_create(
                        bill=bill_obj,
                        description=description,
                        defaults={
                            "quantity": quantity,
                            "unit_price": unit_price,
                            "account": account,
                            "tax_amount": tax_amount,
                            "line_amount": line_amount,
                        },
                    )
                if created:
                    logger.info(f"New bill added: {defaults['number']}")
                else:
                    logger.info(f"Updated bill: {defaults['number']}")

        except Exception as e:
            logger.error(f"Error processing bill {bill_obj.invoice_number}: {str(e)}")
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

def sync_accounts(xero_accounts):
    for account_data in xero_accounts:
        xero_account_id = getattr(account_data, "account_id", None)
        account_code = getattr(account_data, "code", None)
        account_name = getattr(account_data, "name", None)
        account_type = getattr(account_data, "type", None)
        tax_type = getattr(account_data, "tax_type", None)
        description = getattr(account_data, "description", None)
        enable_payments = getattr(account_data, "eenable_payments_to_account", False)
        last_modified = getattr(account_data, "_updated_date_utc", None)

        raw_json = serialise_xero_object(account_data)

        try:
            account, created = XeroAccount.objects.update_or_create(
                xero_id=xero_account_id,
                defaults={
                    "account_code": account_code,
                    "account_name": account_name,
                    "description": description,
                    "account_type": account_type,
                    "tax_type": tax_type,
                    "enable_payments": enable_payments,
                    "last_modified": last_modified,
                    "raw_json": raw_json,
                },
            )

            if created:
                logger.info(f"New account added: {account.account_name} ({account.account_code})")
            else:
                logger.info(f"Updated account: {account.account_name} ({account.account_code})")
        except Exception as e:
            logger.error(f"Error processing account {account_name}: {str(e)}")
            logger.error(f"Account data: {raw_json}")
            raise



def debug_sync_invoice(invoice_number):
    # Step 1: Initialize APIs
    xero_tenant_id = get_tenant_id()
    accounting_api = AccountingApi(api_client)

    # Step 2: Get Xero tenant ID

    # Step 3: Delete the invoice from the local database
    try:
        with transaction.atomic():
            invoice = Invoice.objects.get(number=invoice_number)
            invoice_id = invoice.id
            invoice.delete()
            logger.info(f"Invoice {invoice_number} deleted from the database.")
    except Invoice.DoesNotExist:
        logger.info(f"Invoice {invoice_number} does not exist in the database.")

    # Step 4: Fetch the invoice from Xero
    try:
        response = accounting_api.get_invoices(
            xero_tenant_id,
            invoice_numbers=[invoice_number],
#            summary_only=False
        )
        # response2 = accounting_api.get_invoices(
        #     xero_tenant_id,
        #     invoice_numbers=[invoice_number],
        #     summary_only=False
        # )

        invoices = response.invoices if response.invoices else []
        logging.info(invoices)
        if not invoices:
            logger.error(f"Invoice {invoice_number} not found in Xero.")
            raise
    except Exception as e:
        logger.error(f"Failed to fetch invoice {invoice_number} from Xero: {str(e)}")
        raise

    # Step 5: Sync the invoice back into the database
    try:
        sync_invoices(invoices)  # Call your existing sync function
        logger.info(f"Successfully synced invoice {invoice_number} back into the database.")
    except Exception as e:
        logger.error(f"Failed to sync invoice {invoice_number} into the database: {str(e)}")


def sync_all_xero_data():
    accounting_api = AccountingApi(api_client)

    our_latest_contact = get_last_modified_time(Client)
    our_latest_invoice = get_last_modified_time(Invoice)
    our_latest_bill = get_last_modified_time(Bill)
    our_latest_account = get_last_modified_time(XeroAccount)

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

    sync_xero_data(
        xero_entity_type = "accounts",
        xero_api_function = accounting_api.get_accounts,
        sync_function = sync_accounts,
        last_modified_time = our_latest_account,
        supports_pagination = False
    )