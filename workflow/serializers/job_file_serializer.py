from rest_framework import serializers

from workflow.models import JobFile


class JobFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobFile
        fields = [
            "id",
            "filename",
            "file_path",
            "mime_type",
            "uploaded_at",
            "status",
            "print_on_jobsheet",
        ]
        read_only_fields = ["id", "filename", "file_path", "mime_type", "uploaded_at"]
