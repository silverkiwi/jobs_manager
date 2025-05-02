import traceback

import logging

from django.views.generic import TemplateView

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from workflow.services.job_service import get_paid_complete_jobs

logger = logging.getLogger(__name__)


class ArchiveCompleteJobsViews:
    """
    Class that centralizes views related to archiving completed paid jobs.
    Contains both TemplateView for template rendering and APIViews for receiving and sending data.
    """

    class ArchiveCompleteJobsTemplateView(TemplateView):
        """View for renderizing the related page."""
        template_names = "jobs/archive_complete_jobs.html"

    class ArchiveCompleteJobsAPIView(APIView):
        """API Endpoint to provide Job data for archiving display"""
        def get(self, request, *args, **kwargs):
            try:
                jobs = get_paid_complete_jobs()

                if jobs.count() == 0:
                    return Response({
                        "success": True,
                        "jobs": []
                    }, status=status.HTTP_200_OK)
                
                return Response({
                    "success": True,
                    "jobs": 
                })
            except Exception as e:
                pass
