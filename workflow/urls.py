from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import create_job, job_list, job_detail, create_job_pricing, register, profile


urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
]


from django.urls import path
from .views import create_job, job_list, job_detail, create_job_pricing

from django.urls import path
from .views import create_job, job_list, job_detail, create_job_pricing, create_time_entry

urlpatterns = [
    path('jobs/create/', create_job, name='create_job'),
    path('jobs/', job_list, name='job_list'),
    path('jobs/<uuid:pk>/', job_detail, name='job_detail'),
    path('jobs/<uuid:pk>/edit/', views.edit_job, name='edit_job'),
    path('jobs/<uuid:job_id>/job_pricing/create/', create_job_pricing, name='create_job_pricing'),
    path('staff/register/', register, name='register'),
    path('staff/profile/', profile, name='profile'),
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/<uuid:pk>/', views.staff_profile, name='staff_profile'),
    path('staff/<uuid:pk>/edit/', views.edit_staff, name='edit_staff'),
    path('time_entries/create/', create_time_entry, name='create_time_entry'),
    path('time_entries/<uuid:pk>/edit/', views.edit_time_entry, name='edit_time_entry'),
    path('time_entries/success/', views.time_entry_success, name='time_entry_success'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
