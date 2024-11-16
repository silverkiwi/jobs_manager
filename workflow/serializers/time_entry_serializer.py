from rest_framework import serializers
from workflow.models import TimeEntry
from workflow.helpers import decimal_to_float

class TimeEntrySerializer(serializers.ModelSerializer):
    total_minutes = serializers.SerializerMethodField()
    revenue = serializers.SerializerMethodField()
    cost = serializers.SerializerMethodField()
    description = serializers.CharField(allow_blank=True)


    class Meta:
        model = TimeEntry  # Assuming the model is named `TimeEntry`
        fields = [
            'id',
            'description',
            'items',
            'mins_per_item',
            'wage_rate',
            'charge_out_rate',
            'total_minutes',  # Expose total as a calculated read-only field
            'revenue',  # Expose revenue as a calculated read-only field
            'cost',
        ]

    def get_total_minutes(self, obj):
        return decimal_to_float(obj.minutes)

    def get_revenue(self, obj):
        return obj.revenue  # Uses the @property defined in the model

    def get_cost(self, obj):
        return obj.cost  # Uses the @property defined in the model
