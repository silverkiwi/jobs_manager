import logging
from rest_framework import serializers

from workflow.models import Client, Job
from workflow.serializers.job_pricing_serializer import JobPricingSerializer

logger = logging.getLogger(__name__)


class JobSerializer(serializers.ModelSerializer):
    latest_estimate_pricing = JobPricingSerializer(required=False)
    latest_quote_pricing = JobPricingSerializer(required=False)
    latest_reality_pricing = JobPricingSerializer(required=False)
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source="client",
        write_only=True,
    )
    job_status = serializers.CharField(source='status')

    class Meta:
        model = Job
        fields = [
            "id",
            "name",
            "client_id",
            "contact_person",
            "contact_phone",
            "job_number",
            "order_number",
            "date_created",
            "material_gauge_quantity",
            "description",
            "latest_estimate_pricing",
            "latest_quote_pricing",
            "latest_reality_pricing",
            "job_status",
            "delivery_date",
            "paid",
            "quote_acceptance_date",
            "job_is_valid",
        ]

    def validate(self, attrs):
        logger.debug(f"JobSerializer validate called with attrs: {attrs}")
        # Validate nested pricing serializers
        nested_pricings = ['latest_estimate_pricing', 'latest_quote_pricing', 'latest_reality_pricing']
        for pricing_key in nested_pricings:
            pricing_data = attrs.get(pricing_key)
            if pricing_data:
                pricing_serializer = JobPricingSerializer(data=pricing_data, partial=True)
                if not pricing_serializer.is_valid():
                    logger.error(f"Validation errors in {pricing_key}: {pricing_serializer.errors}")
                    raise serializers.ValidationError({pricing_key: pricing_serializer.errors})

        validated = super().validate(attrs)
        logger.debug(f"After super().validate, data is: {validated}")
        return validated

    def update(self, instance, validated_data):
        logger.debug(f"JobSerializer update called for instance {instance.id}")
        logger.debug(f"Validated data received: {validated_data}")

        # Handle basic job fields first
        for attr, value in validated_data.items():
            if attr not in ['latest_estimate_pricing', 'latest_quote_pricing', 'latest_reality_pricing']:
                setattr(instance, attr, value)

        pricing_types = {
            'latest_estimate_pricing': instance.latest_estimate_pricing,
            'latest_quote_pricing': instance.latest_quote_pricing,
            'latest_reality_pricing': instance.latest_reality_pricing
        }

        for pricing_type, pricing_instance in pricing_types.items():
            pricing_data = validated_data.get(pricing_type)
            if pricing_data:
                logger.debug(f"Creating serializer for {pricing_type} with data: {pricing_data}")
                pricing_serializer = JobPricingSerializer(
                    instance=pricing_instance,
                    data=pricing_data,
                    partial=True,
                    context=self.context
                )

                # Temporary validation check for debugging
                if pricing_serializer.is_valid():
                    logger.debug(f"{pricing_type} serializer is valid")
                    pricing_serializer.save()
                else:
                    logger.error(f"{pricing_type} serializer validation failed: {pricing_serializer.errors}")
                    raise serializers.ValidationError({pricing_type: pricing_serializer.errors})

        instance.save()
        return instance