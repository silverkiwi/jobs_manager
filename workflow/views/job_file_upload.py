import os

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from jobs_manager import settings


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

        # Save each uploaded file
        for file in files:
            file_path = os.path.join(job_folder, file.name)
            with open(file_path, "wb") as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

        return Response(
            {"status": "success", "message": "Files uploaded successfully"},
            status=status.HTTP_201_CREATED,
        )
