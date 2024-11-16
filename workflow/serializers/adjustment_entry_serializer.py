from rest_framework import serializers

from workflow.models import AdjustmentEntry


class AdjustmentEntrySerializer(serializers.ModelSerializer):
    total = serializers.DecimalField(source='price_adjustment', max_digits=10, decimal_places=2)
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
            'total',
        ]