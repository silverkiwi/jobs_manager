from django.conf import settings
from rest_framework import exceptions
from rest_framework_simplejwt.authentication import (
    JWTAuthentication as BaseJWTAuthentication,
)
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import logging

logger = logging.getLogger(__name__)
print("[IMPORT] jobs_manager.authentication.py loaded")


class JWTAuthentication(BaseJWTAuthentication):
    """
    Custom JWT Authentication that supports both Authorization header and httpOnly cookies.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info("[INIT] JWTAuthentication class initialized!")
        print("[INIT] JWTAuthentication class initialized!")

    def authenticate(self, request):
        if not getattr(settings, "ENABLE_JWT_AUTH", False):
            logger.info("JWT auth disabled via settings.")
            print("[AUTH] JWT auth disabled via settings.")
            return None

        try:
            # First try to get token from Authorization header (default behavior)
            result = super().authenticate(request)
            logger.info(f"Result from header: {result}")
            print(f"[AUTH] Result from header: {result}")

            # If no token in header, try to get from httpOnly cookie
            if result is None:
                raw_token = self.get_raw_token_from_cookie(request)
                logger.info(f"Raw token from cookie: {raw_token}")
                print(f"[AUTH] Raw token from cookie: {raw_token}")
                if raw_token is not None:
                    validated_token = self.get_validated_token(raw_token)
                    logger.info(f"Validated token: {validated_token}")
                    print(f"[AUTH] Validated token: {validated_token}")
                    user = self.get_user(validated_token)
                    logger.info(f"Authenticated user: {user}")
                    print(f"[AUTH] Authenticated user: {user}")
                    result = (user, validated_token)

            if result is None:
                logger.info("No JWT token found in header or cookie.")
                print("[AUTH] No JWT token found in header or cookie.")
                return None

            user, token = result

            if not user.is_active:
                logger.info(f"Inactive user: {user}")
                print(f"[AUTH] Inactive user: {user}")
                raise exceptions.AuthenticationFailed(
                    "User is inactive.", code="user_inactive"
                )

            if hasattr(user, "password_needs_reset") and user.password_needs_reset:
                logger.info(
                    f"User {getattr(user, 'email', user)} authenticated via JWT but needs to reset password."
                )
                print(
                    f"[AUTH] User {getattr(user, 'email', user)} authenticated via JWT but needs to reset password."
                )

            logger.info(
                f"User {getattr(user, 'email', user)} authenticated successfully via JWT."
            )
            print(
                f"[AUTH] User {getattr(user, 'email', user)} authenticated successfully via JWT."
            )
            return result
        except (InvalidToken, TokenError) as e:
            logger.info(f"JWT token error: {e}")
            print(f"[AUTH] JWT token error: {e}")
            if getattr(settings, "ENABLE_DUAL_AUTHENTICATION", False):
                return None
            raise exceptions.AuthenticationFailed(str(e))

    def get_raw_token_from_cookie(self, request):
        """
        Extract raw token from httpOnly cookie.
        """
        simple_jwt_settings = getattr(settings, "SIMPLE_JWT", {})
        cookie_name = simple_jwt_settings.get("AUTH_COOKIE", "access_token")
        logger.info(f"Looking for cookie: {cookie_name}")
        print(f"[AUTH] Looking for cookie: {cookie_name}")
        if cookie_name and cookie_name in request.COOKIES:
            logger.info(
                f"Found cookie {cookie_name} with value: {request.COOKIES[cookie_name]}"
            )
            print(
                f"[AUTH] Found cookie {cookie_name} with value: {request.COOKIES[cookie_name]}"
            )
            return request.COOKIES[cookie_name].encode("utf-8")
        logger.info(f"Cookie {cookie_name} not found in request.")
        print(f"[AUTH] Cookie {cookie_name} not found in request.")
        return None
