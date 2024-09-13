import uuid
from decimal import Decimal

from django.db import models
from django.db.models import CASCADE


class MaterialEntry(models.Model):
    """Materials, e.g. sheets"""

    id: uuid.UUID = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )  # type: ignore
    job_pricing_type = models.ForeignKey(
        "JobPricingType",
        on_delete=CASCADE,
        related_name="material_entries",
    )  # type: ignore
    description: str = models.CharField(max_length=200)  # type: ignore
    cost_price: Decimal = models.DecimalField(
        max_digits=10, decimal_places=2
    )  # type: ignore
    sale_price: Decimal = models.DecimalField(
        max_digits=10, decimal_places=2
    )  # type: ignore
    quantity: Decimal = models.DecimalField(
        max_digits=10, decimal_places=2
    )  # type: ignore

    @property
    def cost(self) -> Decimal:
        return self.cost_price * self.quantity  # type: ignore

    @property
    def revenue(self) -> Decimal:
        return self.sale_price * self.quantity  # type: ignore
