from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy


class SecurityPasswordChangeView(PasswordChangeView):
    template_name = "accounts/registration/password_change_form.html"
    success_url = reverse_lazy("accounts:password_change_done")
