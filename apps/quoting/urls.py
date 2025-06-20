from django.urls import path

from . import views

urlpatterns = [
    path(
        "upload-supplier-pricing/",
        views.UploadSupplierPricingView.as_view(),
        name="upload_supplier_pricing",
    ),
    path(
        "api/extract-supplier-price-list/",
        views.extract_supplier_price_list_data_view,
        name="extract_supplier_price_list_data",
    ),
    path(
        "upload-price-list/",
        views.UploadPriceListView.as_view(),
        name="upload_price_list",
    ),
]
