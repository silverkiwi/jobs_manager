from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, ClassVar, List, Optional, cast

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords  # type: ignore


class StaffManager(BaseUserManager):
    def create_user(
        self, email: str, password: Optional[str] = None, **extra_fields: Any
    ) -> "Staff":
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = cast(Staff, self.model(email=email, **extra_fields))
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: Optional[str] = None, **extra_fields: Any
    ) -> "Staff":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("wage_rate", 0)
        extra_fields.setdefault("charge_out_rate", 0)
        return self.create_user(email, password, **extra_fields)


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
    date_joined: datetime = models.DateTimeField(default=timezone.now)  # type: ignore
    history: HistoricalRecords = HistoricalRecords()  # type: ignore

    objects = StaffManager()  # Use the custom manager

    USERNAME_FIELD: str = "email"
    REQUIRED_FIELDS: ClassVar[List[str]] = [
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

    def is_staff_manager(self):
        return self.groups.filter(name="StaffManager").exists() or self.is_superuser
