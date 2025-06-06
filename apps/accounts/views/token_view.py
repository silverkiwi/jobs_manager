from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import status
from apps.accounts.serializers import CustomTokenObtainPairSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Customized token obtain view that handles password reset requirement
    """
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            User = get_user_model()

            try:
                # Try to get user by username (which is email in our case)
                username = request.data.get("username")
                if username:
                    user = User.objects.get(email=username)

                    if hasattr(user, "password_needs_reset") and user.password_needs_reset:
                        response.data["password_needs_reset"] = True
                        response.data["password_reset_url"] = request.build_absolute_uri(
                            reverse("accounts:password_change")
                        )
            except User.DoesNotExist:
                pass

        return response
