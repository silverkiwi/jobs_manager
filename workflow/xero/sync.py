from workflow.models.client import Client


def sync_clients(xero_contacts):
    for contact_data in xero_contacts:
        is_account_customer = contact_data.get('IsAccountCustomer', False)  # Modify this based on Xero data

        client, created = Client.objects.update_or_create(
            xero_contact_id=contact_data['ContactID'],
            defaults={
                'name': contact_data.get('Name'),
                'email': contact_data.get('EmailAddress'),
                'phone': contact_data.get('Phones')[0]['PhoneNumber'] if contact_data.get('Phones') else None,
                'address': contact_data.get('Addresses')[0]['AddressLine1'] if contact_data.get('Addresses') else None,
                'is_account_customer': is_account_customer,
            }
        )
        if created:
            print(f"New client added: {client.name}")
        else:
            print(f"Updated client: {client.name}")
