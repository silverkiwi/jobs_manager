import logging

from rest_framework.renderers import JSONRenderer, BaseRenderer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import os

from jobs_manager import settings

from django.http import FileResponse, JsonResponse
from django.conf import settings

from workflow.models import JobFile, Job

logger = logging.getLogger(__name__)


class BinaryFileRenderer(BaseRenderer):
    media_type = "*/*"
    format = "file"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class JobFileView(APIView):
    renderer_classes = [JSONRenderer, BinaryFileRenderer]

    def post(self, request):
        job_number = request.data.get("job_number")
        if not job_number:
            return Response(
                {"status": "error", "message": "Job number is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            job = Job.objects.get(job_number=job_number)
        except Job.DoesNotExist:
            return Response(
                {"status": "error", "message": "Job not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        files = request.FILES.getlist("files")
        if not files:
            return Response(
                {"status": "error", "message": "No files uploaded"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
                with open(file_path, "wb") as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)

                # Create database record
                relative_path = os.path.relpath(
                    file_path, settings.DROPBOX_WORKFLOW_FOLDER
                )

                job_file = JobFile.objects.create(
                    job=job,
                    filename=file.name,
                    file_path=relative_path,
                    mime_type=file.content_type,
                )
                uploaded_files.append(job_file.filename)
                logger.debug(f"Created JobFile record for {file.name}")

            except Exception as e:
                logger.exception(f"Error processing file {file.name}")
                errors.append(f"Error uploading {file.name}: {str(e)}")

        if errors:
            if uploaded_files:
                return Response(
                    {
                        "status": "partial_success",
                        "uploaded": uploaded_files,
                        "errors": errors,
                    },
                    status=status.HTTP_207_MULTI_STATUS,
                )
            return Response(
                {"status": "error", "message": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "status": "success",
                "uploaded": uploaded_files,
                "message": "Files uploaded successfully",
            },
            status=status.HTTP_201_CREATED,
        )

    def _get_by_number(self, job_number):
        """
        Return the file list of a job.
        """
        try:
            job = Job.objects.get(job_number=job_number)
        except Job.DoesNotExist:
            return Response(
                {"status": "error", "message": "Job not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        job_files = JobFile.objects.filter(job=job)
        if not job_files.exists():
            return Response([], status=status.HTTP_200_OK)

        return Response([
            {"filename": file.filename, "file_path": file.file_path}
            for file in job_files
        ], status=status.HTTP_200_OK)

    def _get_by_path(self, file_path):
        """
        Serve a specific file for download.
        """
        full_path = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, file_path)

        if not os.path.exists(full_path):
            return Response(
                {"status": "error", "message": "File not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            response = FileResponse(open(full_path, "rb"))

            import mimetypes
            content_type, _ = mimetypes.guess_type(full_path)
            if content_type:
                response["Content-Type"] = content_type

            response["Content-Disposition"] = f'inline; filename="{os.path.basename(file_path)}"'
            return response
        except Exception as e:
            logger.exception(f"Error serving file {file_path}")
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get(self, request, file_path=None, job_number=None):
        """
        Based on the request, serve a file for download or return the file list of the job. 
        """
        if job_number:
            return self._get_by_number(job_number)
        elif file_path:
            return self._get_by_path(file_path)
        else:
            return Response(
                {"status": "error", "message": "Invalid request, provide file_path or job_number"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
    def put(self, request):
        """
        Updates an existing file.
        """
        logger.debug("Processing PUT request to update file")
        
        job_number = request.data.get("job_number")
        if not job_number:
            logger.error("Job number not provided in request")
            return Response({
                "status": "error", 
                "message": "Job number is required"
            }, status=400)
        
        file_obj = request.FILES.get("files")
        if not file_obj:
            logger.error("No file provided in request")
            return JsonResponse({
                "status": "error",
                "message": "No file provided"
            }, status=400)
        
        try:
            job = Job.objects.get(job_number=job_number)
            logger.debug(f"Found job with number {job_number}")
        except Job.DoesNotExist:
            logger.error(f"Job not found with number {job_number}")
            return

        existing_files = JobFile.objects.filter(job=job, filename=file_obj.name)
        if existing_files.exists():
            job_file = existing_files.first()
            file_path = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, job_file.file_path)
            logger.debug(f"Found existing file at path: {file_path}")

            try:
                with open(file_path, "wb") as destination:
                    for chunk in file_obj.chunks():
                        destination.write(chunk)
                logger.info(f"Successfully updated file: {file_path}")

                return Response({
                    "status": "success",
                    "message": "File updated successfully"
                }, status=200)
            except Exception as e:
                logger.exception(f"Error updating file {file_path}: {str(e)}")
                return Response({
                    "status": "error",
                    "message": f"Error updating file: {str(e)}"
                }, status=500)
        else:
            logger.error(f"No existing file found for job {job_number} with name {file_obj.name}")
            return Response({
                "status": "error",
                "message": "File not found for update"
            }, status=404)
