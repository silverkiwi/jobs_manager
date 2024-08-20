from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

from django.urls import path

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('jobs/create/', views.JobCreateView.as_view(), name='create_job'),
    path('jobs/', views.JobListView.as_view(), name='job_list'),
    path('jobs/<uuid:pk>/', views.JobDetailView.as_view(), name='job_detail'),
    path('jobs/<uuid:pk>/edit/', views.JobUpdateView.as_view(), name='edit_job'),
    path('staff/register/', views.RegisterView.as_view(), name='register'),
    path('staff/profile/', views.ProfileView.as_view(), name='profile'),
    path('staff/', views.StaffListView.as_view(), name='staff_list'),
    path('staff/<uuid:pk>/', views.StaffProfileView.as_view(), name='staff_profile'),
    path('staff/<uuid:pk>/edit/', views.StaffUpdateView.as_view(), name='edit_staff'),
    path('time_entries/create/', views.CreateTimeEntryView.as_view(), name='create_time_entry'),
    path('time_entries/<uuid:pk>/edit/', views.TimeEntryUpdateView.as_view(), name='edit_time_entry'),
    path('time_entries/success/', views.TimeEntrySuccessView.as_view(), name='time_entry_success'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
