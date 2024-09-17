import json
from datetime import datetime, date
from uuid import UUID
import logging

from django.db.models import Max
from xero_python.accounting import AccountingApi
from xero_python.identity import IdentityApi

from workflow.models.client import Client
from workflow.xero.xero import api_client

logger = logging.getLogger(__name__)

def sync_xero_contacts():
    contacts_last_modified_time = get_last_client_modified_time()

    accounting_api = AccountingApi(api_client)
    identity_api = IdentityApi(api_client)
    connections = identity_api.get_connections()

    if not connections:
        raise Exception("No Xero tenants found.")

    xero_tenant_id = connections[0].tenant_id
    contacts = accounting_api.get_contacts(xero_tenant_id, if_modified_since=contacts_last_modified_time)

    # Call the sync_clients function to update or create clients in the local DB
    sync_clients(contacts.contacts)


def get_last_client_modified_time():
    """Fetch the latest 'updated_date_utc' from the Client model, or default to a far past date."""
    last_modified_time = Client.objects.aggregate(Max('last_modified'))['last_modified__max']

    # Return the actual last modified time or default to a far past date
    return last_modified_time.isoformat() if last_modified_time else '2000-01-01T00:00:00Z'


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
    elif hasattr(obj, '__dict__'):
        return serialise_xero_object(obj.__dict__)
    else:
        return str(obj)


def sync_clients(xero_contacts):
    for contact_data in xero_contacts:
        xero_contact_id = getattr(contact_data, 'contact_id', None),  # Safe access to contact_id
        contact_groups = getattr(contact_data, 'contact_groups', [])
        payment_terms = getattr(contact_data, 'payment_terms', None)
        is_account_customer = payment_terms is not None and getattr(payment_terms, 'sales', None) is not None

        raw_json = serialise_xero_object(contact_data)

        # Extract necessary information for the Client model
        phone = contact_data.phones[0].phone_number if contact_data.phones else ''
        address = contact_data.addresses[0].address_line1 if contact_data.addresses else ''

        client, created = Client.objects.update_or_create(
            xero_contact_id=getattr(contact_data, 'contact_id', None),
            defaults={
                'name': contact_data.name,
                'email': contact_data.email_address,
                'phone': phone,
                'address': address,
                'is_account_customer': is_account_customer,
                'raw_json': raw_json
            }
        )


        if created:
            logger.info(f"New client added: {client.name}")
        else:
            logger.info(f"Updated client: {client.name}")


def sync_xero_data():
    sync_xero_contacts()
