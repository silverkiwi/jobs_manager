from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # List of URL names that should be accessible without login
        exempt_urls = [reverse("login")]
        if hasattr(settings, "LOGIN_EXEMPT_URLS"):
            exempt_urls += [reverse(url) for url in settings.LOGIN_EXEMPT_URLS]

        if not request.user.is_authenticated and request.path_info not in exempt_urls:
            return redirect(settings.LOGIN_URL)
        return self.get_response(request)
