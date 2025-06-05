from django.urls import reverse
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import status


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Customized token obtain view that handles password reset requirement
    """

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            from django.contrib.auth import get_user_model

            User = get_user_model()

            try:
                user = User.objects.get(email=request.data["email"])

                if hasattr(user, "password_needs_reset") and user.password_needs_reset:
                    response.data["password_needs_reset"] = True
                    response.data["password_reset_url"] = request.build_absolute_uri(
                        reverse("password_change")
                    )
            except User.DoesNotExist:
                pass

        return response
