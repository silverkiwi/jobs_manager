import logging
import os
import tempfile

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from apps.client.models import Client

from .models import ProductParsingMapping, SupplierPriceList, SupplierProduct
from .services.ai_price_extraction import extract_price_data
from .services.product_parser import (
    ProductParser,
    create_mapping_record,
    populate_all_mappings_with_llm,
)

logger = logging.getLogger(__name__)


@login_required
def index(request):
    return render(request, "quoting/index.html")


class UploadSupplierPricingView(LoginRequiredMixin, TemplateView):
    template_name = "purchasing/upload_supplier_pricing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Upload Supplier Pricing"
        # In a real scenario, you would fetch and add existing supplier pricing data here
        # For now, we'll just pass an empty list or dummy data
        context["uploaded_pricing"] = SupplierPriceList.objects.all().order_by(
            "-uploaded_at"
        )
        return context

    def post(self, request, *args, **kwargs):
        # This method will handle the PDF upload
        # For now, we'll just return a success message
        if "pdf_file" in request.FILES:
            uploaded_file = request.FILES["pdf_file"]
            logger.info(
                f"Received PDF upload: {uploaded_file.name}, size: {uploaded_file.size} bytes"
            )

            # Save the file temporarily
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=os.path.splitext(uploaded_file.name)[1]
            ) as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            content_type = uploaded_file.content_type

            extracted_data, error = extract_price_data(temp_file_path, content_type)

            # Clean up the temporary file
            os.unlink(temp_file_path)

            if error:
                messages.error(
                    request,
                    f"Error extracting data from '{uploaded_file.name}': {error}",
                )
            else:
                # Save extracted data to database - ALL OR NOTHING
                from django.db import transaction

                supplier_name = extracted_data.get("supplier", {}).get(
                    "name", "Unknown Supplier"
                )
                items_data = extracted_data.get("items", [])

                logger.info(
                    f"Starting atomic insertion for supplier '{supplier_name}' with {len(items_data)} items"
                )

                try:
                    with transaction.atomic():
                        # Get existing supplier/client - do not create
                        try:
                            supplier = Client.objects.get(name=supplier_name)
                            logger.info(
                                f"Found supplier: {supplier.name} (ID: {supplier.id})"
                            )
                        except Client.DoesNotExist:
                            messages.error(
                                request,
                                f"Supplier '{supplier_name}' not found in system. Please create the supplier first.",
                            )
                            return self.get(request, *args, **kwargs)

                        # Create price list entry
                        price_list = SupplierPriceList.objects.create(
                            supplier=supplier, file_name=uploaded_file.name
                        )
                        logger.info(
                            f"Created SupplierPriceList record: {price_list.id} for supplier {supplier.name}"
                        )

                        # Validate and save ALL products - fail on ANY error
                        items_saved = 0
                        logger.info(
                            f"Processing {len(items_data)} items for database insertion"
                        )

                        for idx, item in enumerate(items_data):
                            # Detailed logging for each item
                            logger.debug(
                                f"Processing item {idx}: {item.get('description', '')[:50]}..."
                            )

                            # Validate required fields
                            if not item.get("description"):
                                raise ValueError(
                                    f"Item {idx}: Missing required field 'description'"
                                )

                            if not item.get("variant_id"):
                                raise ValueError(
                                    f"Item {idx}: Missing required field 'variant_id' for '{item.get('description', '')[:50]}'"
                                )

                            # Parse and validate price
                            variant_price = None
                            if item.get("unit_price") is not None:
                                try:
                                    variant_price = float(
                                        str(item["unit_price"]).replace("$", "").strip()
                                    )
                                    if variant_price < 0:
                                        raise ValueError(
                                            f"Negative price: {variant_price}"
                                        )
                                except (ValueError, TypeError) as e:
                                    raise ValueError(
                                        f"Item {idx}: Invalid price '{item.get('unit_price')}' - {e}"
                                    )
                            else:
                                logger.warning(
                                    f"Item {idx}: No price for '{item.get('description', '')[:50]}'"
                                )

                            # Create product - let any database errors propagate
                            product = SupplierProduct.objects.create(
                                supplier=supplier,
                                price_list=price_list,
                                product_name=item.get(
                                    "product_name", item.get("description", "")
                                )[:500],
                                item_no=item.get("supplier_item_code", "")[:100],
                                description=item.get("description", ""),
                                specifications=item.get("specifications", ""),
                                variant_id=item.get("variant_id", "")[:100],
                                variant_price=variant_price,
                                url="",  # PDF uploads don't have URLs
                            )

                            # Create mapping record (LLM called at end of batch)
                            create_mapping_record(product)

                            items_saved += 1

                            if items_saved % 50 == 0:
                                logger.info(
                                    f"Progress: {items_saved}/{len(items_data)} items saved"
                                )

                        # Verify insertion
                        final_count = SupplierProduct.objects.filter(
                            price_list=price_list
                        ).count()
                        if final_count != len(items_data):
                            raise ValueError(
                                f"Insertion verification failed: expected {len(items_data)} items, "
                                f"but found {final_count} in database"
                            )

                        # Log parsing statistics if available
                        if "parsing_stats" in extracted_data:
                            stats = extracted_data["parsing_stats"]
                            logger.info(
                                f"Parsing stats - Total lines: {stats.get('total_lines', 0)}, "
                                f"Items found: {stats.get('items_found', 0)}, "
                                f"Pages processed: {stats.get('pages_processed', 0)}"
                            )

                        # Batch process all new mappings with LLM
                        populate_all_mappings_with_llm()

                        # Success - transaction will commit
                        messages.success(
                            request,
                            f"File '{uploaded_file.name}' processed successfully. "
                            f"Saved ALL {items_saved} products from {supplier_name}.",
                        )
                        logger.info(
                            f"Successfully saved ALL {items_saved} products from PDF: {uploaded_file.name} to price list {price_list.id}"
                        )

                except Exception as db_error:
                    # Transaction rolled back automatically
                    logger.exception(
                        f"Failed to save products - transaction rolled back: {db_error}"
                    )
                    messages.error(
                        request,
                        f"Failed to save products: {db_error}. No data was saved.",
                    )
        else:
            messages.error(request, "No PDF file was uploaded.")

        return self.get(
            request, *args, **kwargs
        )  # Redirect back to the same page to show messages and updated list


class UploadPriceListView(LoginRequiredMixin, TemplateView):
    template_name = "quoting/upload_price_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Upload Supplier Price List"
        return context


@require_http_methods(["POST"])
def extract_supplier_price_list_data_view(request):
    """
    Extract data from a supplier price list using Gemini.
    """
    try:
        if "price_list_file" not in request.FILES:
            return JsonResponse(
                {"success": False, "error": "No price list file uploaded."}, status=400
            )

        price_list_file = request.FILES["price_list_file"]

        # Save the file temporarily
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(price_list_file.name)[1]
        ) as temp_file:
            for chunk in price_list_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        content_type = price_list_file.content_type

        extracted_data, error = extract_price_data(temp_file_path, content_type)

        # Clean up the temporary file
        os.unlink(temp_file_path)

        if error:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Error extracting data from price list: {error}",
                },
                status=400,
            )

        return JsonResponse({"success": True, "extracted_data": extracted_data})

    except Exception as e:
        logger.exception(f"Error in extract_supplier_price_list_data_view: {e}")
        return JsonResponse(
            {"success": False, "error": f"An unexpected error occurred: {str(e)}"},
            status=500,
        )


@require_http_methods(["POST"])
def extract_supplier_price_list_data_view(request):
    """
    Extract data from a supplier price list using Gemini.
    """
    try:
        if "price_list_file" not in request.FILES:
            return JsonResponse(
                {"success": False, "error": "No price list file uploaded."}, status=400
            )

        price_list_file = request.FILES["price_list_file"]

        # Save the file temporarily
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(price_list_file.name)[1]
        ) as temp_file:
            for chunk in price_list_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        content_type = price_list_file.content_type

        extracted_data, error = extract_price_data(temp_file_path, content_type)

        # Clean up the temporary file
        os.unlink(temp_file_path)

        if error:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Error extracting data from price list: {error}",
                },
                status=400,
            )

        return JsonResponse({"success": True, "extracted_data": extracted_data})

    except Exception as e:
        logger.exception(f"Error in extract_supplier_price_list_data_view: {e}")
        return JsonResponse(
            {"success": False, "error": f"An unexpected error occurred: {str(e)}"},
            status=500,
        )
