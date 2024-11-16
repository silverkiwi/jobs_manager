from rest_framework import serializers

from workflow.helpers import decimal_to_float
from workflow.models import MaterialEntry

class MaterialEntrySerializer(serializers.ModelSerializer):
    unit_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    total = serializers.SerializerMethodField()
    description = serializers.CharField(allow_blank=True)
    item_code = serializers.CharField(allow_blank=True)
    comments = serializers.CharField(allow_blank=True)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = MaterialEntry
        fields = [
            'id',
            'item_code',
            'description',
            'quantity',
            'unit_cost',
            'unit_revenue',
            'total',
            'comments',
        ]

    def get_total(self, obj):
        return decimal_to_float(obj.revenue)