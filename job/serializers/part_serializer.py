from rest_framework import serializers
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