class MaterialEntry(models.Model):
    """Materials, e.g. sheets"""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )  # type: ignore
    job_pricing: ForeignKey = models.ForeignKey(
        "JobPricing", on_delete=CASCADE, related_name="material_entries"
    )
    description = models.CharField(max_length=200)  # type: ignore
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)  # type: ignore
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)  # type: ignore
    quantity = models.DecimalField(max_digits=10, decimal_places=2)  # type: ignore

    @property
    def cost(self) -> Decimal:
        return self.cost_price * self.quantity  # type: ignore

    @property
    def revenue(self) -> Decimal:
        return self.sale_price * self.quantity  # type: ignore
