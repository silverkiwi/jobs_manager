# Register your models here.

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Job, Staff
from .forms import StaffCreationForm, StaffChangeForm

from simple_history.admin import SimpleHistoryAdmin


class StaffAdmin(UserAdmin):
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
    list_filter = (
        "is_staff",
        "is_active",
    )
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal Info",
            {"fields": ("first_name", "last_name", "pay_rate", "ims_payroll_id")},
        ),
        ("Permissions", {"fields": ("is_staff", "is_active")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "pay_rate",
                    "ims_payroll_id",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )
    search_fields = ("email",)
    ordering = ("email",)


admin.site.register(Job, SimpleHistoryAdmin)
admin.site.register(Staff, SimpleHistoryAdmin)
