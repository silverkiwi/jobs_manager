from django.db import models
from django.utils import timezone

class XeroToken(models.Model):
    tenant_id = models.CharField(max_length=100, unique=True)
    token_type = models.CharField(max_length=50)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"Xero Token for Tenant: {self.tenant_id}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
