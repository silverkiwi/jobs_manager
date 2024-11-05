# jobs_manager/workflow/serializers.py

from rest_framework import serializers

from workflow.models import JobPricing, MaterialEntry, AdjustmentEntry, TimeEntry, Client, Staff
from workflow.models.job import Job


class StaffSerializer:
    class Meta:
        model = Staff
        fields = '__all__'


class TimeSerializer(serializers.ModelSerializer):
    staff_id = serializers.PrimaryKeyRelatedField(
        queryset=Staff.objects.all(),
        source='staff',  # This will link `staff_id` to the `staff` field on the model
    )

    class Meta:
        model = TimeEntry
        fields = '__all__'

class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialEntry
        fields = '__all__'

class AdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdjustmentEntry
        fields = '__all__'



class JobPricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPricing
        fields = '__all__'

    def get_time_entries(self, obj):
        return TimeSerializer(obj.time_entries, many=True).data

    def get_material_entries(self, obj):
        return MaterialSerializer(obj.material_entries, many=True).data

    def get_adjustment_entries(self, obj):
        return AdjustmentSerializer(obj.adjustment_entries, many=True).data


class ClientSerializer:
    class Meta:
        model = Client
        fields = '__all__'


class JobSerializer(serializers.ModelSerializer):
    pricings = JobPricingSerializer(many=True)
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source='client',  # This will link `client_id` to the `client` field on the model
        write_only=True   # This is used for update operations
    )

    class Meta:
        model = Job
        fields = '__all__'  # Use '__all__' to include all fields or specify fields as needed
        extra_kwargs = {
            'name': {'required': False, 'allow_blank': True},
            'contact_person': {'required': False, 'allow_blank': True},
            'contact_phone': {'required': False, 'allow_blank': True},
            'description': {'required': False, 'allow_blank': True},
            'date_created': {'required': False}
        }

    def get_pricings(self, obj):
        # Use the decorator or reverse relationship to retrieve the associated job pricings
        return JobPricingSerializer(obj.pricings, many=True).data
