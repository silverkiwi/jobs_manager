import logging
import os

from django.http import FileResponse, JsonResponse
from rest_framework import status
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

# Use django.conf.settings to access the fully configured Django settings
# This ensures we get settings after all imports and env vars are processed
from django.conf import settings

from workflow.models import Job, JobFile

logger = logging.getLogger(__name__)


class BinaryFileRenderer(BaseRenderer):
    media_type = "*/*"
    format = "file"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class JobFileView(APIView):
    renderer_classes = [JSONRenderer, BinaryFileRenderer]

    def save_file(self, job, file_obj, print_on_jobsheet):
        """
        Save file to disk and create or update JobFile record.
        """
        job_folder = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, f"Job-{job.job_number}")
        os.makedirs(job_folder, exist_ok=True)

        file_path = os.path.join(job_folder, file_obj.name)
        logger.debug(f"Saving file to {file_path}")

        try:
            with open(file_path, "wb") as destination:
                for chunk in file_obj.chunks():
                    destination.write(chunk)

            relative_path = os.path.relpath(file_path, settings.DROPBOX_WORKFLOW_FOLDER)

            job_file, created = JobFile.objects.update_or_create(
                job=job,
                filename=file_obj.name,
                defaults={
                    "file_path": relative_path,
                    "mime_type": file_obj.content_type,
                    "print_on_jobsheet": print_on_jobsheet
                }
            )

            logger.info(f"{'Created' if created else 'Updated'} JobFile: {job_file.filename}")
            return {
                "id": str(job_file.id),
                "filename": job_file.filename,
                "file_path": job_file.file_path,
                "print_on_jobsheet": job_file.print_on_jobsheet
            }
        except Exception as e:
            logger.exception(f"Error processing file {file_obj.name}: {str(e)}")
            return {"error": f"Error uploading {file_obj.name}: {str(e)}"}

    def post(self, request):
        """
        Handle file uploads. Creates new files or updates existing ones.
        """
        logger.debug("Processing POST request to upload files")

        job_number = request.data.get("job_number")
        if not job_number:
            return Response({"status": "error", "message": "Job number is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            job = Job.objects.get(job_number=job_number)
        except Job.DoesNotExist:
            return Response({"status": "error", "message": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        files = request.FILES.getlist("files")
        if not files:
            return Response({"status": "error", "message": "No files uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        print_on_jobsheet = request.data.get("print_on_jobsheet") in ["true", "True", "1"]

        uploaded_files = []
        errors = []

        for file_obj in files:
            result = self.save_file(job, file_obj, print_on_jobsheet)
            if "error" in result:
                errors.append(result["error"])
            else:
                uploaded_files.append(result)

        if errors:
            return Response({
                "status": "partial_success" if uploaded_files else "error",
                "uploaded": uploaded_files,
                "errors": errors
            }, status=status.HTTP_207_MULTI_STATUS if uploaded_files else status.HTTP_400_BAD_REQUEST)

        return Response({
            "status": "success",
            "uploaded": uploaded_files,
            "message": "Files uploaded successfully"
        }, status=status.HTTP_201_CREATED)

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

        return Response(
            [
                {"filename": file.filename, "file_path": file.file_path, "id": file.id}
                for file in job_files
            ],
            status=status.HTTP_200_OK,
        )

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

            response["Content-Disposition"] = (
                f'inline; filename="{os.path.basename(file_path)}"'
            )
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
                {
                    "status": "error",
                    "message": "Invalid request, provide file_path or job_number",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def put(self, request):
        """
        Update an existing job file, replacing the file and updating `print_on_jobsheet`.
        """
        logger.debug("Processing PUT request to update file")

        job_number = request.data.get("job_number")
        file_obj = request.FILES.get("files")
        print_on_jobsheet = str(request.data.get("print_on_jobsheet")) in ["true", "True", "1"]

        logger.info(f"Received PUT request - job_number: {job_number}, filename: {file_obj.name if file_obj else None}, print_on_jobsheet: {print_on_jobsheet}")

        if not job_number:
            logger.error("Job number not provided in request")
            return Response(
                {"status": "error", "message": "Job number is required"}, status=400
            )

        file_obj = request.FILES.get("files")
        if not file_obj:
            logger.error("No file provided in request")
            return JsonResponse(
                {"status": "error", "message": "No file provided"}, status=400
            )

        try:
            job = Job.objects.get(job_number=job_number)
            logger.info(f"Found job with number {job_number}")
        except Job.DoesNotExist:
            return Response({"status": "error", "message": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        job_file = JobFile.objects.filter(job=job, filename=file_obj.name).first()
        if not job_file:
            return Response({"status": "error", "message": "File not found for update"}, status=status.HTTP_404_NOT_FOUND)

        logger.info(f"Found existing job file: {job_file.filename} with current print_on_jobsheet={job_file.print_on_jobsheet}")
        
        file_path = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, job_file.file_path)
        try:
            with open(file_path, "wb") as destination:
                for chunk in file_obj.chunks():
                    destination.write(chunk)

            old_print_value = job_file.print_on_jobsheet
            job_file.print_on_jobsheet = print_on_jobsheet
            job_file.save()

            logger.info(f"Successfully updated file: {file_path}")
            logger.info(f"Updated print_on_jobsheet from {old_print_value} to {print_on_jobsheet}")
            
            return Response({
                "status": "success",
                "message": "File updated successfully",
                "print_on_jobsheet": job_file.print_on_jobsheet
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Error updating file {file_path}: {str(e)}")
            return Response({"status": "error", "message": f"Error updating file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, file_path=None):
        """Delete a job file."""
        try:
            # Get the JobFile by ID
            job_file = JobFile.objects.get(id=file_path)

            # Delete the physical file
            full_path = os.path.join(
                settings.DROPBOX_WORKFLOW_FOLDER, job_file.file_path
            )
            if os.path.exists(full_path):
                os.remove(full_path)

            # Delete the database record
            job_file.delete()

            return Response(status=status.HTTP_204_NO_CONTENT)
        except JobFile.DoesNotExist:
            return Response(
                {"status": "error", "message": "File not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.exception(f"Error deleting file {file_path}")
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
