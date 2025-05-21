from rest_framework import serializers

from workflow.models import AdjustmentEntry


class AdjustmentEntrySerializer(serializers.ModelSerializer):
    revenue = serializers.SerializerMethodField(read_only=True)
    cost = serializers.SerializerMethodField(read_only=True)
    description = serializers.CharField(allow_blank=True, required=False)
    comments = serializers.CharField(allow_blank=True, required=False)

    class Meta:
        model = AdjustmentEntry
        fields = [
            "id",
            "description",
            "cost_adjustment",
            "price_adjustment",
            "comments",
            "revenue",
            "cost",
            "created_at",
            "updated_at",
        ]

    def get_revenue(self, obj):
        # Use price_adjustment for revenue
        return obj.price_adjustment

    def get_cost(self, obj):
        # Use cost_adjustment for cost
        return obj.cost_adjustment
