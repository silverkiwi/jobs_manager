# jobs_manager/workflow/serializers.py
import logging

from rest_framework import serializers

from workflow.models import (
    JobPricing,
    MaterialEntry,
    AdjustmentEntry,
    TimeEntry,
    Client,
    Staff,
)
from workflow.models.job import Job

logger = logging.getLogger(__name__)

class StaffSerializer:
    class Meta:
        model = Staff
        fields = "__all__"


class TimeSerializer(serializers.ModelSerializer):
    staff_id = serializers.PrimaryKeyRelatedField(
        queryset=Staff.objects.all(),
        source="staff",  # This will link `staff_id` to the `staff` field on the model
    )

    class Meta:
        model = TimeEntry
        fields = "__all__"


class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialEntry
        fields = "__all__"


class AdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdjustmentEntry
        fields = "__all__"


class JobPricingSerializer(serializers.ModelSerializer):
    time_entries = serializers.SerializerMethodField()
    material_entries = serializers.SerializerMethodField()
    adjustment_entries = serializers.SerializerMethodField()

    class Meta:
        model = JobPricing
        fields = "__all__"

    def get_time_entries(self, obj):
        return TimeSerializer(obj.time_entries.all(), many=True).data

    def get_material_entries(self, obj):
        return MaterialSerializer(obj.material_entries.all(), many=True).data

    def get_adjustment_entries(self, obj):
        return AdjustmentSerializer(obj.adjustment_entries.all(), many=True).data


class ClientSerializer:
    class Meta:
        model = Client
        fields = "__all__"


class JobSerializer(serializers.ModelSerializer):

    # Handle multiple nested job pricings
    historical_pricings = JobPricingSerializer(many=True, required=False)

    # Handle latest pricings as individual fields for each pricing stage
    latest_estimate_pricing = JobPricingSerializer(required=False)
    latest_quote_pricing = JobPricingSerializer(required=False)
    latest_reality_pricing = JobPricingSerializer(required=False)

    # Related client field using client_id
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source="client",
        write_only=True,  # Only required for updates; hides from read responses
    )

    class Meta:
        model = Job
        fields = [
            "id",  # Primary key (maps to job_id in HTML)
            "name",
            "client_id",  # This is used to set the client
            "contact_person",
            "contact_phone",
            "job_number",
            "order_number",
            "date_created",
            "material_gauge_quantity",
            "description",
            "historical_pricings",  # All historical pricings
            "latest_estimate_pricing",  # Latest pricing per stage
            "latest_quote_pricing",
            "latest_reality_pricing",
        ]

    def update(self, instance, validated_data):
        # Step 1: Handle updating latest pricings
        latest_fields = ["latest_estimate_pricing", "latest_quote_pricing", "latest_reality_pricing"]

        for field in latest_fields:
            latest_data = validated_data.pop(field, None)
            if latest_data:
                related_instance = getattr(instance, field, None)
                if related_instance:
                    for attr, value in latest_data.items():
                        setattr(related_instance, attr, value)
                    related_instance.save()

        # Step 2: Handle updating historical pricings if provided
        pricings_data = validated_data.pop("historical_pricings", None)
        logger.debug(f"Payload historical_pricings: {pricings_data}")
        if pricings_data:
            for pricing_data in pricings_data:
                # Use pricing ID to identify historical entries to update
                pricing_id = pricing_data.get("id")
                if pricing_id:
                    historical_instance = JobPricing.objects.get(pk=pricing_id)
                    for attr, value in pricing_data.items():
                        setattr(historical_instance, attr, value)
                    historical_instance.save()

        # Step 3: Update the rest of the job fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

