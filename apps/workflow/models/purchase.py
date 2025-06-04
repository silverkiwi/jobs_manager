"""
Proxy models for Purchase-related entities that have been moved to the purchasing app.
These proxy models maintain backward compatibility for existing code that imports from workflow.
"""

from apps.purchasing.models import (
    PurchaseOrder as _PurchaseOrder,
    PurchaseOrderLine as _PurchaseOrderLine,
    PurchaseOrderSupplierQuote as _PurchaseOrderSupplierQuote,
)


class PurchaseOrder(_PurchaseOrder):
    """Proxy model for PurchaseOrder - redirects to purchasing app."""
    
    class Meta:
        proxy = True
        app_label = 'workflow'


class PurchaseOrderLine(_PurchaseOrderLine):
    """Proxy model for PurchaseOrderLine - redirects to purchasing app."""
    
    class Meta:
        proxy = True
        app_label = 'workflow'


class PurchaseOrderSupplierQuote(_PurchaseOrderSupplierQuote):
    """Proxy model for PurchaseOrderSupplierQuote - redirects to purchasing app."""
    
    class Meta:
        proxy = True
        app_label = 'workflow'
