from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
import os
from .forms import JobForm, JobPricingForm, TimeEntryForm, MaterialEntryForm, AdjustmentEntryForm
from .models import Job, JobPricing


def index(request):
    return render(request, 'workflow/index.html')

def about(request):
    return render(request, 'workflow/about.html')

from django.shortcuts import render, redirect, get_object_or_404
from .forms import JobForm, JobPricingForm
from .models import Job, JobPricing

@login_required
def create_job(request):
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('job_list')
    else:
        form = JobForm()
    return render(request, 'workflow/job_form.html', {'form': form})

@login_required
def job_list(request):
    jobs = Job.objects.all()
    return render(request, 'workflow/job_list.html', {'jobs': jobs})

@login_required
def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    history = job.history.all().order_by('-history_date')
    context = {
        'job': job,
        'job_pricings': job.job_pricings.all(),
        'history': history,
    }
    return render(request, 'workflow/job_detail.html', context)

def create_job_pricing(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    if request.method == 'POST':
        form = JobPricingForm(request.POST)
        if form.is_valid():
            job_pricing = form.save(commit=False)
            job_pricing.job = job
            job_pricing.save()
            return redirect('job_detail', pk=job.id)
    else:
        form = JobPricingForm()
    return render(request, 'workflow/job_pricing_form.html', {'form': form, 'job': job})

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

from django.shortcuts import render, redirect
from .forms import TimeEntryForm

@login_required
def create_time_entry(request):
    if request.method == 'POST':
        form = TimeEntryForm(request.POST)
        if form.is_valid():
            time_entry = form.save(commit=False)
            staff = time_entry.staff
            time_entry.wage_rate = staff.wage_rate
            time_entry.charge_out_rate = staff.charge_out_rate
            time_entry.save()
            return redirect('time_entry_success')  # Redirect to a success page or another page
    else:
        form = TimeEntryForm()

    return render(request, 'workflow/create_time_entry.html', {'form': form})
