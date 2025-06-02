import logging
import tempfile
import os

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .services.gemini_price_list_extraction import extract_data_from_supplier_price_list_gemini
from .models import SupplierPriceList

logger = logging.getLogger(__name__)

@login_required
def index(request):
    return render(request, 'quoting/index.html')

class UploadSupplierPricingView(LoginRequiredMixin, TemplateView):
    template_name = 'purchases/upload_supplier_pricing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Upload Supplier Pricing'
        # In a real scenario, you would fetch and add existing supplier pricing data here
        # For now, we'll just pass an empty list or dummy data
        context['uploaded_pricing'] = SupplierPriceList.objects.all().order_by('-uploaded_at')
        return context

    def post(self, request, *args, **kwargs):
        # This method will handle the PDF upload
        # For now, we'll just return a success message
        if 'pdf_file' in request.FILES:
            uploaded_file = request.FILES['pdf_file']
            logger.info(f"Received PDF upload: {uploaded_file.name}, size: {uploaded_file.size} bytes")

            # Save the file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            content_type = uploaded_file.content_type

            extracted_data, error = extract_data_from_supplier_price_list_gemini(temp_file_path, content_type)

            # Clean up the temporary file
            os.unlink(temp_file_path)

            if error:
                messages.error(request, f"Error extracting data from '{uploaded_file.name}': {error}")
            else:
                messages.success(request, f"File '{uploaded_file.name}' uploaded and data extracted successfully.")
                # You might want to store extracted_data in the database or session here
                logger.info(f"Extracted data: {extracted_data}")
        else:
            messages.error(request, "No PDF file was uploaded.")
        
        return self.get(request, *args, **kwargs) # Redirect back to the same page to show messages and updated list


class UploadPriceListView(LoginRequiredMixin, TemplateView):
    template_name = 'quoting/upload_price_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Upload Supplier Price List'
        return context


@require_http_methods(["POST"])
def extract_supplier_price_list_data_view(request):
    """
    Extract data from a supplier price list using Gemini.
    """
    try:
        if 'price_list_file' not in request.FILES:
            return JsonResponse({
                "success": False,
                "error": "No price list file uploaded."
            }, status=400)

        price_list_file = request.FILES['price_list_file']

        # Save the file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(price_list_file.name)[1]) as temp_file:
            for chunk in price_list_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        content_type = price_list_file.content_type

        extracted_data, error = extract_data_from_supplier_price_list_gemini(temp_file_path, content_type)

        # Clean up the temporary file
        os.unlink(temp_file_path)

        if error:
            return JsonResponse({
                "success": False,
                "error": f"Error extracting data from price list: {error}"
            }, status=400)

        return JsonResponse({
            "success": True,
            "extracted_data": extracted_data
        })

    except Exception as e:
        logger.exception(f"Error in extract_supplier_price_list_data_view: {e}")
        return JsonResponse({
            "success": False,
            "error": f"An unexpected error occurred: {str(e)}"
        }, status=500)


@require_http_methods(["POST"])
def extract_supplier_price_list_data_view(request):
    """
    Extract data from a supplier price list using Gemini.
    """
    try:
        if 'price_list_file' not in request.FILES:
            return JsonResponse({
                "success": False,
                "error": "No price list file uploaded."
            }, status=400)

        price_list_file = request.FILES['price_list_file']

        # Save the file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(price_list_file.name)[1]) as temp_file:
            for chunk in price_list_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        content_type = price_list_file.content_type

        extracted_data, error = extract_data_from_supplier_price_list_gemini(temp_file_path, content_type)

        # Clean up the temporary file
        os.unlink(temp_file_path)

        if error:
            return JsonResponse({
                "success": False,
                "error": f"Error extracting data from price list: {error}"
            }, status=400)

        return JsonResponse({
            "success": True,
            "extracted_data": extracted_data
        })

    except Exception as e:
        logger.exception(f"Error in extract_supplier_price_list_data_view: {e}")
        return JsonResponse({
            "success": False,
            "error": f"An unexpected error occurred: {str(e)}"
        }, status=500)
