from rest_framework import serializers

from workflow.models import AdjustmentEntry
from workflow.helpers import decimal_to_float

class AdjustmentEntrySerializer(serializers.ModelSerializer):
    revenue = serializers.SerializerMethodField(read_only=True)
    cost = serializers.SerializerMethodField(read_only=True)
    description = serializers.CharField(allow_blank=True)
    comments = serializers.CharField(allow_blank=True)

    class Meta:
        model = AdjustmentEntry
        fields = [
            'id',
            'description',
            'cost_adjustment',
            'price_adjustment',
            'comments',
            'revenue',  # Calculated as price_adjustment
            'cost',     # Calculated as cost_adjustment
        ]

    def get_revenue(self, obj):
        # Use price_adjustment for revenue
        return obj.price_adjustment

    def get_cost(self, obj):
        # Use cost_adjustment for cost
        return obj.cost_adjustment

