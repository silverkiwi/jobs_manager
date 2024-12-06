import json
import logging
import time
import uuid
from datetime import date, datetime, timedelta
from uuid import UUID

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import transaction
from django.db.models import Max
from xero_python.accounting import AccountingApi

from workflow.api.xero.xero import api_client, get_tenant_id
from workflow.models import BillLineItem
from workflow.models.client import Client
from workflow.models.invoice import Bill, Invoice, InvoiceLineItem, CreditNote, \
    CreditNoteLineItem
from workflow.models.xero_account import XeroAccount

logger = logging.getLogger(__name__)


def set_invoice_or_bill_fields(document, document_type):
    """
    Process either an invoice or bill from Xero.

    Args:
        document: Instance of XeroInvoiceOrBill
        document_type: String either "INVOICE" or "BILL"
    """

    if not document.raw_json:
        raise ValueError(
            f"{document_type.title()} raw_json is empty. We better not try to process it")


    is_invoice = document.raw_json.get('_type') == 'ACCREC'
    is_bill = document.raw_json.get('_type') == 'ACCPAY'
    is_credit_note = document.raw_json.get('_type') in ['ACCRECCREDIT', 'ACCPAYCREDIT']

    if is_invoice:
        json_document_type = "INVOICE"
    elif is_bill:
        json_document_type = "BILL"
    elif is_credit_note:
        json_document_type = "CREDIT_NOTE"

    # Validate the document matches the type
    if document_type != json_document_type:
        raise ValueError(
            f"Document type mismatch. Got {document_type} but document appears to be a {json_document_type}"
        )


    raw_data = document.raw_json

    # Common fields that are identical between invoices and bills
    if is_credit_note:
        document.xero_id = raw_data.get("_credit_note_id")
        document.number = raw_data.get("_credit_note_number")
    else:
        document.xero_id = raw_data.get("_invoice_id")
        document.number = raw_data.get("_invoice_number")
    document.date = raw_data.get("_date")
    document.due_date = raw_data.get("_due_date")
    document.status = raw_data.get("_status")
    document.tax = raw_data.get("_total_tax")
    document.total_excl_tax = raw_data.get("_sub_total")
    document.total_incl_tax = raw_data.get("_total")
    if document_type == "CREDIT_NOTE":
        document.amount_due = raw_data.get("_remaining_credit")
    else:
        document.amount_due = raw_data.get("_amount_due")
    document.xero_last_modified = raw_data.get("_updated_date_utc")

    # Set or create the client/supplier
    contact_data = raw_data.get("_contact", {})
    contact_id = contact_data.get("_contact_id")
    contact_name = contact_data.get("_name")
    client = Client.objects.filter(xero_contact_id=contact_id).first()
    if not client:
        raise ValueError(f"Client not found for {document_type.lower()} {document.number}")
    document.client = client

    document.save()

    # Handle line items
    line_items_data = raw_data.get("_line_items", [])
    amount_type = raw_data.get('_line_amount_types', {}).get('_value_')

    # Determine which line item model to use
    LineItemModel = (
        InvoiceLineItem if is_invoice else
        BillLineItem if is_bill else
        CreditNoteLineItem if is_credit_note else
        None
    )
    document_field = (
        'invoice' if is_invoice else
        'bill' if is_bill else
        'credit_note' if is_credit_note else
        None
    )

    for line_item_data in line_items_data:
        line_item_id = line_item_data.get("_line_item_id")
        xero_line_id = uuid.UUID(line_item_id)
        description = line_item_data.get("_description") or "No description provided"
        quantity = line_item_data.get("_quantity", 1)
        unit_price = line_item_data.get("_unit_amount",1)

        try:
            line_amount = float(line_item_data.get("_line_amount", 0))
            tax_amount = float(line_item_data.get("_tax_amount", 0))
        except (TypeError, ValueError):
            line_amount = 0
            tax_amount = 0

        # Fix for the GST calculation bug
        if amount_type == 'Inclusive':
            line_amount_excl_tax = line_amount - tax_amount
            line_amount_incl_tax = line_amount
        else:
            line_amount_excl_tax = line_amount
            line_amount_incl_tax = line_amount + tax_amount

        # Fetch the account
        account_code = line_item_data.get("_account_code")
        account = XeroAccount.objects.filter(account_code=account_code).first()

        # Sync the line item using dynamic field name
        kwargs = {
            document_field: document,
            "xero_line_id": xero_line_id
        }
        line_item, created = LineItemModel.objects.update_or_create(
            **kwargs,
            defaults={
                "quantity": quantity,
                "unit_price": unit_price,
                "description": description,
                "account": account,
                "tax_amount": tax_amount,
                "line_amount_excl_tax": line_amount_excl_tax,
                "line_amount_incl_tax": line_amount_incl_tax,
            },
        )
        # print(f"{'Created' if created else 'Updated'} Line Item: "
        #       f"Amount Excl. Tax: {line_item.line_amount_excl_tax}, "
        #       f"Tax Amount: {line_item.tax_amount}, Total Incl. Tax: {line_item.line_amount_incl_tax}")


def set_client_fields(client):
    # Extract relevant fields from raw_json
    if not client.raw_json:
        raise ValueError("Client raw_json is empty.  We better not try to process it")

    raw_data = client.raw_json

    # Extract basic client fields from raw JSON
    client.name = raw_data.get("_name")
    client.email = raw_data.get("_email_address")
    # Handling the phone number
    phones = raw_data.get("_phones", [])
    client.phone = phones[0].get("phone_number", "") if phones else ""

    # Handling the address
    addresses = raw_data.get("addresses", [])
    client.address = addresses[0].get("address_line1", "") if addresses else ""

    # Handling payment terms (keeping the condition from old logic)
    payment_terms = raw_data.get("payment_terms")
    client.is_account_customer = (
        payment_terms is not None and payment_terms.get("sales") is not None
    )

    updated_date_utc = raw_data.get("_updated_date_utc")
    if updated_date_utc:
        client.xero_last_modified = updated_date_utc
    else:
        raise ValueError("Xero last modified date is missing from the raw JSON.")

    # Save the updated client information
    client.save()


def reprocess_invoices():
    """Reprocess all existing invoices to set fields based on raw JSON."""
    for invoice in Invoice.objects.all():
        try:
            set_invoice_or_bill_fields(invoice,"INVOICE")
            logger.info(f"Reprocessed invoice: {invoice.number}")
        except Exception as e:
            logger.error(f"Error reprocessing invoice {invoice.number}: {str(e)}")


def reprocess_bills():
    """Reprocess all existing bills to set fields based on raw JSON."""
    for bill in Bill.objects.all():
        try:
            set_invoice_or_bill_fields(bill,"BILL")
            logger.info(f"Reprocessed bill: {bill.number}")
        except Exception as e:
            logger.error(f"Error reprocessing bill {bill.number}: {str(e)}")

def reprocess_credit_notes():
    """Reprocess all existing credit notes to set fields based on raw JSON."""
    for credit_note in CreditNote.objects.all():
        try:
            set_invoice_or_bill_fields(credit_note,"CREDIT NOTE")
            logger.info(f"Reprocessed credit note: {credit_note.number}")
        except Exception as e:
            logger.error(f"Error reprocessing credit note {credit_note.number}: {str(e)}")

def reprocess_clients():
    """Reprocess all existing clients to set fields based on raw JSON."""
    for client in Client.objects.all():
        try:
            set_client_fields(client)
            logger.info(f"Reprocessed client: {client.name}")
        except Exception as e:
            logger.error(f"Error reprocessing client {client.name}: {str(e)}")


def reprocess_all():
    """Reprocesses all data to set fields based on raw JSON."""
    # NOte, we don't have a reprocess accounts because it just feels too weird.
    # If you break accounts, you probably want to handle it manually
    reprocess_clients()
    reprocess_invoices()
    reprocess_bills()


def sync_xero_data(
    xero_entity_type,
    xero_api_function,
    sync_function,
    last_modified_time,
    additional_params=None,
    supports_pagination=True,
):

    logger.info(
        f"Syncing Xero data... Entity: {xero_entity_type}, since {last_modified_time}"
    )

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
            params.update(
                {
                    "page": page,
                    "page_size": page_size,
                }
            )

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
    last_modified_time = model.objects.aggregate(Max("xero_last_modified"))[
        "xero_last_modified__max"
    ]
    if last_modified_time:
        # The handling of milliseconds differs between django and Xero.  This simplifies things by simply syncing them again
        last_modified_time = last_modified_time - timedelta(seconds=1)

    if last_modified_time:
        last_modified_str = last_modified_time.isoformat()
    else:
        last_modified_str = "2000-01-01T00:00:00Z"

    logger.info(f"{model.__name__}: Using last_modified_time={last_modified_str}")

    return last_modified_str


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


def remove_junk_json_fields(data):
    """We delete currency fields because they're really bulky and repeated on every invoice"""
    exclude_keys = {"_currency_code", "_currency_rate"}

    if isinstance(data, dict):
        # Recursively remove currency fields from the dictionary
        return {
            key: remove_junk_json_fields(value)
            for key, value in data.items()
            if key not in exclude_keys
        }
    elif isinstance(data, list):
        # Recursively apply this function for lists of items
        return [remove_junk_json_fields(item) for item in data]
    else:
        return data  # Base case: return data as-is if it's not a dict or list

def clean_raw_json(data):
    def is_unwanted_field(key, value):
        unwanted_patterns = ["_value2member_map_", "_generate_next_value_", "_member_names_", "__objclass__"]
        return any(pattern in key for pattern in unwanted_patterns)

    def recursively_clean(data):
        if isinstance(data, dict):
            return {
                k: recursively_clean(v) for k, v in data.items()
                if not is_unwanted_field(k, v)
            }
        elif isinstance(data, list):
            return [recursively_clean(i) for i in data]
        else:
            return data

    return recursively_clean(data)


def sync_invoices(invoices):
    """Sync Xero invoices (ACCREC)."""
    for inv in invoices:
        xero_id = getattr(inv, "invoice_id")

        # Retrieve the client for the invoice first
        client = Client.objects.filter(xero_contact_id=inv.contact.contact_id).first()
        if not client:
            logger.warning(f"Client not found for invoice {inv.invoice_number}")
            raise ValueError(f"Client not found for invoice {inv.invoice_number}")

        dirty_raw_json = serialise_xero_object(inv)
        raw_json = clean_raw_json(dirty_raw_json)

        # Retrieve or create the invoice (without saving initially)
        try:
            invoice = Invoice.objects.get(xero_id=xero_id)
            created = False
        except Invoice.DoesNotExist:
            invoice = Invoice(xero_id=xero_id, client=client)
            created = True

        # Perform the rest of the operations
        try:
            # Update raw_json
            invoice.raw_json = raw_json

            # Set other fields from raw_json using set_invoice_fields
            set_invoice_or_bill_fields(invoice,"INVOICE")

            # Log whether the invoice was created or updated
            if created:
                logger.info(
                    f"New invoice added: {invoice.number} updated_at={invoice.xero_last_modified}"
                )
            else:
                logger.info(
                    f"Updated invoice: {invoice.number} updated_at={invoice.xero_last_modified}"
                )

        except Exception as e:
            logger.error(f"Error processing invoice {inv.invoice_number}: {str(e)}")
            logger.error(f"Invoice data: {raw_json}")
            raise


def sync_bills(bills):
    """Sync Xero bills (ACCPAY)."""
    for bill_data in bills:
        xero_id = getattr(bill_data, "invoice_id")
        dirty_raw_json = serialise_xero_object(bill_data)
        raw_json = clean_raw_json(dirty_raw_json)
        bill_number = raw_json["_invoice_number"]
        # Retrieve the client for the bill first
        client = Client.objects.filter(
            xero_contact_id=bill_data.contact.contact_id
        ).first()
        if not client:
            logger.warning(f"Client not found for bill {bill_number}")
            continue

        # Retrieve or create the bill without saving immediately
        try:
            bill = Bill.objects.get(xero_id=xero_id)
            created = False
        except Bill.DoesNotExist:
            bill = Bill(xero_id=xero_id, client=client)
            created = True

        # Now perform the rest of the operations, ensuring everything is set before saving
        try:
            # Update raw_json and other necessary fields
            bill.raw_json = raw_json

            # Set other fields using set_bill_fields (which also saves the bill)
            set_invoice_or_bill_fields(bill,"BILL")

            # Log whether the bill was created or updated
            if created:
                logger.info(
                    f"New bill added: {bill.number} updated_at={bill.xero_last_modified}"
                )
            else:
                logger.info(
                    f"Updated bill: {bill.number} updated_at={bill.xero_last_modified}"
                )

        except Exception as e:
            logger.error(f"Error processing bill {bill_number}: {str(e)}")
            logger.error(f"Bill data: {raw_json}")
            raise

def sync_credit_notes(notes):
    """Sync Xero credit notes."""
    for note_data in notes:
        xero_id = getattr(note_data, "credit_note_id")
        dirty_raw_json = serialise_xero_object(note_data)
        raw_json = clean_raw_json(dirty_raw_json)
        note_number = raw_json["_credit_note_number"]
        # Retrieve the client for the credit note first
        client = Client.objects.filter(
            xero_contact_id=note_data.contact.contact_id
        ).first()
        if not client:
            logger.warning(f"Client not found for credit note {note_number}")
            continue

        # Retrieve or create the credit note without saving immediately
        try:
            note = CreditNote.objects.get(xero_id=xero_id)
            created = False
        except CreditNote.DoesNotExist:
            note = CreditNote(xero_id=xero_id, client=client)
            created = True

        # Now perform the rest of the operations, ensuring everything is set before saving
        try:
            # Update raw_json and other necessary fields
            note.raw_json = raw_json

            # Set other fields using set_invoice_or_bill_fields
            set_invoice_or_bill_fields(note,"CREDIT_NOTE")

            # Log whether the credit note was created or updated
            if created:
                logger.info(
                    f"New credit note added: {note.number} updated_at={note.xero_last_modified}"
                )
            else:
                logger.info(
                    f"Updated credit note: {note.number} updated_at={note.xero_last_modified}"
                )

        except Exception as e:
            logger.error(f"Error processing credit note {note_number}: {str(e)}")
            logger.error(f"Note data: {raw_json}")
            raise

def sync_clients(xero_contacts):
    for contact_data in xero_contacts:
        xero_contact_id = getattr(contact_data, "contact_id", None)

        raw_json_with_currency = serialise_xero_object(contact_data)
        raw_json = remove_junk_json_fields(
            raw_json_with_currency
        )  # Client doesn't have any currency fields but kept for consistancy

        try:
            client = Client.objects.get(xero_contact_id=xero_contact_id)
            created = False
        except Client.DoesNotExist:
            client = Client(xero_contact_id=xero_contact_id)
            created = True

        try:
            client.raw_json = raw_json
            set_client_fields(client)

            if created:
                logger.info(
                    f"New client added: {client.name} updated_at={client.xero_last_modified}"
                )
            else:
                logger.info(
                    f"Updated client: {client.name} updated_at={client.xero_last_modified}"
                )
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
        xero_last_modified = getattr(account_data, "_updated_date_utc", None)

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
                    "xero_last_modified": xero_last_modified,
                    "raw_json": raw_json,
                },
            )

            if created:
                logger.info(
                    f"New account added: {account.account_name} ({account.account_code})"
                )
            else:
                logger.info(
                    f"Updated account: {account.account_name} ({account.account_code})"
                )
        except Exception as e:
            logger.error(f"Error processing account {account_name}: {str(e)}")
            logger.error(f"Account data: {raw_json}")
            raise


def sync_client_to_xero(client):
    """
    Sync a client from the local database to Xero - either a new one, or after a change
    """

    # Step 1: Validate client data before attempting to sync
    if not client.validate_for_xero():
        logger.error(
            f"Client {client.id} failed validation and will not be synced to Xero."
        )
        return False  # Exit early if validation fails

    xero_tenant_id = get_tenant_id()  # Fetch Xero tenant ID
    accounting_api = AccountingApi(api_client)  # Initialize the Accounting API for Xero

    # Step 2: Log sync attempt
    logger.info(f"Attempting to sync client {client.name} with Xero.")

    # Step 3: Prepare client data for Xero using the model method
    contact_data = client.get_client_for_xero()
    if not contact_data:
        logger.error(
            f"Client {client.id} failed validation and will not be synced to Xero."
        )
        return False  # Exit early if validation fails

    # Step 4: Create or update the client in Xero
    try:
        response = accounting_api.create_contacts(
            xero_tenant_id, contacts={"contacts": [contact_data]}
        )
        contacts = response.contacts if response.contacts else []
        logger.info(f"Successfully synced client {client.name} to Xero.")
        return contacts  # Return the synced contacts for further processing
    except Exception as e:
        logger.error(f"Failed to sync client {client.name} to Xero: {str(e)}")
        raise


def single_sync_client(
    client_identifier=None, xero_contact_id=None, client_name=None, delete_local=False
):
    """
    Sync a single client from Xero to the app. Supports lookup by internal ID, Xero ID, or client name.
    Optionally deletes the local client before syncing from Xero if `delete_local` is set to True.
    """
    # Step 1: Initialize APIs
    xero_tenant_id = get_tenant_id()
    accounting_api = AccountingApi(api_client)

    # Step 2: Get the client
    try:
        # Fetch by internal ID if provided
        if client_identifier:
            client = Client.objects.get(id=client_identifier)

        # Fetch by Xero contact ID if provided
        elif xero_contact_id:
            client = Client.objects.get(xero_contact_id=xero_contact_id)

        # Fetch by client name if provided
        elif client_name:
            clients = Client.objects.filter(name=client_name)

            if clients.count() > 1:
                raise MultipleObjectsReturned(
                    f"Multiple clients found for name {client_name}. Please refine the search."
                )
            elif clients.count() == 1:
                client = clients.first()
            else:
                raise ObjectDoesNotExist(f"No client found for name {client_name}.")

        if not client:
            raise ObjectDoesNotExist(
                "No valid client found with the given identifiers."
            )

        logger.info(f"Attempting to sync client {client.name} with Xero.")

    except ObjectDoesNotExist as e:
        logger.error(str(e))
        raise
    except MultipleObjectsReturned as e:
        logger.error(str(e))
        raise

    # Step 3: Optionally delete the client from the local database if delete_local is True
    if delete_local:
        try:
            with transaction.atomic():
                client.delete()
                logger.info(
                    f"Client {client_name or client_identifier} deleted from the database."
                )
        except Client.DoesNotExist:
            logger.info(
                f"Client {client_name or client_identifier} does not exist in the database."
            )

    # Step 4: Fetch the client from Xero
    try:
        response = accounting_api.get_contacts(
            xero_tenant_id,
            i_ds=[xero_contact_id] if xero_contact_id else None,
            where=(
                f'Name=="{client_name}"'
                if client_name and not xero_contact_id
                else None
            ),
        )

        contacts = response.contacts if response.contacts else []
        logger.info(contacts)

        if not contacts:
            logger.error(
                f"Client {client_name or client_identifier} not found in Xero."
            )
            raise

        xero_client = contacts[0]  # Assuming the first match
    except Exception as e:
        logger.error(
            f"Failed to fetch client {client_name or client_identifier} from Xero: {str(e)}"
        )
        raise

    # Step 5: Sync the client back into the database
    try:
        sync_clients([xero_client])  # Call your existing sync function for clients
        logger.info(
            f"Successfully synced client {client_name or client_identifier} back into the database."
        )
    except Exception as e:
        logger.error(
            f"Failed to sync client {client_name or client_identifier} into the database: {str(e)}"
        )
        raise


def single_sync_invoice(
    invoice_identifier=None, xero_invoice_id=None, invoice_number=None
):
    # Step 1: Initialize APIs
    xero_tenant_id = get_tenant_id()
    accounting_api = AccountingApi(api_client)

    # Step 2: Get the invoice
    try:
        # Fetch by internal ID if provided
        if invoice_identifier:
            invoice = Invoice.objects.get(id=invoice_identifier)

        # Fetch by Xero invoice ID if provided
        elif xero_invoice_id:
            invoice = Invoice.objects.get(xero_invoice_id=xero_invoice_id)

        # Fetch by invoice number if provided
        elif invoice_number:
            invoices = Invoice.objects.filter(number=invoice_number)

            if invoices.count() > 1:
                raise MultipleObjectsReturned(
                    f"Multiple invoices found for number {invoice_number}. Please refine the search."
                )
            elif invoices.count() == 1:
                invoice = invoices.first()
            else:
                raise ObjectDoesNotExist(
                    f"No invoice found for number {invoice_number}."
                )

        if not invoice:
            raise ObjectDoesNotExist(
                "No valid invoice found with the given identifiers."
            )

        logger.info(f"Attempting to sync invoice {invoice.number} with Xero.")

    except ObjectDoesNotExist as e:
        logger.error(str(e))
        raise
    except MultipleObjectsReturned as e:
        logger.error(str(e))
        raise

    # Step 3: Delete the invoice from the local database
    try:
        with transaction.atomic():
            invoice.delete()
            logger.info(f"Invoice {invoice_number} deleted from the database.")
    except Invoice.DoesNotExist:
        logger.info(f"Invoice {invoice_number} does not exist in the database.")

    # Step 4: Fetch the invoice from Xero
    try:
        response = accounting_api.get_invoices(
            xero_tenant_id,
            invoice_numbers=[invoice_number],
            #            summary_only=False  # I found I didn't need this.  If we have < 100 invoices then it syncs enough detail
        )

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
        logger.info(
            f"Successfully synced invoice {invoice_number} back into the database."
        )
    except Exception as e:
        logger.error(
            f"Failed to sync invoice {invoice_number} into the database: {str(e)}"
        )


def sync_all_xero_data():
    accounting_api = AccountingApi(api_client)

    our_latest_contact = get_last_modified_time(Client)
    our_latest_invoice = get_last_modified_time(Invoice)
    our_latest_bill = get_last_modified_time(Bill)
    our_latest_credit_note = get_last_modified_time(CreditNote)
    our_latest_account = get_last_modified_time(XeroAccount)

    # Just put here for lazy debugging since I can trigger this with a button
    # invoice = Invoice.objects.filter(number="INV-54021").first()
    # set_invoice_or_bill_fields(invoice, "INVOICE")
    #reprocess_all()

    sync_xero_data(
        xero_entity_type="accounts",
        xero_api_function=accounting_api.get_accounts,
        sync_function=sync_accounts,
        last_modified_time=our_latest_account,
        supports_pagination=False,
    )

    sync_xero_data(
        xero_entity_type="contacts",
        xero_api_function=accounting_api.get_contacts,
        sync_function=sync_clients,
        last_modified_time=our_latest_contact,
    )

    sync_xero_data(
        xero_entity_type="invoices",
        xero_api_function=accounting_api.get_invoices,
        sync_function=sync_invoices,
        last_modified_time=our_latest_invoice,
        additional_params={"where": 'Type=="ACCREC"'},
    )
    sync_xero_data(
        xero_entity_type="invoices",
        xero_api_function=accounting_api.get_invoices,
        sync_function=sync_bills,
        last_modified_time=our_latest_bill,
        additional_params={"where": 'Type=="ACCPAY"'},
    )

    sync_xero_data(
        xero_entity_type="credit_notes",
        xero_api_function=accounting_api.get_credit_notes,
        sync_function=sync_credit_notes,
        last_modified_time=our_latest_credit_note,
    )
