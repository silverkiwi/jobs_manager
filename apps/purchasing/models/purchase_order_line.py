import uuid

from django.db import models

from apps.job.enums import MetalType


class PurchaseOrderLine(models.Model):
    """A line item on a PO."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(
        "purchasing.PurchaseOrder", on_delete=models.CASCADE, related_name="po_lines"
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

    class Meta:
        db_table = 'workflow_purchaseorderline'
