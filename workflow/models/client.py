import uuid

from django.db import models

class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # Internal UUID
    xero_contact_id = models.CharField(max_length=255, unique=True)  # Xero ContactID
    name = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    is_account_customer = models.BooleanField(default=False)  # Account vs cash customer flag

    def __str__(self):
        return self.name
