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
        logger.debug(f"Initial data contains: {self.initial_data.keys()}")
        validated = super().validate(attrs)
        logger.debug(f"After super().validate, data is: {validated}")
        return validated

    def update(self, instance, validated_data):
        logger.debug(f"JobSerializer update called for instance {instance.id}")

        # Handle basic job fields first
        for attr, value in validated_data.items():
            if attr not in ['latest_estimate_pricing', 'latest_quote_pricing', 'latest_reality_pricing']:
                setattr(instance, attr, value)

        # Get pricing data from initial_data
        raw_data = self.initial_data

        # Handle each pricing type using their respective serializers
        pricing_types = {
            'latest_estimate': instance.latest_estimate_pricing,
            'latest_quote': instance.latest_quote_pricing,
            'latest_reality': instance.latest_reality_pricing
        }

        for pricing_type, pricing_instance in pricing_types.items():
            if pricing_type in raw_data:
                pricing_serializer = JobPricingSerializer(
                    instance=pricing_instance,
                    data=raw_data[pricing_type],
                    partial=True,
                    context=self.context
                )
                if pricing_serializer.is_valid():
                    pricing_serializer.save()
                else:
                    logger.error(f"Validation errors in {pricing_type}: {pricing_serializer.errors}")

        instance.save()
        return instance