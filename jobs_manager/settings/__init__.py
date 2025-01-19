import os

from dotenv import load_dotenv

from .base import BASE_DIR


load_dotenv(BASE_DIR / ".env")
ENVIRONMENT = os.getenv("DJANGO_ENV", "local")
AWS = os.getenv("AWS", False)

if ENVIRONMENT == "production_like":
    from .production_like import *

    # If the app is running on an EC2 instance on AWS, then import different cache settings
    if AWS:
        from .cache import *
else:
    from .local import *
