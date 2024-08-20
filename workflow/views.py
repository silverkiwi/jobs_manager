from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, FormView
from django.urls import reverse_lazy
from .forms import StaffCreationForm, StaffChangeForm, StaffForm, JobForm, JobPricingForm, TimeEntryForm
from .models import Job, JobPricing, Staff, TimeEntry
import logging

logger = logging.getLogger(__name__)

class IndexView(TemplateView):
    template_name = 'workflow/index.html'

class AboutView(TemplateView):
    template_name = 'workflow/about.html'

class JobCreateView(CreateView):
    model = Job
    form_class = JobForm
    template_name = 'workflow/job_form.html'
    success_url = reverse_lazy('job_list')

class JobListView(ListView):
    model = Job
    template_name = 'workflow/job_list.html'
    context_object_name = 'jobs'

class JobDetailView(DetailView):
    model = Job
    template_name = 'workflow/job_detail.html'
    context_object_name = 'job'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job = self.object

        pricing_models = job.job_pricings.all()
        pricing_data = []

        for model in pricing_models:
            time_entries = model.time_entries.all()
            material_entries = model.material_entries.all()
            adjustment_entries = model.adjustment_entries.all()

            total_time_cost = sum(entry.cost for entry in time_entries)
            total_time_revenue = sum(entry.revenue for entry in time_entries)

            total_material_cost = sum(entry.cost for entry in material_entries)
            total_material_revenue = sum(entry.revenue for entry in material_entries)

            total_adjustment_cost = sum(entry.cost for entry in adjustment_entries)
            total_adjustment_revenue = sum(entry.revenue for entry in adjustment_entries)

            total_cost = total_time_cost + total_material_cost + total_adjustment_cost
            total_revenue = total_time_revenue + total_material_revenue + total_adjustment_revenue

            pricing_data.append({
                'model': model,
                'total_time_cost': total_time_cost,
                'total_time_revenue': total_time_revenue,
                'total_material_cost': total_material_cost,
                'total_material_revenue': total_material_revenue,
                'total_adjustment_cost': total_adjustment_cost,
                'total_adjustment_revenue': total_adjustment_revenue,
                'total_cost': total_cost,
                'total_revenue': total_revenue,
            })

        context['pricing_data'] = pricing_data

        history = job.history.all()
        history_diffs = []
        for i in range(len(history) - 1):
            new_record = history[i]
            old_record = history[i + 1]
            delta = new_record.diff_against(old_record)
            changes = [
                {
                    'field': change.field,
                    'old': change.old,
                    'new': change.new
                }
                for change in delta.changes
            ]
            history_diffs.append((new_record, changes))

        # Add the initial record with no changes
        if history:
            history_diffs.append((history.last(), []))

        context['history_diffs'] = history_diffs


        return context

class RegisterView(FormView):
    template_name = 'workflow/register.html'
    form_class = StaffCreationForm
    success_url = reverse_lazy('job_list')

    def form_valid(self, form):
        form.save()
        email = form.cleaned_data.get('email')
        raw_password = form.cleaned_data.get('password1')
        user = authenticate(email=email, password=raw_password)
        login(self.request, user)
        return super().form_valid(form)

class ProfileView(UpdateView):
    model = Staff
    form_class = StaffChangeForm
    template_name = 'workflow/profile.html'
    success_url = reverse_lazy('job_list')

    def get_object(self):
        return self.request.user

class CreateTimeEntryView(CreateView):
    model = TimeEntry
    form_class = TimeEntryForm
    template_name = 'workflow/create_time_entry.html'
    success_url = reverse_lazy('time_entry_success')

    def form_valid(self, form):
        time_entry = form.save(commit=False)
        staff = time_entry.staff
        time_entry.wage_rate = staff.wage_rate
        time_entry.charge_out_rate = staff.charge_out_rate

        job = time_entry.job
        job_pricing, created = JobPricing.objects.get_or_create(
            job=job,
            pricing_type='actual'
        )

        time_entry.job_pricing = job_pricing
        time_entry.save()

        job.save(update_fields=["last_updated"])

        return super().form_valid(form)

    def form_invalid(self, form):
        logger.debug("Form errors: %s", form.errors)
        return super().form_invalid(form)

class TimeEntrySuccessView(TemplateView):
    template_name = 'workflow/time_entry_success.html'

class StaffListView(ListView):
    model = Staff
    template_name = 'workflow/staff_list.html'
    context_object_name = 'staff_members'

class StaffProfileView(DetailView):
    model = Staff
    template_name = 'workflow/staff_profile.html'
    context_object_name = 'staff_member'

class JobUpdateView(UpdateView):
    model = Job
    form_class = JobForm
    template_name = 'workflow/edit_job.html'

    def get_success_url(self):
        return reverse_lazy('job_detail', kwargs={'pk': self.object.pk})

class StaffUpdateView(UpdateView):
    model = Staff
    form_class = StaffForm
    template_name = 'workflow/edit_staff.html'

    def get_success_url(self):
        return reverse_lazy('staff_profile', kwargs={'pk': self.object.pk})

class TimeEntryUpdateView( UpdateView):
    model = TimeEntry
    form_class = TimeEntryForm
    template_name = 'workflow/edit_time_entry.html'
    success_url = reverse_lazy('time_entry_success')

    def form_valid(self, form):
        time_entry = form.save(commit=False)
        time_entry.save(update_fields=['date', 'minutes', 'note', 'is_billable', 'job', 'staff'])
        return super().form_valid(form)

class DashboardView(TemplateView):
    template_name = 'workflow/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # You can add any additional context data here if needed
        return context
