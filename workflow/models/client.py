import logging
import uuid

from django.db import models

logger = logging.getLogger(__name__)


class Client(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )  # Internal UUID
    xero_contact_id = models.CharField(
        max_length=255, unique=True, null=True, blank=True
    )
    # Optional because not all prospects are synced to Xero
    name = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    is_account_customer = models.BooleanField(
        default=False
    )  # Account vs cash customer flag
    xero_last_modified = models.DateTimeField(null=False, blank=False)

    raw_json = models.JSONField(
        null=True, blank=True
    )  # For debugging, stores the raw JSON from Xero
    django_created_at = models.DateTimeField(auto_now_add=True)
    django_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def validate_for_xero(self):
        """
        Validate if the client data is sufficient to sync to Xero.
        """
        if not self.name:
            logger.error(f"Client {self.id} does not have a valid name.")
            return False
        if not self.email and not self.phone:
            logger.error(
                f"Client {self.id} needs either a valid email or phone number."
            )
            return False
        # Add more checks as necessary for other fields
        return True

    def get_client_for_xero(self):
        """
        Return the client data in a format suitable for syncing to Xero.
        Maps relevant fields from the model to the Xero API format.
        """
        if self.validate_for_xero() is False:
            return None

        client_dict = {
            "contact_id": self.xero_contact_id if self.xero_contact_id else None,
            "name": self.name,  # Required by Xero
            "email_address": self.email if self.email else None,
            "phones": [
                {
                    "phone_type": "DEFAULT",
                    "phone_number": self.phone if self.phone else None,
                }
            ],
            "addresses": [
                {
                    "address_type": "STREET",
                    "attention_to": self.name,
                    "address_line1": self.address if self.address else None,
                    # Map additional address fields as needed, such as city, region, postal code, etc.
                }
            ],
            "is_customer": self.is_account_customer,  # If relevant to Xero, flag customer vs. cash
            # Add more mappings if necessary, like financial details, account numbers, GST, etc.
        }
        return client_dict
