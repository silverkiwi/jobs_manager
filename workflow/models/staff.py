import uuid
from datetime import timezone
from typing import Optional, List

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from workflow.models.staff_manager import StaffManager


class Staff(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )  # type: ignore
    email: str = models.EmailField(unique=True)  # type: ignore
    first_name: str = models.CharField(max_length=30)  # type: ignore
    last_name: str = models.CharField(max_length=30)  # type: ignore
    preferred_name: Optional[str] = models.CharField(
        max_length=30, blank=True, null=True
    )  # type: ignore
    wage_rate: float = models.DecimalField(
        max_digits=10, decimal_places=2
    )  # type: ignore
    charge_out_rate: float = models.DecimalField(
        max_digits=10, decimal_places=2
    )  # type: ignore
    ims_payroll_id: str = models.CharField(max_length=100, unique=True)  # type: ignore
    is_active: bool = models.BooleanField(default=True)  # type: ignore
    is_staff: bool = models.BooleanField(default=False)  # type: ignore
    date_joined: timezone.datetime = models.DateTimeField(
        default=timezone.now
    )  # type: ignore
    history: HistoricalRecords = HistoricalRecords()  # type: ignore

    objects: "StaffManager" = StaffManager()

    USERNAME_FIELD: str = "email"
    REQUIRED_FIELDS: List[str] = [
        "first_name",
        "last_name",
        "wage_rate",
        "charge_out_rate",
        "ims_payroll_id",
    ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def get_display_name(self) -> str:
        return self.preferred_name or self.first_name
