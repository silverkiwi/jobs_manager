import os

from dotenv import load_dotenv

from .base import BASE_DIR

load_dotenv(BASE_DIR / ".env")
ENVIRONMENT = os.getenv("DJANGO_ENV", "local")
AWS = os.getenv("AWS", False)

if ENVIRONMENT == "production_like":
    from .production_like import *  # noqa: F403, F401

    if AWS:
        DEBUG = False
    else:
        DEBUG = (
            True  # Need to set it as True otherwise staticfiles won't be served locally
        )
else:
    from .local import *  # noqa: F403, F401
