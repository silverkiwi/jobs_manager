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


def sync_clients(xero_contacts):
    for contact_data in xero_contacts:
        xero_contact_id = getattr(contact_data, 'contact_id', None),  # Safe access to contact_id
        contact_groups = getattr(contact_data, 'contact_groups', [])
        is_account_customer = any(group['Name'] == 'Account Customers' for group in contact_groups)

        client, created = Client.objects.update_or_create(
            xero_contact_id=getattr(contact_data, 'contact_id', None),
            defaults={
                'name': getattr(contact_data, 'name', None),
                'email': getattr(contact_data, 'email_address', None),
                'phone': getattr(contact_data, 'phones', [None])[0].phone_number if getattr(contact_data, 'phones', None) else None,
                'address': getattr(contact_data, 'addresses', [None])[0].address_line1 if getattr(contact_data, 'addresses', None) else None,
                'is_account_customer': is_account_customer,  # Set based on contact groups
            }
        )


        if created:
            logger.info(f"New client added: {client.name}")
        else:
            logger.info(f"Updated client: {client.name}")


def sync_xero_data():
    sync_xero_contacts()
