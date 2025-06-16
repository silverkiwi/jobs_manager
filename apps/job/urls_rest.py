"""
URLs REST para o módulo Job

Novas rotas REST seguindo padrões modernos para integração com frontend Vue.js
"""

from django.urls import path

from apps.job.views.job_rest_views import (
    JobCreateRestView,
    JobDetailRestView,
    JobToggleComplexRestView,
    JobTogglePricingMethodologyRestView,
    JobEventRestView,
    JobTimeEntryRestView,
    JobMaterialEntryRestView,
    JobAdjustmentEntryRestView,
)

from apps.job.views.job_costing_views import JobCostSetView

from apps.job.views.workshop_view import WorkshopPDFView

from apps.job.views.job_file_upload import JobFileUploadView
from apps.job.views.job_file_view import JobFileView, JobFileThumbnailView

from apps.job.views.quote_import_views import (
    QuoteImportPreviewView,
    QuoteImportView,
    QuoteImportStatusView,
)


# URLs for new REST views
rest_urlpatterns = [
    # Job CRUD operations (REST style)
    path('rest/jobs/', JobCreateRestView.as_view(), name='job_create_rest'),
    path('rest/jobs/<uuid:job_id>/', JobDetailRestView.as_view(), name='job_detail_rest'),
    
    # Job toggles
    path('rest/jobs/toggle-complex/', JobToggleComplexRestView.as_view(), name='job_toggle_complex_rest'),
    path('rest/jobs/toggle-pricing-methodology/', JobTogglePricingMethodologyRestView.as_view(), name='job_toggle_pricing_methodology_rest'),
    
    # Job events
    path('rest/jobs/<uuid:job_id>/events/', JobEventRestView.as_view(), name='job_events_rest'),
    
    # Job entries
    path('rest/jobs/<uuid:job_id>/time-entries/', JobTimeEntryRestView.as_view(), name='job_time_entries_rest'),
    path('rest/jobs/<uuid:job_id>/material-entries/', JobMaterialEntryRestView.as_view(), name='job_material_entries_rest'),
    path('rest/jobs/<uuid:job_id>/adjustment-entries/', JobAdjustmentEntryRestView.as_view(), name='job_adjustment_entries_rest'),    
    
    # Job costing
    path('rest/jobs/<uuid:pk>/cost_sets/<str:kind>/', JobCostSetView.as_view(), name='job_cost_set_rest'),

    # Workshop PDF
    path('rest/jobs/<uuid:job_id>/workshop-pdf/', WorkshopPDFView.as_view(), name='workshop-pdf'),    
    
    # Job files
    path('rest/jobs/files/upload/', JobFileUploadView.as_view(), name='job_file_upload'),
    path('rest/jobs/files/<int:job_number>/', JobFileView.as_view(), name='job_files_list'),
    path('rest/jobs/files/', JobFileView.as_view(), name='job_file_base'),
    path('rest/jobs/files/<path:file_path>/', JobFileView.as_view(), name='job_file_download'),
    path('rest/jobs/files/<int:file_path>/', JobFileView.as_view(), name='job_file_delete'),
    path('rest/jobs/files/<uuid:file_id>/thumbnail/', JobFileThumbnailView.as_view(), name='job_file_thumbnail'),
    
    # Quote Import
    path('rest/jobs/<uuid:job_id>/quote/import/preview/', QuoteImportPreviewView.as_view(), name='quote_import_preview'),
    path('rest/jobs/<uuid:job_id>/quote/import/', QuoteImportView.as_view(), name='quote_import'),
    path('rest/jobs/<uuid:job_id>/quote/status/', QuoteImportStatusView.as_view(), name='quote_import_status'),
]
