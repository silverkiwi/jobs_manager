import os
from dotenv import load_dotenv


load_dotenv(BASE_DIR / ".env")
ENVIRONMENT = os.getenv("DJANGO_ENV", "local")

if ENVIRONMENT == "production":
    from .production import *
else:
    from .local import *
