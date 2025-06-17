from rest_framework import serializers
from decimal import Decimal
from apps.job.models import CostSet, CostLine


class CostLineSerializer(serializers.ModelSerializer):
    """
    Serializer for CostLine model - read-only with basic depth
    """
    total_cost = serializers.ReadOnlyField()
    total_rev = serializers.ReadOnlyField()
    
    class Meta:
        model = CostLine
        fields = [
            'id', 'kind', 'desc', 'quantity', 'unit_cost', 'unit_rev',
            'total_cost', 'total_rev', 'ext_refs', 'meta'
        ]
        read_only_fields = fields


class TimesheetCostLineSerializer(serializers.ModelSerializer):
    """
    Serializer for CostLine model specifically for timesheet entries
    
    Architecture principle: Job data comes from CostSet->Job relationship, 
    NOT from metadata. This ensures data consistency and follows SRP:
    - Metadata = timesheet-specific data (staff, date, billable, etc.)
    - Relationship = job data (job_id, job_number, job_name, client)
    
    Benefits:
    - No data duplication
    - Always consistent with source Job
    - Simplified queries and maintenance
    """
    total_cost = serializers.ReadOnlyField()
    total_rev = serializers.ReadOnlyField()
    
    # Job information from CostSet relationship (NOT from metadata)
    job_id = serializers.CharField(source='cost_set.job.id', read_only=True)
    job_number = serializers.CharField(source='cost_set.job.job_number', read_only=True)
    job_name = serializers.CharField(source='cost_set.job.name', read_only=True)
    charge_out_rate = serializers.DecimalField(source='cost_set.job.charge_out_rate', max_digits=10, decimal_places=2, read_only=True)
    
    # Client name with null handling
    client_name = serializers.SerializerMethodField()
    
    def get_client_name(self, obj):
        """Get client name with safe null handling"""
        if obj.cost_set and obj.cost_set.job and obj.cost_set.job.client:
            return obj.cost_set.job.client.name
        return ''
    
    class Meta:
        model = CostLine
        fields = [
            'id', 'kind', 'desc', 'quantity', 'unit_cost', 'unit_rev',
            'total_cost', 'total_rev', 'ext_refs', 'meta',
            'job_id', 'job_number', 'job_name', 'client_name', 'charge_out_rate'
        ]
        read_only_fields = fields


class CostLineCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for CostLine creation and updates - full write capabilities
    """
    class Meta:
        model = CostLine
        fields = [
            'kind', 'desc', 'quantity', 'unit_cost', 'unit_rev',
            'ext_refs', 'meta'
        ]
    
    def validate_quantity(self, value):
        """Validate quantity is non-negative"""
        if value < 0:
            raise serializers.ValidationError("Quantity must be non-negative")
        return value
    
    def validate_unit_cost(self, value):
        """Validate unit cost is non-negative"""
        if value < 0:
            raise serializers.ValidationError("Unit cost must be non-negative")
        return value
    
    def validate_unit_rev(self, value):
        """Validate unit revenue is non-negative"""
        if value < 0:
            raise serializers.ValidationError("Unit revenue must be non-negative")
        return value


class CostSetSerializer(serializers.ModelSerializer):
    """
    Serializer for CostSet model - includes nested cost lines
    """
    cost_lines = CostLineSerializer(many=True, read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Garante que summary sempre tem os campos obrigatórios
        summary = data.get('summary') or {}
        data['summary'] = {
            'cost': summary.get('cost', 0),
            'rev': summary.get('rev', 0),
            'hours': summary.get('hours', 0)
        }
        return data
    
    class Meta:
        model = CostSet
        fields = [
            'id', 'kind', 'rev', 'summary', 'created', 'cost_lines'
        ]
        read_only_fields = fields
