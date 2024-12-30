import logging

from rest_framework.renderers import JSONRenderer, BaseRenderer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import os

from jobs_manager import settings

from django.http import FileResponse
from django.conf import settings

from workflow.models import JobFile, Job

logger = logging.getLogger(__name__)


class BinaryFileRenderer(BaseRenderer):
    media_type = '*/*'
    format = 'file'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class JobFileView(APIView):
    renderer_classes = [JSONRenderer, BinaryFileRenderer]

    def post(self, request):
        job_number = request.data.get('job_number')
        if not job_number:
            return Response({"status": "error", "message": "Job number is required"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            job = Job.objects.get(job_number=job_number)
        except Job.DoesNotExist:
            return Response({"status": "error", "message": "Job not found"},
                            status=status.HTTP_404_NOT_FOUND)

        files = request.FILES.getlist('files')
        if not files:
            return Response({"status": "error", "message": "No files uploaded"},
                            status=status.HTTP_400_BAD_REQUEST)

        uploaded_files = []
        errors = []

        # Define the Dropbox sync folder path
        job_folder = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, f"Job-{job_number}")
        os.makedirs(job_folder, exist_ok=True)

        for file in files:
            logger.debug(f"Processing file: {file.name}")
            file_path = os.path.join(job_folder, file.name)

            try:
                # Save file to filesystem
                with open(file_path, 'wb') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)

                # Create database record
                relative_path = os.path.relpath(
                    file_path,
                    settings.DROPBOX_WORKFLOW_FOLDER
                )

                job_file = JobFile.objects.create(
                    job=job,
                    filename=file.name,
                    file_path=relative_path,
                    mime_type=file.content_type
                )
                uploaded_files.append(job_file.filename)
                logger.debug(f"Created JobFile record for {file.name}")

            except Exception as e:
                logger.exception(f"Error processing file {file.name}")
                errors.append(f"Error uploading {file.name}: {str(e)}")

        if errors:
            if uploaded_files:
                return Response({
                    "status": "partial_success",
                    "uploaded": uploaded_files,
                    "errors": errors
                }, status=status.HTTP_207_MULTI_STATUS)
            return Response({
                "status": "error",
                "message": errors
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "status": "success",
            "uploaded": uploaded_files,
            "message": "Files uploaded successfully"
        }, status=status.HTTP_201_CREATED)


    def get(self, request, file_path=None):
        """Serve a job file."""
        if not file_path:
            return Response({"status": "error", "message": "File path is required"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Security: Validate file_path is within allowed folder
        full_path = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, file_path)
        if not os.path.exists(full_path):
            return Response({"status": "error", "message": "File not found"},
                            status=status.HTTP_404_NOT_FOUND)

        # Open and serve the file
        try:
            response = FileResponse(open(full_path, 'rb'))
            # Try to guess the content type
            import mimetypes
            content_type, _ = mimetypes.guess_type(full_path)
            if content_type:
                response['Content-Type'] = content_type
            # Set filename for download
            response[
                'Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
            return response
        except Exception as e:
            logger.exception(f"Error serving file {file_path}")
            return Response({"status": "error", "message": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)