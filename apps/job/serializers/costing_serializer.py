from rest_framework import serializers
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
