from rest_framework import serializers
from uuid import UUID
from job.models import Part


class PartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Part
        fields = [
            "id",
            "name",
            "description",
            "job_pricing",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Convert UUID fields to strings for JSON serialization
        for field_name, value in representation.items():
            if isinstance(value, UUID):
                representation[field_name] = str(value)
        
        return representation