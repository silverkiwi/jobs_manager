from django.urls import path
from django.contrib.auth import views as auth_views
from workflow.views import kanban, xero, core_views
from django.views.generic import RedirectView

from django.urls import path

#    path('', views.DashboardView.as_view(), name='dashboard'),

urlpatterns = [
    path('', RedirectView.as_view(url='/kanban/'), name='dashboard'),
    path('api/fetch_status_values/', core_views.fetch_status_values, name='fetch_status_values'),
    path('api/xero/authenticate/', xero.xero_authenticate, name='xero_authenticate'),
    path('api/xero/oauth/callback/', xero.xero_oauth_callback, name='xero_oauth_callback'),
    path('api/xero/success/', xero.xero_connection_success, name='xero_connection_success'),
    path('api/xero/error/', xero.xero_auth_error, name='xero_auth_error'),  # Add this line
    path('api/xero/contacts/', xero.get_xero_contacts, name='xero_get_contacts'),
    path('api/xero/refresh_token/', xero.refresh_xero_token, name='xero_refresh_token'),
    path('jobs/create/', core_views.JobCreateView.as_view(), name='create_job'),
    path('jobs/', core_views.JobListView.as_view(), name='job_list'),
    path('jobs/<uuid:pk>/', core_views.JobDetailView.as_view(), name='job_detail'),
    path('jobs/<uuid:pk>/edit/', core_views.JobUpdateView.as_view(), name='edit_job'),
    path('jobs/<uuid:pk>/update_status/', kanban.update_job_status, name='update_job_status'),
    path('kanban/', kanban.kanban_view, name='kanban'),
    path('kanban/fetch_jobs/<str:status>/', kanban.fetch_jobs, name='fetch_jobs'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('staff/', core_views.StaffListView.as_view(), name='staff_list'),
    path('staff/register/', core_views.RegisterView.as_view(), name='register'),
    path('staff/profile/', core_views.ProfileView.as_view(), name='profile'),
    path('staff/<uuid:pk>/', core_views.StaffProfileView.as_view(), name='staff_profile'),
    path('staff/<uuid:pk>/edit/', core_views.StaffUpdateView.as_view(), name='edit_staff'),
    path('time_entries/create/', core_views.CreateTimeEntryView.as_view(), name='create_time_entry'),
    path('time_entries/<uuid:pk>/edit/', core_views.TimeEntryUpdateView.as_view(), name='edit_time_entry'),
    path('time_entries/success/', core_views.TimeEntrySuccessView.as_view(), name='time_entry_success'),
]
