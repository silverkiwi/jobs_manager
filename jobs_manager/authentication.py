from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication as BaseJWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework import exceptions

class JWTAuthentication(BaseJWTAuthentication):
    """
    Custom JWT Authentication.
    """

    def authenticate(self, request):
        if not getattr(settings, "ENABLE_JWT_AUTH", False):
            return None

        try:
            result = super().authenticate(request)

            if result is None:
                return None

            user, token = result

            if not user.is_active:
                raise exceptions.AuthenticationFailed(
                    "User is inactive.", code="user_inactive"
                )
            
            if hasattr(user, "password_needs_reset") and user.password_needs_reset:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"User {user.email} authenticated via JWT but needs to reset password.")
            
            return result

        except (InvalidToken, TokenError) as e:
            if getattr(settings, "ENABLE_DUAL_AUTHENTICATION", False):
                return None
            
            raise exceptions.AuthenticationFailed(str(e))
