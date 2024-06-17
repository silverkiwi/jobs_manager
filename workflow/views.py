from django.shortcuts import render, redirect, get_object_or_404
import os
from .forms import JobForm, PricingModelForm, TimeEntryForm, MaterialEntryForm, ManualEntryForm
from .models import Job, PricingModel


def index(request):
    return render(request, 'workflow/index.html')

def about(request):
    return render(request, 'workflow/about.html')

from django.shortcuts import render, redirect, get_object_or_404
from .forms import JobForm, PricingModelForm
from .models import Job, PricingModel

def create_job(request):
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('job_list')
    else:
        form = JobForm()
    return render(request, 'workflow/job_form.html', {'form': form})

def job_list(request):
    jobs = Job.objects.all()
    return render(request, 'workflow/job_list.html', {'jobs': jobs})

def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    pricing_models = job.pricing_models.all()
    return render(request, 'workflow/job_detail.html', {
        'job': job,
        'pricing_models': pricing_models,
    })

def create_pricing_model(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    if request.method == 'POST':
        form = PricingModelForm(request.POST)
        if form.is_valid():
            pricing_model = form.save(commit=False)
            pricing_model.job = job
            pricing_model.save()
            return redirect('job_detail', pk=job.id)
    else:
        form = PricingModelForm()
    return render(request, 'workflow/pricing_model_form.html', {'form': form, 'job': job})

from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from .forms import StaffCreationForm, StaffChangeForm

def register(request):
    if request.method == 'POST':
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            form.save()
            email = form.cleaned_data.get('email')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(email=email, password=raw_password)
            login(request, user)
            return redirect('job_list')
    else:
        form = StaffCreationForm()
    return render(request, 'workflow/register.html', {'form': form})

def profile(request):
    if request.method == 'POST':
        form = StaffChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('job_list')
    else:
        form = StaffChangeForm(instance=request.user)
    return render(request, 'workflow/profile.html', {'form': form})
