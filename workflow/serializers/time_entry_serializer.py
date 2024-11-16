from rest_framework import serializers
from workflow.models import TimeEntry
from workflow.helpers import decimal_to_float

class TimeEntrySerializer(serializers.ModelSerializer):
    total_minutes = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    description = serializers.CharField(allow_blank=True)

    class Meta:
        model = TimeEntry
        fields = [
            'id',
            'description',
            'items',
            'mins_per_item',
            'wage_rate',
            'charge_out_rate',
            'total_minutes',
            'total',
        ]

    def get_total_minutes(self, obj):
        return decimal_to_float(obj.minutes)

    def get_total(self, obj):
        return decimal_to_float(obj.revenue)