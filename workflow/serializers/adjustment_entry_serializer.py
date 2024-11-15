class AdjustmentEntrySerializer(serializers.ModelSerializer):
    total = serializers.DecimalField(source='price_adjustment', max_digits=10, decimal_places=2)

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





