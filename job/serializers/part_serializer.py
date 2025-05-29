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
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Convert UUID id field to string for JSON serialization
        representation['id'] = str(representation['id'])
        
        return representation