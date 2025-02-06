from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "msm-workflow.ngrok-free.app",
    "measured-enormously-man.ngrok-free.app",
]

INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405

MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa: F405

INTERNAL_IPS = ["127.0.0.1"]

# CSRF settings for ngrok
CSRF_TRUSTED_ORIGINS = [
    "https://msm-workflow.ngrok-free.app",
    "https://measured-enormously-man.ngrok-free.app",
    "http://localhost",
    "http://127.0.0.1",
]

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"
