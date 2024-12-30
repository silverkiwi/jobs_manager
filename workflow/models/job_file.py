import uuid

from django.db import models
from django.conf import settings
import os


class JobFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey("Job", related_name="files", on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)  # Original filename
    file_path = models.CharField(max_length=500)  # Relative path to Dropbox
    mime_type = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    @property
    def full_path(self):
        """Full system path to the file."""
        return os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, self.file_path)

    @property
    def url(self):
        """URL to serve the file (if using Django to serve media)."""
        return f"/jobs/files/{self.file_path}"  # We'll need to add this URL pattern

