from typing import Any, Optional, cast

from django.contrib.auth.base_user import BaseUserManager

from workflow.models import Staff


class StaffManager(BaseUserManager):
    def create_user(
        self, email: str, password: Optional[str] = None, **extra_fields: Any
    ) -> Staff:
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = cast(Staff, self.model(email=email, **extra_fields))
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: Optional[str] = None, **extra_fields: Any
    ) -> Staff:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("wage_rate", 0)
        extra_fields.setdefault("charge_out_rate", 0)
        return self.create_user(email, password, **extra_fields)
