import uuid
import logging

from django.db import models
from django.db.models import Max, IntegerField
from django.db.models.functions import Cast, Substr
from django.utils import timezone

from apps.workflow.helpers import get_company_defaults

logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    """A request to purchase materials from a supplier."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    supplier = models.ForeignKey(
        "client.Client",
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
    reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Optional reference for the purchase order",
    )
    order_date = models.DateField(default=timezone.now)
    expected_delivery = models.DateField(null=True, blank=True)
    xero_id = models.UUIDField(unique=True, null=True, blank=True)
    xero_tenant_id = models.CharField(
        max_length=255, null=True, blank=True
    )  # For reference only - we are not fully multi-tenant yet
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
        po_prefix = defaults.po_prefix  # Get prefix from CompanyDefaults

        prefix_len = len(po_prefix)

        # 1) Filter to exactly <prefix><digits> (removed hyphen from regex)
        # 2) Strip off "<prefix>" (first prefix_len chars), cast the rest to int
        # 3) Take the MAX of that numeric part
        agg = (
            PurchaseOrder.objects.filter(po_number__regex=rf"^{po_prefix}\d+$")
            .annotate(num=Cast(Substr("po_number", prefix_len + 1), IntegerField()))
            .aggregate(max_num=Max("num"))
        )
        max_existing = agg["max_num"] or 0

        nxt = max(start, max_existing + 1)
        return f"{po_prefix}{nxt:04d}"  # Use the dynamic prefix

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

    class Meta:
        db_table = "workflow_purchaseorder"
