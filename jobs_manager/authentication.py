from django.conf import settings
from rest_framework import exceptions
from rest_framework_simplejwt.authentication import (
    JWTAuthentication as BaseJWTAuthentication,
)
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import logging

logger = logging.getLogger(__name__)


class JWTAuthentication(BaseJWTAuthentication):
    """
    Custom JWT Authentication that supports both Authorization header and httpOnly cookies.
    """

    def authenticate(self, request):
        if not getattr(settings, "ENABLE_JWT_AUTH", False):
            logger.debug("JWT auth disabled via settings.")
            return None

        try:
            # First try to get token from Authorization header (default behavior)
            result = super().authenticate(request)
            logger.debug(f"Result from header: {result}")

            # If no token in header, try to get from httpOnly cookie
            if result is None:
                raw_token = self.get_raw_token_from_cookie(request)
                logger.debug(f"Raw token from cookie: {raw_token}")
                if raw_token is not None:
                    validated_token = self.get_validated_token(raw_token)
                    logger.debug(f"Validated token: {validated_token}")
                    user = self.get_user(validated_token)
                    logger.debug(f"Authenticated user: {user}")
                    result = (user, validated_token)

            if result is None:
                logger.warning("No JWT token found in header or cookie.")
                return None

            user, token = result

            if not user.is_active:
                logger.warning(f"Inactive user: {user}")
                raise exceptions.AuthenticationFailed(
                    "User is inactive.", code="user_inactive"
                )

            if hasattr(user, "password_needs_reset") and user.password_needs_reset:
                logger.warning(
                    f"User {getattr(user, 'email', user)} authenticated via JWT but needs to reset password."
                )

            logger.info(
                f"User {getattr(user, 'email', user)} authenticated successfully via JWT."
            )
            return result
        except (InvalidToken, TokenError) as e:
            logger.error(f"JWT token error: {e}")
            if getattr(settings, "ENABLE_DUAL_AUTHENTICATION", False):
                return None
            raise exceptions.AuthenticationFailed(str(e))

    def get_raw_token_from_cookie(self, request):
        """
        Extract raw token from httpOnly cookie.
        """
        simple_jwt_settings = getattr(settings, "SIMPLE_JWT", {})
        cookie_name = simple_jwt_settings.get("AUTH_COOKIE", "access_token")
        logger.debug(f"Looking for cookie: {cookie_name}")
        if cookie_name and cookie_name in request.COOKIES:
            logger.debug(
                f"Found cookie {cookie_name} with value: {request.COOKIES[cookie_name]}"
            )
            return request.COOKIES[cookie_name].encode("utf-8")
        logger.debug(f"Cookie {cookie_name} not found in request.")
        return None
