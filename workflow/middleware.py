from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class LoginRequiredMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.exempt_urls = [reverse("login")]
        self.exempt_url_prefixes = []
        
        if hasattr(settings, "LOGIN_EXEMPT_URLS"):
            for url in settings.LOGIN_EXEMPT_URLS:
                # Using URL prefixes instead of doing reverse
                self.exempt_url_prefixes.append(url)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path_info in self.exempt_urls:
            return self.get_response(request)
            
        path = request.path_info.lstrip('/')
        if any(path.startswith(prefix) for prefix in self.exempt_url_prefixes):
            return self.get_response(request)

        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
            
        return self.get_response(request)


class PasswordStrengthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.password_needs_reset:
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
