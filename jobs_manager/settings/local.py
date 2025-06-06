from .base import *  # noqa: F403

# Load DEBUG from environment - should be False in production
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Load ALLOWED_HOSTS from environment variables
allowed_hosts_env = os.getenv("ALLOWED_HOSTS", "")
if allowed_hosts_env:
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(",") if host.strip()]
else:
    # Fallback for development
    ALLOWED_HOSTS = [
        "127.0.0.1",
        "localhost",
    ]

INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405

MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa: F405

INTERNAL_IPS = ["127.0.0.1"]

# CSRF settings - Load from environment variables
csrf_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
csrf_trusted_origins = []

if csrf_origins_env:
    # Convert CORS origins to CSRF trusted origins (add https:// variants)
    for origin in csrf_origins_env.split(","):
        origin = origin.strip()
        if origin:
            csrf_trusted_origins.append(origin)
            # Add https variant if it's http
            if origin.startswith("http://"):
                https_variant = origin.replace("http://", "https://")
                csrf_trusted_origins.append(https_variant)

# Add ngrok domain if available
ngrok_domain = os.getenv("NGROK_DOMAIN")
if ngrok_domain:
    csrf_trusted_origins.append(ngrok_domain)
    # Also add http variant for local development
    if ngrok_domain.startswith("https://"):
        http_variant = ngrok_domain.replace("https://", "http://")
        csrf_trusted_origins.append(http_variant)

CSRF_TRUSTED_ORIGINS = csrf_trusted_origins if csrf_trusted_origins else [
    "http://localhost",
    "http://127.0.0.1",
]

# CORS Configuration - Load from environment variables
cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
if cors_origins_env:
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
else:
    # Fallback for development if not set in .env
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",  # Vue.js default dev server
        "http://localhost:8080",  # Vue CLI default port
        "http://localhost:5173",  # Vite default port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ]

# Add ngrok domain from environment if available
ngrok_domain = os.getenv("NGROK_DOMAIN")
if ngrok_domain and ngrok_domain not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS.append(ngrok_domain)

CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "True").lower() == "true"

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

# Enable JWT Authentication for API - Load from environment
ENABLE_JWT_AUTH = os.getenv("ENABLE_JWT_AUTH", "True").lower() == "true"
ENABLE_DUAL_AUTHENTICATION = os.getenv("ENABLE_DUAL_AUTHENTICATION", "True").lower() == "true"
