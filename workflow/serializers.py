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
    total_minutes = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

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
        return obj.minutes

    def get_total(self, obj):
        return obj.revenue


class MaterialEntrySerializer(serializers.ModelSerializer):
    cost_rate = serializers.DecimalField(source='unit_cost', max_digits=10, decimal_places=2)
    retail_rate = serializers.DecimalField(source='unit_revenue', max_digits=10, decimal_places=2)
    total = serializers.SerializerMethodField()

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

    def get_total(self, obj):
        return obj.revenue


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

    def _process_pricing_data(self, pricing_data, pricing_instance):
        """Process pricing data for a specific pricing instance"""
        logger.debug(f"Processing pricing data for instance {pricing_instance.id}")
        logger.debug(f"Raw pricing data received: {pricing_data}")

        if not pricing_data:
            logger.debug("No pricing data provided")
            return

        # Process time entries
        time_entries = pricing_data.get('time', [])
        logger.debug(f"Processing {len(time_entries)} time entries")
        logger.debug(f"Time entries data: {time_entries}")
        existing_entries = list(pricing_instance.time_entries.all().values())
        logger.debug(f"Existing time entries before deletion: {existing_entries}")
        pricing_instance.time_entries.all().delete()
        logger.debug("Deleted existing time entries")
        for entry in time_entries:
            logger.debug(f"Creating time entry with data: {entry}")
            new_entry = TimeEntry.objects.create(
                job_pricing=pricing_instance,
                description=entry.get('description', ''),
                items=entry.get('items', 0),
                mins_per_item=entry.get('mins_per_item', 0),
                wage_rate=entry.get('wage_rate', 0),
                charge_out_rate=entry.get('charge_out_rate', 0),
            )
            logger.debug(f"Created new time entry: {new_entry.id}")

        # Process material entries
        material_entries = pricing_data.get('materials', [])
        logger.debug(f"Processing {len(material_entries)} material entries")
        pricing_instance.material_entries.all().delete()
        for entry in material_entries:
            MaterialEntry.objects.create(
                job_pricing=pricing_instance,
                item_code=entry.get('item_code', ''),
                description=entry.get('description', ''),
                quantity=entry.get('quantity', 0),
                unit_cost=entry.get('cost_rate', 0),
                unit_revenue=entry.get('retail_rate', 0),
                comments=entry.get('comments', ''),
            )

        # Process adjustment entries
        adjustment_entries = pricing_data.get('adjustments', [])
        logger.debug(f"Processing {len(adjustment_entries)} adjustment entries")
        pricing_instance.adjustment_entries.all().delete()
        for entry in adjustment_entries:
            AdjustmentEntry.objects.create(
                job_pricing=pricing_instance,
                description=entry.get('description', ''),
                cost_adjustment=entry.get('cost_adjustment', 0),
                price_adjustment=entry.get('price_adjustment', 0),
                comments=entry.get('comments', ''),
            )

    def update(self, instance, validated_data):
        logger.debug(f"JobSerializer update called for instance {instance.id}")
        logger.debug(f"Validated data received: {validated_data}")

        # Get pricing data from the initial_data instead of request
        raw_data = self.initial_data
        logger.debug(f"Initial data: {raw_data}")

        # Process each pricing section
        if 'latest_estimate' in raw_data:
            logger.debug("Processing latest estimate pricing")
            self._process_pricing_data(raw_data['latest_estimate'], instance.latest_estimate_pricing)
        else:
            logger.debug("No latest_estimate in raw_data")

        if 'latest_quote' in raw_data:
            logger.debug("Processing latest quote pricing")
            self._process_pricing_data(raw_data['latest_quote'], instance.latest_quote_pricing)
        else:
            logger.debug("No latest_quote in raw_data")

        if 'latest_reality' in raw_data:
            logger.debug("Processing latest reality pricing")
            self._process_pricing_data(raw_data['latest_reality'], instance.latest_reality_pricing)
        else:
            logger.debug("No latest_reality in raw_data")

        # Update the job instance with non-pricing data
        logger.debug("Updating job instance with non-pricing data")
        for attr, value in validated_data.items():
            logger.debug(f"Setting attribute {attr} = {value}")
            setattr(instance, attr, value)

        instance.save()
        logger.debug("Job update completed")
        return instance
