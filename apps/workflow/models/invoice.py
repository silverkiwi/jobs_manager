from apps.accounting.models import (
    Invoice as _Invoice,
    Bill as _Bill,
    CreditNote as _CreditNote,
    InvoiceLineItem as _InvoiceLineItem,
    BillLineItem as _BillLineItem,
    CreditNoteLineItem as _CreditNoteLineItem,
)


class Invoice(_Invoice):
    class Meta:
        proxy = True


class Bill(_Bill):
    class Meta:
        proxy = True


class CreditNote(_CreditNote):
    class Meta:
        proxy = True


class InvoiceLineItem(_InvoiceLineItem):
    class Meta:
        proxy = True


class BillLineItem(_BillLineItem):
    class Meta:
        proxy = True


class CreditNoteLineItem(_CreditNoteLineItem):
    class Meta:
        proxy = True
