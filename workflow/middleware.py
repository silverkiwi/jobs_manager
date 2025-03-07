from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class LoginRequiredMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # List of URL names that should be accessible without login
        exempt_urls = [reverse("login")]
        if hasattr(settings, "LOGIN_EXEMPT_URLS"):
            exempt_urls += [reverse(url) for url in settings.LOGIN_EXEMPT_URLS]

        if not request.user.is_authenticated and request.path_info not in exempt_urls:
            return redirect(settings.LOGIN_URL)
        return self.get_response(request)


class PasswordStrengthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and getattr(request.user, 'password_needs_reset', False):
            exempt_urls = [
                reverse('password_change'),
                reverse('password_change_done'),
                reverse('logout'),
                reverse('login'),
            ]
            
            if request.path not in exempt_urls and not request.path.startswith('/static/'):
                messages.warning(
                    request, 
                    "For security reasons, you need to update your password to meet our new requirements."
                )
                return redirect('password_change')
        
        return self.get_response(request)
