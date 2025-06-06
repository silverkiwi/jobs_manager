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

# CORS settings for frontend development
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Vue.js default dev server
    "http://localhost:8080",  # Vue CLI default port
    "http://localhost:5173",  # Vite default port
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:5173",
    "https://msm-workflow.ngrok-free.app",
    "https://measured-enormously-man.ngrok-free.app",
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Additional CORS settings for better compatibility
CORS_ALLOW_ALL_ORIGINS = True  # Allow all origins during development
CORS_ALLOWED_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_PREFLIGHT_MAX_AGE = 86400

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "mediafiles"

# Enable JWT Authentication for API
ENABLE_JWT_AUTH = True
ENABLE_DUAL_AUTHENTICATION = True
