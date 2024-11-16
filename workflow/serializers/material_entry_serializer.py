from rest_framework import serializers

from workflow.helpers import decimal_to_float
from workflow.models import MaterialEntry

class MaterialEntrySerializer(serializers.ModelSerializer):
    cost_rate = serializers.DecimalField(source='unit_cost', max_digits=10, decimal_places=2)
    retail_rate = serializers.DecimalField(source='unit_revenue', max_digits=10, decimal_places=2)
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
            'cost_rate',
            'retail_rate',
            'total',
            'comments',
        ]

    def get_total(self, obj):
        return decimal_to_float(obj.revenue)