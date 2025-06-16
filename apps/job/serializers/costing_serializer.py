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
    
    class Meta:
        model = CostSet
        fields = [
            'id', 'kind', 'rev', 'summary', 'created', 'cost_lines'
        ]
        read_only_fields = fields
