import os
import uuid

from django.conf import settings
from django.db import models


class PurchaseOrderSupplierQuote(models.Model):
    """A quote file attached to a purchase order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.OneToOneField(
        "purchasing.PurchaseOrder", 
        related_name="supplier_quote", 
        on_delete=models.CASCADE
    )
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    mime_type = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    extracted_data = models.JSONField(null=True, blank=True, help_text="Extracted data from the quote")
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("deleted", "Deleted")],
        default="active",
    )

    @property
    def full_path(self):
        """Full system path to the file."""
        return os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, self.file_path)

    @property
    def url(self):
        """URL to serve the file."""
        return f"/purchases/quotes/{self.file_path}"

    @property
    def size(self):
        """Return size of file in bytes."""
        if self.status == "deleted":
            return None

        file_path = self.full_path
        return os.path.getsize(file_path) if os.path.exists(file_path) else None

    class Meta:
        db_table = 'workflow_purchaseordersupplierquote'
