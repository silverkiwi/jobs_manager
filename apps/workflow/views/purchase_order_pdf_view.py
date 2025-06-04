import logging

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workflow.models.purchase import PurchaseOrder
from apps.workflow.services.purchase_order_pdf_service import create_purchase_order_pdf

logger = logging.getLogger(__name__)


class PurchaseOrderPDFView(APIView):
    """
    API view for generating and returning PDF documents for purchase orders.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, purchase_order_id):
        """
        Generate and return a PDF for the specified purchase order.
        
        Args:
            request: The HTTP request
            purchase_order_id: UUID of the purchase order
            
        Returns:
            FileResponse: PDF file if successful
            Response: Error details if unsuccessful
        """
        try:
            # Retrieve the purchase order
            purchase_order = get_object_or_404(PurchaseOrder, pk=purchase_order_id)
            
            # Generate the PDF using the service
            pdf_buffer = create_purchase_order_pdf(purchase_order)
            
            # Configure the response
            filename = f"PO_{purchase_order.po_number}.pdf"
            
            # Return as inline content or for download based on query parameter
            as_attachment = request.query_params.get('download', 'false').lower() == 'true'
            
            # Create the response with the PDF
            response = FileResponse(
                pdf_buffer,
                as_attachment=as_attachment,
                filename=filename,
                content_type="application/pdf",
            )
            
            # Add content disposition header
            disposition = f'{"attachment" if as_attachment else "inline"}; filename="{filename}"'
            response["Content-Disposition"] = disposition
            
            return response
            

        except Exception as e:
            logger.exception(f"Error generating PDF for purchase order {purchase_order_id}: {str(e)}")
            return Response(
                {
                    "status": "error", 
                    "message": "Could not generate PDF",
                    "details": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
