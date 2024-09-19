import uuid
from decimal import Decimal

from django.db import models

from workflow.enums import InvoiceStatus
from workflow.models.client import Client


class XeroInvoiceOrBill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # Internal UUID
    xero_id = models.UUIDField(unique=True)
    number = models.CharField(max_length=255)
    client = models.ForeignKey("Client", on_delete=models.CASCADE)
    date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=InvoiceStatus.choices,default=InvoiceStatus.DRAFT)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    last_modified = models.DateTimeField()
    raw_json = models.JSONField()

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.number} - {self.client.name}"


class Invoice(XeroInvoiceOrBill):

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"


class Bill(XeroInvoiceOrBill):

    class Meta:
        verbose_name = "Bill"
        verbose_name_plural = "Bills"

    @property
    def vendor(self):
        """Return the client as 'vendor' for bills."""
        return self.client


class InvoiceLineItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # Internal UUID
    invoice = models.ForeignKey("Invoice", on_delete=models.CASCADE, related_name="line_items")  # Link to Invoice
    description = models.TextField()  # Description of the line item
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))  # Quantity
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # Unit price
    line_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Total line amount (quantity * unit price)
    account = models.ForeignKey("XeroAccount", on_delete=models.SET_NULL, null=True, blank=True)  # Link to XeroAccount
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Tax amount for the line item
    tax_type = models.CharField(max_length=50, null=True, blank=True)  # Optional, in case tax types vary in the future

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.description} - {self.total_price}"

# Line items specific to Bills
class BillLineItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # Internal UUID
    bill = models.ForeignKey("Bill", on_delete=models.CASCADE, related_name="line_items")  # Link to Bill
    description = models.TextField()  # Description of the line item
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))  # Quantity
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # Unit price
    line_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Total line amount (quantity * unit price)
    account = models.ForeignKey("XeroAccount", on_delete=models.SET_NULL, null=True, blank=True)  # Link to XeroAccount
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Tax amount for the line item
    tax_type = models.CharField(max_length=50, null=True, blank=True)  # Optional, in case tax types vary in the future

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.description} - {self.total_price}"
