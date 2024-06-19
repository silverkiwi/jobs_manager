from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
import os
from .forms import JobForm, JobPricingForm, TimeEntryForm, MaterialEntryForm, AdjustmentEntryForm, StaffForm
from .models import Job, JobPricing, Staff
import logging

logger = logging.getLogger(__name__)


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
        logger.debug("Form data: %s", request.POST)
        if form.is_valid():
            time_entry = form.save(commit=False)
            staff = time_entry.staff
            time_entry.wage_rate = staff.wage_rate
            time_entry.charge_out_rate = staff.charge_out_rate

            # Find or create the 'actual' JobPricing for the selected job
            job = time_entry.job
            job_pricing, created = JobPricing.objects.get_or_create(
                job=job,
                pricing_type='actual',
                defaults={'cost': 0.0, 'revenue': 0.0}
            )

            # Save the time entry with the associated job pricing
            time_entry.job_pricing = job_pricing
            time_entry.save()
            return redirect('time_entry_success')
        else:
            logger.debug("Form errors: %s", form.errors)
    else:
        form = TimeEntryForm()

    return render(request, 'workflow/create_time_entry.html', {'form': form})

from django.shortcuts import render

@login_required
def time_entry_success(request):
    return render(request, 'workflow/time_entry_success.html')

@login_required
def staff_list(request):
    staff_members = Staff.objects.all()
    return render(request, 'workflow/staff_list.html', {'staff_members': staff_members})

@login_required
def staff_profile(request, pk):
    staff_member = get_object_or_404(Staff, pk=pk)
    return render(request, 'workflow/staff_profile.html', {'staff_member': staff_member})

@login_required
def edit_job(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            return redirect('job_detail', pk=job.pk)
    else:
        form = JobForm(instance=job)
    return render(request, 'workflow/edit_job.html', {'form': form})

@login_required
def edit_staff(request, pk):
    staff_member = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        form = StaffForm(request.POST, instance=staff_member)
        if form.is_valid():
            form.save()
            return redirect('staff_profile', pk=staff_member.pk)
    else:
        form = StaffForm(instance=staff_member)
    return render(request, 'workflow/edit_staff.html', {'form': form})

@login_required
def edit_time_entry(request, pk):
    time_entry = get_object_or_404(TimeEntry, pk=pk)
    if request.method == 'POST':
        form = TimeEntryForm(request.POST, instance=time_entry)
        if form.is_valid():
            # Only change the fields specified in the form, not wage_rate or charge_out_rate
            time_entry = form.save(commit=False)
            time_entry.save(update_fields=['date', 'duration', 'note', 'is_billable', 'job', 'staff'])
            return redirect('time_entry_success')
    else:
        form = TimeEntryForm(instance=time_entry)

    return render(request, 'workflow/edit_time_entry.html', {'form': form})
