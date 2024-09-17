from django.db import models

from workflow.models.client import Client


class XeroInvoiceOrBill(models.Model):
    xero_id = models.UUIDField(unique=True)
    number = models.CharField(max_length=255)
    client = models.ForeignKey("Client", on_delete=models.CASCADE)
    date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50)
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
