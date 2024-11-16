import uuid
import logging
import datetime
from decimal import Decimal

from rest_framework import serializers

from workflow.models import JobPricing
from workflow.serializers.time_entry_serializer import TimeEntrySerializer
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

    def to_internal_value(self, data):
        logger.debug(f"JobPricingSerializer to_internal_value called with data: {data}")
        # Extract the nested entries data before validation
        time_data = data.get('time', [])
        material_data = data.get('materials', [])
        adjustment_data = data.get('adjustments', [])

        # Restructure data to match serializer fields
        restructured_data = {
            'time_entries': time_data,
            'material_entries': material_data,
            'adjustment_entries': adjustment_data,
        }

        logger.debug(f"Restructured data for internal value: {restructured_data}")
        internal_value = super().to_internal_value(restructured_data)
        logger.debug(f"JobPricingSerializer to_internal_value result: {internal_value}")
        return internal_value

    def validate(self, attrs):
        logger.debug(f"JobPricingSerializer validate called with attrs: {attrs}")
        validated_data = super().validate(attrs)
        logger.debug(f"JobPricingSerializer validate result: {validated_data}")
        return validated_data

    def update(self, instance, validated_data):
        logger.debug(f"JobPricingSerializer update called for instance {instance.id}")
        logger.debug(f"Update validated_data: {validated_data}")

        # Handle nested time entries using the serializer
        if 'time_entries' in validated_data:
            logger.debug("Processing time entries")
            instance.time_entries.all().delete()
            time_serializer = TimeEntrySerializer(data=validated_data['time_entries'], many=True)
            if time_serializer.is_valid():
                time_serializer.save(job_pricing=instance)
            else:
                logger.error(f"Time entry validation errors: {time_serializer.errors}")

        # Handle nested material entries using the serializer
        if 'material_entries' in validated_data:
            logger.debug("Processing material entries")
            instance.material_entries.all().delete()
            material_serializer = MaterialEntrySerializer(data=validated_data['material_entries'], many=True)
            if material_serializer.is_valid():
                material_serializer.save(job_pricing=instance)
            else:
                logger.error(f"Material entry validation errors: {material_serializer.errors}")

        # Handle nested adjustment entries using the serializer
        if 'adjustment_entries' in validated_data:
            logger.debug("Processing adjustment entries")
            instance.adjustment_entries.all().delete()
            adjustment_serializer = AdjustmentEntrySerializer(data=validated_data['adjustment_entries'], many=True)
            if adjustment_serializer.is_valid():
                adjustment_serializer.save(job_pricing=instance)
            else:
                logger.error(f"Adjustment entry validation errors: {adjustment_serializer.errors}")

        # Update the remaining fields
        for attr, value in validated_data.items():
            if attr not in ['time_entries', 'material_entries', 'adjustment_entries']:
                setattr(instance, attr, value)

        instance.save()
        logger.debug("JobPricing update completed")
        return instance