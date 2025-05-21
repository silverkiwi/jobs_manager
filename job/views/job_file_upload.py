import os

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

# Use django.conf.settings to access the fully configured Django settings
# This ensures we get settings after all imports and env vars are processed
from django.conf import settings

# Atualizar imports se necessário
from job.models import Job, JobFile


class JobFileUploadView(APIView):
    def post(self, request):
        job_number = request.data.get("job_number")
        if not job_number:
            return Response(
                {"status": "error", "message": "Job number is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        files = request.FILES.getlist("files")
        if not files:
            return Response(
                {"status": "error", "message": "No files uploaded"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Define the Dropbox sync folder path
        job_folder = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, f"Job-{job_number}")
        os.makedirs(job_folder, exist_ok=True)

        os.chmod(job_folder, 0o2775)
 
        # Save each uploaded file
        for file in files:
            file_path = os.path.join(job_folder, file.name)
            with open(file_path, "wb") as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
                os.chmod(file_path, 0o664)

        return Response(
            {"status": "success", "message": "Files uploaded successfully"},
            status=status.HTTP_201_CREATED,
        )
