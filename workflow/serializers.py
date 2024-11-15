import logging
from decimal import Decimal
import datetime
import uuid

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

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


class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Staff
        fields = "__all__"


class TimeEntrySerializer(serializers.ModelSerializer):
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


class MaterialEntrySerializer(serializers.ModelSerializer):
    cost_rate = serializers.DecimalField(source='unit_cost', max_digits=10, decimal_places=2)
    retail_rate = serializers.DecimalField(source='unit_revenue', max_digits=10, decimal_places=2)

    class Meta:
        model = MaterialEntry
        fields = [
            'id',
            'item_code',
            'description',
            'quantity',
            'cost_rate',
            'retail_rate',
            'total',
            'comments',
        ]


class AdjustmentEntrySerializer(serializers.ModelSerializer):
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


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = "__all__"


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

    def _process_pricing_entries(self, pricing_data, pricing_instance):
        """Process time, material, and adjustment entries for a pricing instance"""
        logger.debug(f"Processing pricing entries for instance {pricing_instance.id}")
        logger.debug(f"Received pricing data: {pricing_data}")

        if not pricing_data:
            logger.debug("No pricing data provided")
            return

        # Handle time entries
        if 'time' in pricing_data:
            logger.debug(f"Processing {len(pricing_data['time'])} time entries")
            pricing_instance.time_entries.all().delete()
            for entry in pricing_data['time']:
                logger.debug(f"Creating time entry: {entry}")
                TimeEntry.objects.create(
                    job_pricing=pricing_instance,
                    description=entry.get('description', ''),
                    items=entry.get('items', 0),
                    mins_per_item=entry.get('mins_per_item', 0),
                    wage_rate=entry.get('wage_rate', 0),
                    charge_out_rate=entry.get('charge_out_rate', 0),
                )

        # Handle material entries
        if 'materials' in pricing_data:
            logger.debug(f"Processing {len(pricing_data['materials'])} material entries")
            pricing_instance.material_entries.all().delete()
            for entry in pricing_data['materials']:
                logger.debug(f"Creating material entry: {entry}")
                MaterialEntry.objects.create(
                    job_pricing=pricing_instance,
                    item_code=entry.get('item_code', ''),
                    description=entry.get('description', ''),
                    quantity=entry.get('quantity', 0),
                    unit_cost=entry.get('cost_rate', 0),
                    unit_revenue=entry.get('retail_rate', 0),
                    comments=entry.get('comments', ''),
                )

        # Handle adjustment entries
        if 'adjustments' in pricing_data:
            logger.debug(f"Processing {len(pricing_data['adjustments'])} adjustment entries")
            pricing_instance.adjustment_entries.all().delete()
            for entry in pricing_data['adjustments']:
                logger.debug(f"Creating adjustment entry: {entry}")
                AdjustmentEntry.objects.create(
                    job_pricing=pricing_instance,
                    description=entry.get('description', ''),
                    cost_adjustment=entry.get('cost_adjustment', 0),
                    price_adjustment=entry.get('price_adjustment', 0),
                    comments=entry.get('comments', ''),
                )

        logger.debug(f"Finished processing entries for pricing instance {pricing_instance.id}")

    def update(self, instance, validated_data):
        logger.debug(f"JobSerializer update called for instance {instance.id}")
        logger.debug(f"Validated data received: {validated_data}")

        # Extract pricing data
        latest_estimate = validated_data.pop('latest_estimate', None)
        latest_quote = validated_data.pop('latest_quote', None)
        latest_reality = validated_data.pop('latest_reality', None)

        logger.debug(f"Extracted estimate data: {latest_estimate}")
        logger.debug(f"Extracted quote data: {latest_quote}")
        logger.debug(f"Extracted reality data: {latest_reality}")

        # Update the job instance with non-pricing data
        for attr, value in validated_data.items():
            logger.debug(f"Setting attribute {attr} = {value}")
            setattr(instance, attr, value)
        instance.save()

        # Process each pricing section
        if latest_estimate:
            logger.debug("Processing latest estimate pricing")
            self._process_pricing_entries(latest_estimate, instance.latest_estimate_pricing)
        if latest_quote:
            logger.debug("Processing latest quote pricing")
            self._process_pricing_entries(latest_quote, instance.latest_quote_pricing)
        if latest_reality:
            logger.debug("Processing latest reality pricing")
            self._process_pricing_entries(latest_reality, instance.latest_reality_pricing)

        logger.debug("Job update completed")
        return instance