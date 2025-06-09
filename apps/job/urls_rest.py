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
    create_job_rest_api,
    job_detail_rest_api,
    toggle_complex_job_rest_api,
    toggle_pricing_methodology_rest_api,
    add_job_event_rest_api,
)

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
    
    # Compatibility endpoints (functional views)
    path('api/rest/create-job/', create_job_rest_api, name='create_job_rest_api'),
    path('api/rest/jobs/<uuid:job_id>/', job_detail_rest_api, name='job_detail_rest_api'),
    path('api/rest/toggle-complex-job/', toggle_complex_job_rest_api, name='toggle_complex_job_rest_api'),
    path('api/rest/toggle-pricing-methodology/', toggle_pricing_methodology_rest_api, name='toggle_pricing_methodology_rest_api'),
    path('api/rest/jobs/<uuid:job_id>/add-event/', add_job_event_rest_api, name='add_job_event_rest_api'),
]
