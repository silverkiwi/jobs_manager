import logging

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from workflow.models import Job
from workflow.services.workshop_pdf_service import create_workshop_pdf

logger = logging.getLogger(__name__)


class WorkshopPDFView(APIView):
    def get(self, request, job_id):
        """Generate and return a workshop PDF for printing."""
        try:
            job = get_object_or_404(Job, pk=job_id)

            # Generate the workshop PDF
            pdf_buffer = create_workshop_pdf(job)

            # Return the PDF for printing
            response = FileResponse(
                pdf_buffer,
                as_attachment=False,
                filename=f"workshop_{job.job_number}.pdf",
                content_type="application/pdf",
            )

            # Add header to trigger print dialog
            response["Content-Disposition"] = (
                f'inline; filename="workshop_{job.job_number}.pdf"'
            )

            return response

        except Exception as e:
            logger.exception(f"Error generating workshop PDF for job {job_id}")
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
