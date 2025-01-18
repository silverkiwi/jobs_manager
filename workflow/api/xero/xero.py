import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.cache import cache
from xero_python.api_client import ApiClient, Configuration
from xero_python.api_client.oauth2 import OAuth2Token
from xero_python.identity import IdentityApi
from xero_python.api_client.oauth2 import TokenApi

logger = logging.getLogger(__name__)

XERO_SCOPES = [
    "offline_access",
    "openid", 
    "profile",
    "email",
    "accounting.contacts",
    "accounting.transactions",
    "accounting.reports.read",
    "accounting.settings",
    "accounting.journals.read",
]

api_client = ApiClient(
    Configuration(
        oauth2_token=OAuth2Token(
            client_id=settings.XERO_CLIENT_ID,
            client_secret=settings.XERO_CLIENT_SECRET,
        ),
    ),
)


@api_client.oauth2_token_getter
def get_token() -> Optional[Dict[str, Any]]:
    """Get token from cache."""
    logger.debug("Getting token from cache")
    token = cache.get("xero_token")
    logger.debug(f"Retrieved token: {token}")
    return token


@api_client.oauth2_token_saver
def store_token(token: Dict[str, Any]) -> None:
    """Store token in cache with 29 minute timeout."""
    logger.info(f"Storing token: {token}")
    cache.set("xero_token", token, timeout=1740)  # 29 minutes
    logger.debug("Token stored successfully")


def refresh_token() -> Optional[Dict[str, Any]]:
    """Refresh the token using the refresh_token."""
    logger.info("Attempting to refresh token")
    token = get_token()
    if not token or "refresh_token" not in token:
        logger.error("No valid token to refresh")
        return None

    logger.debug("Calling token refresh API")
    token_api = TokenApi(api_client)
    refreshed_token = token_api.refresh_token(token)
    refreshed_dict = refreshed_token.to_dict()
    logger.debug(f"Token refreshed successfully: {refreshed_dict}")
    store_token(refreshed_dict)
    return refreshed_dict


def get_valid_token() -> Optional[Dict[str, Any]]:
    """Get a valid token, refreshing if needed."""
    logger.debug("Getting valid token")
    token = get_token()
    if not token:
        logger.warning("No token found")
        return None

    expires_at = token.get("expires_at")
    if expires_at:
        expires_at_datetime = datetime.fromtimestamp(expires_at, tz=timezone.utc)
        if datetime.now(timezone.utc) > expires_at_datetime:
            logger.info("Token expired, refreshing")
            token = refresh_token()
    logger.debug(f"Returning valid token: {token}")
    return token


def get_authentication_url(state: str) -> str:
    """Get the URL for initial Xero OAuth."""
    logger.debug(f"Generating authentication URL with state: {state}")
    url = f"https://login.xero.com/identity/connect/authorize?{urlencode({
        'response_type': 'code',
        'client_id': settings.XERO_CLIENT_ID,
        'redirect_uri': settings.XERO_REDIRECT_URI,
        'scope': ' '.join(XERO_SCOPES),
        'state': state,
    })}"
    logger.debug(f"Generated URL: {url}")
    return url


def get_tenant_id_from_connections() -> str:
    """Get tenant ID using current token."""
    logger.debug("Getting tenant ID from connections")
    identity_api = IdentityApi(api_client)
    connections = identity_api.get_connections()
    if not connections:
        logger.error("No Xero tenants found")
        raise Exception("No Xero tenants found.")
    tenant_id = connections[0].tenant_id
    logger.debug(f"Retrieved tenant ID: {tenant_id}")
    return tenant_id


def exchange_code_for_token(code, state, session_state):
    """
    Exchange authorization code for access and refresh tokens from Xero.
    """
    logger.info(f"Exchanging code for token. Code: {code}, State: {state}")
    url = "https://identity.xero.com/connect/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.XERO_REDIRECT_URI,
        "client_id": settings.XERO_CLIENT_ID,
        "client_secret": settings.XERO_CLIENT_SECRET,
    }

    # Log Xero configuration
    logger.debug(f"XERO_REDIRECT_URI: {settings.XERO_REDIRECT_URI}")
    logger.debug(f"XERO_CLIENT_ID: {settings.XERO_CLIENT_ID}")
    logger.debug(f"XERO_CLIENT_SECRET: {settings.XERO_CLIENT_SECRET}")

    try:
        response = requests.post(url, headers=headers, data=data)
        logger.info(f"Requesting token exchange with code: {code} and state: {state}")
        logger.debug(f"Request payload: {data}")
        logger.debug(f"Response: {response.status_code}, {response.json()}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error: {response.status_code} - {response.text}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise e


def get_tenant_id() -> str:
    """
    Retrieve the tenant ID from cache, refreshing or re-authenticating as needed.
    """
    logger.debug("Getting tenant ID")
    tenant_id = cache.get(
        "xero_tenant_id"
    )  # Step 1: Try to retrieve the tenant ID from the cache.
    logger.debug(f"Tenant ID from cache: {tenant_id}")
    
    token = (
        get_valid_token()
    )  # Step 2: Ensure a valid token exists, refreshing if necessary.

    if not token:
        logger.error("No valid token found")
        raise Exception(
            "No valid Xero token found. Please complete the authorization workflow."
        )

    if (
        not tenant_id
    ):  # Step 3: If tenant ID is missing, fetch it using the current token.
        logger.info("No tenant ID in cache, fetching from Xero")
        try:
            tenant_id = get_tenant_id_from_connections()
            logger.debug(f"Caching tenant ID: {tenant_id}")
            cache.set(
                "xero_tenant_id", tenant_id
            )  # Cache the tenant ID for future use.
        except Exception as e:
            logger.error(f"Failed to fetch tenant ID: {str(e)}")
            raise Exception(f"Failed to fetch tenant ID: {str(e)}")

    logger.debug(f"Returning tenant ID: {tenant_id}")
    return tenant_id
