from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError

from .job import Job


class CostSet(models.Model):
    """
    Representa um conjunto de custos para um job em uma revisão específica.
    Pode ser uma estimativa, cotação ou custo real.
    """
    
    KIND_CHOICES = [
        ('estimate', 'Estimate'),
        ('quote', 'Quote'),
        ('actual', 'Actual'),
    ]
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='cost_sets')
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    rev = models.IntegerField()
    summary = models.JSONField(default=dict, help_text="Summary data for this cost set")
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['job', 'kind', 'rev'],
                name='unique_job_kind_rev'
            )
        ]
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.job.name} - {self.get_kind_display()} Rev {self.rev}"
    
    def clean(self):
        if self.rev < 0:
            raise ValidationError("Revision must be non-negative")


class CostLine(models.Model):
    """
    Representa uma linha de custo dentro de um CostSet.
    Pode ser tempo, material ou ajuste.
    """
    
    KIND_CHOICES = [
        ('time', 'Time'),
        ('material', 'Material'),
        ('adjust', 'Adjustment'),
    ]
    
    cost_set = models.ForeignKey(CostSet, on_delete=models.CASCADE, related_name='cost_lines')
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    desc = models.CharField(max_length=255, help_text="Description of this cost line")
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('1.000'))
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    unit_rev = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    ext_refs = models.JSONField(default=dict, help_text="External references (e.g., time entry IDs, material IDs)")
    meta = models.JSONField(default=dict, help_text="Additional metadata")
    
    class Meta:
        indexes = [
            models.Index(fields=['cost_set_id', 'kind']),
        ]
        ordering = ['id']
    
    def __str__(self):
        return f"{self.cost_set} - {self.get_kind_display()}: {self.desc}"
    
    @property
    def total_cost(self):
        """Calcula o custo total (quantidade * custo unitário)"""
        return self.quantity * self.unit_cost
    
    @property
    def total_rev(self):
        """Calcula a receita total (quantidade * receita unitária)"""
        return self.quantity * self.unit_rev
    
    def clean(self):
        if self.quantity < 0:
            raise ValidationError("Quantity must be non-negative")
        if self.unit_cost < 0:
            raise ValidationError("Unit cost must be non-negative")
        if self.unit_rev < 0:
            raise ValidationError("Unit revenue must be non-negative")
