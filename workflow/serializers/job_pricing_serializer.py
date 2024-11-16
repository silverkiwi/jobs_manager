import uuid
import logging
from datetime import datetime
from decimal import Decimal

from rest_framework import serializers

from workflow.models import MaterialEntry, JobPricing

from workflow.serializers.time_entry_sterelizer import TimeEntrySerializer

from workflow.serializers.material_entry_serializer import MaterialEntrySerializer

from workflow.serializers.adjustment_entry_serializer import AdjustmentEntrySerializer

logger = logging.getLogger(__name__)


class JobPricingSerializer(serializers.ModelSerializer):
    time_entries = TimeEntrySerializer(many=True, required=False)
    material_entries = MaterialEntrySerializer(many=True, required=False)
    adjustment_entries = AdjustmentEntrySerializer(many=True, required=False)

    class Meta:
        model = JobPricing
        fields = [
            'id',
            'pricing_stage',
            'pricing_type',
            'revision_number',
            'created_at',
            'updated_at',
            'time_entries',
            'material_entries',
            'adjustment_entries',
        ]

    def to_representation(self, instance):
        logger.debug(f"JobPricingSerializer to_representation called for instance {instance.id}")
        representation = super().to_representation(instance)

        # Convert Decimal fields to float
        for key, value in representation.items():
            if isinstance(value, Decimal):
                representation[key] = float(value)
            elif isinstance(value, datetime.datetime):
                representation[key] = value.isoformat()
            elif isinstance(value, uuid.UUID):
                representation[key] = str(value)

        logger.debug(f"JobPricingSerializer representation result: {representation}")
        return representation

