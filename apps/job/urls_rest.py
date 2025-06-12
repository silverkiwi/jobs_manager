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

from apps.job.views.workshop_view import WorkshopPDFView

# URLs para novas views REST
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
    path('rest/jobs/<uuid:job_id>/workshop-pdf/', WorkshopPDFView.as_view(), name='workshop-pdf'),
]
