from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
]


from django.urls import path
from .views import create_job, job_list, job_detail, create_pricing_model

from django.urls import path
from .views import create_job, job_list, job_detail, create_pricing_model

urlpatterns = [
    path('jobs/create/', create_job, name='create_job'),
    path('jobs/', job_list, name='job_list'),
    path('jobs/<int:pk>/', job_detail, name='job_detail'),
    path('jobs/<int:job_id>/pricing_model/create/', create_pricing_model, name='create_pricing_model'),
]
