import os
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Max
from django.utils import timezone

from apps.workflow.enums import MetalType
from apps.workflow.helpers import get_company_defaults
from apps.workflow.models import CompanyDefaults

from django.db.models import Max, IntegerField
from django.db.models.functions import Cast, Substr



class PurchaseOrder(models.Model):
    """A request to purchase materials from a supplier."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    supplier = models.ForeignKey(
        "Client",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        null=True,
        blank=True,
    )
    job = models.ForeignKey(
        "job.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Primary job this PO is for",
    )
    po_number = models.CharField(max_length=50, unique=True)
    reference = models.CharField(max_length=100, blank=True, null=True, help_text="Optional reference for the purchase order")
    order_date = models.DateField(default=timezone.now)
    expected_delivery = models.DateField(null=True, blank=True)
    xero_id = models.UUIDField(unique=True, null=True, blank=True)
    xero_tenant_id = models.CharField(
            max_length=255, null=True, blank=True
        ) # For reference only - we are not fully multi-tenant yet
    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"),
            ("submitted", "Submitted to Supplier"),
            ("partially_received", "Partially Received"),
            ("fully_received", "Fully Received"),
            ("deleted", "Deleted"),
        ],
        default="draft",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    xero_last_modified = models.DateTimeField(null=True, blank=True)
    xero_last_synced = models.DateTimeField(null=True, blank=True, default=timezone.now)
    online_url = models.URLField(max_length=500, null=True, blank=True)

    def generate_po_number(self):
        """Generate the next sequential PO number based on the configured prefix."""
        defaults = get_company_defaults()
        start = defaults.starting_po_number
        po_prefix = defaults.po_prefix # Get prefix from CompanyDefaults

        prefix_len = len(po_prefix)

        # 1) Filter to exactly <prefix><digits> (removed hyphen from regex)
        # 2) Strip off "<prefix>" (first prefix_len chars), cast the rest to int
        # 3) Take the MAX of that numeric part
        agg = (
            PurchaseOrder.objects
                .filter(po_number__regex=rf"^{po_prefix}\d+$")
                .annotate(num=Cast(Substr("po_number", prefix_len + 1), IntegerField()))
                .aggregate(max_num=Max("num"))
        )
        max_existing = agg["max_num"] or 0

        nxt = max(start, max_existing + 1)
        return f"{po_prefix}{nxt:04d}" # Use the dynamic prefix

    def save(self, *args, **kwargs):
        """Save the model and auto-generate PO number if none exists."""
        if not self.po_number:
            self.po_number = self.generate_po_number()

        super().save(*args, **kwargs)

    def reconcile(self):
        """Check received quantities against ordered quantities."""
        for line in self.po_lines.all():
            total_received = sum(
                po_line.quantity for po_line in line.received_lines.all()
            )
            if total_received > line.quantity:
                return "Over"
            elif total_received < line.quantity:
                return "Partial"

        self.status = "fully_received"
        self.save()
        return "Reconciled"


class PurchaseOrderLine(models.Model):
    """A line item on a PO."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="po_lines"
    )
    job = models.ForeignKey(
        "job.Job",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="purchase_order_lines",
        help_text="The job this purchase line is for",
    )
    description = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    dimensions = models.CharField(max_length=255, blank=True, null=True, help_text="Dimensions such as length, width, height, etc.")
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_tbc = models.BooleanField(default=False, help_text="If true, the price is to be confirmed and unit cost will be None")
    supplier_item_code = models.CharField(max_length=50, blank=True, null=True, help_text="Supplier's own item code/SKU")
    received_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total quantity received against this line",
    )
    metal_type = models.CharField(
        max_length=100,
        choices=MetalType.choices,
        default=MetalType.UNSPECIFIED,
        blank=True,
        null=True,
    )
    alloy = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Alloy specification (e.g., 304, 6061)"
    )
    specifics = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Specific details (e.g., m8 countersunk socket screw)"
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Where this item will be stored"
    )
    dimensions = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Dimensions such as length, width, height, etc."
    )
    raw_line_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Raw JSON data from the source system or document"
    )


class PurchaseOrderSupplierQuote(models.Model):
    """A quote file attached to a purchase order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.OneToOneField(PurchaseOrder, related_name="supplier_quote", on_delete=models.CASCADE)
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
