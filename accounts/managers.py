from __future__ import annotations

from django.contrib.auth.base_user import BaseUserManager
from typing import cast, TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from accounts.models import Staff


class StaffManager(BaseUserManager):
    """
    Custom manager for Staff user model that combines:
    - Type hints for better code maintainability
    - Strict validation for superuser creation
    - Proper default values for staff-specific fields
    """
    
    def create_user(self, email: str, password: Optional[str] = None, **extra_fields: Any) -> "Staff":
        if not email:
            raise ValueError("The Email field must be set")
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return cast("Staff", user)

    def create_superuser(self, email: str, password: str, **extra_fields: Any) -> "Staff":
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('wage_rate', 0)  # Default wage rate for superusers
        
        # Strict validation for superuser status
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)
    