from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class LoginRequiredMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.exempt_urls = [reverse("accounts:login")]
        self.exempt_url_prefixes = []

        if hasattr(settings, "LOGIN_EXEMPT_URLS"):
            for url_name in settings.LOGIN_EXEMPT_URLS:
                # Using URL prefixes instead of doing reverse
                try:
                    # Try to resolve the URL name to an actual path
                    self.exempt_urls.append(reverse(url_name))                   
                except Exception as e:
                    # If it fails, we assume it's a prefix and add it directly
                    self.exempt_url_prefixes.append(url_name)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Check exact path matches first
        if request.path_info in self.exempt_urls:
            return self.get_response(request)

        # Check path prefixes
        path = request.path_info.lstrip("/")
        if any(path.startswith(prefix) for prefix in self.exempt_url_prefixes):
            return self.get_response(request)

        # Special handling for API endpoints - they should not redirect to login
        if request.path_info.startswith('/accounts/') and '/api/' in request.path_info:
            return self.get_response(request)
        
        # Handle logout endpoints specifically
        if request.path_info.endswith('/logout/'):
            return self.get_response(request)

        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)

        return self.get_response(request)

        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)

        return self.get_response(request)


class PasswordStrengthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, "ENABLE_JWT_AUTH", False) and not hasattr(
            request, "session"
        ):
            return self.get_response(request)

        if request.user.is_authenticated and request.user.password_needs_reset:
            exempt_urls = [
                reverse("accounts:password_change"),
                reverse("accounts:password_change_done"),
                reverse("accounts:logout"),
                reverse("accounts:login"),
                reverse("accounts:token_obtain_pair"),
                reverse("accounts:token_refresh"),
                reverse("accounts:token_verify"),
            ]

            if request.path.startswith("/api/") and getattr(
                settings, "ENABLE_DUAL_AUTHENTICATION", False
            ):
                return self.get_response(request)

            if request.path not in exempt_urls and not request.path.startswith(
                "/static/"
            ):
                messages.warning(
                    request,
                    "For security reasons, you need to update your password to meet our new requirements.",
                )
                return redirect("accounts:password_change")

        return self.get_response(request)
