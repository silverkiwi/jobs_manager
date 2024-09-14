# workflow/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from simple_history.admin import SimpleHistoryAdmin
from workflow.models import Job, Staff, TimeEntry, MaterialEntry, AdjustmentEntry, JobPricing
from workflow.forms import StaffCreationForm, StaffChangeForm

# Remove the duplicate StaffAdmin class and ensure only one exists
@admin.register(Staff)
class StaffAdmin(UserAdmin, SimpleHistoryAdmin):
    add_form = StaffCreationForm
    form = StaffChangeForm
    model = Staff
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    )
    list_filter = ("is_staff", "is_active",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": (
            "first_name",
            "last_name",
            "preferred_name",
            "wage_rate",
            "charge_out_rate",
            "ims_payroll_id",
        )}),
        ("Permissions", {"fields": (
            "is_staff",
            "is_active",
            "is_superuser",
            "groups",
            "user_permissions",
        )}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "first_name",
                "last_name",
                "preferred_name",
                "wage_rate",
                "charge_out_rate",
                "ims_payroll_id",
                "password1",
                "password2",
                "is_staff",
                "is_active",
            ),
        }),
    )
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

@admin.register(Job)
class JobAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'client_name', 'job_number', 'status', 'paid', 'date_created')
    search_fields = ('name', 'client_name', 'job_number', 'order_number', 'contact_person')
    list_filter = ('status', 'paid', 'date_created')

@admin.register(JobPricing)
class JobPricingAdmin(SimpleHistoryAdmin):
    list_display = ('job', 'estimate_type', 'created_at', 'updated_at')
    search_fields = ('job__name', 'estimate_type')
    list_filter = ('estimate_type', 'created_at', 'updated_at')

@admin.register(AdjustmentEntry)
class AdjustmentEntryAdmin(admin.ModelAdmin):
    list_display = ('job_pricing', 'description', 'cost', 'revenue', 'id')
    search_fields = ('description',)
    list_filter = ('job_pricing__estimate_type',)

@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ('job_pricing', 'staff', 'date', 'hours', 'cost', 'revenue')
    search_fields = ('staff__first_name', 'staff__last_name', 'job_pricing__job__name')
    list_filter = ('job_pricing__estimate_type', 'date')

@admin.register(MaterialEntry)
class MaterialEntryAdmin(admin.ModelAdmin):
    list_display = ('job_pricing', 'description', 'quantity', 'unit_cost', 'cost', 'revenue')
    search_fields = ('description',)
    list_filter = ('job_pricing__estimate_type',)

