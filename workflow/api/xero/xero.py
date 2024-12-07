# workflow/xero/xero.py
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.cache import cache
from xero_python.api_client import ApiClient, Configuration
from xero_python.api_client.oauth2 import OAuth2Token, TokenApi
from xero_python.identity import IdentityApi

from workflow.models.xero_token import XeroToken

logger = logging.getLogger(__name__)

# Xero documented token lifespan: 30 minutes (1800 seconds) for short-lived tokens.
# If Xero fails to provide expires_in for some reason, we fallback to 1800.
DEFAULT_EXPIRES_IN = 1800

# Define scopes centrally, so it's easy to adjust them later if needed.
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

_refresh_lock = threading.Lock()

# Decorators must be defined after api_client is created, ensuring the SDK registers them.
@api_client.oauth2_token_getter
def get_token_internal() -> Optional[Dict[str, Any]]:
    """Retrieve the current token from cache or DB.
    Returns a dict with required fields or None if no token is stored."""
    token = cache.get("xero_oauth2_token")
    if token is not None:
        return token

    try:
        token_instance = XeroToken.get_instance()
        # Trusting token_instance fields from initial authorization setup.
        # If we lack any fields from Xero in the DB, consider logging a warning or raising an error.
        expires_in = int((token_instance.expires_at - datetime.now(timezone.utc)).total_seconds())
        if expires_in <= 0:
            # If the token in DB is already expired, we could log or handle differently.
            logger.warning("Token in DB is expired. Consider re-authorizing with Xero.")
            return None

        token = {
            "access_token": token_instance.access_token,
            "refresh_token": token_instance.refresh_token,
            "token_type": token_instance.token_type or "Bearer",
            "expires_in": expires_in,
            "scope": " ".join(XERO_SCOPES),
            "expires_at": int(token_instance.expires_at.timestamp()),
        }
        cache.set("xero_oauth2_token", token)
        return token
    except XeroToken.DoesNotExist:
        # No token stored yet, user needs to authenticate.
        return None

@api_client.oauth2_token_saver
def store_token(token: Dict[str, Any]) -> None:
    """Store and update the token in cache. No DB access here."""
    # Validate required fields
    for required in ("access_token", "token_type", "expires_in", "scope"):
        if required not in token:
            logger.error(f"Missing {required} in Xero token response.")
            raise ValueError(f"Xero token response missing '{required}' field.")

    # Compute expires_at from expires_in
    expires_at_dt = datetime.now(timezone.utc) + timedelta(seconds=token["expires_in"])
    token["expires_at"] = int(expires_at_dt.timestamp())

    # Just cache the token, no DB access
    cache.set("xero_oauth2_token", token)


def get_tenant_id() -> str:
    """Retrieve the tenant_id from the DB. Assumes initial auth completed."""
    token_instance = XeroToken.objects.first()
    if not token_instance:
        logger.error("No tenant_id in DB. Initial authorization likely not done.")
        raise Exception("No tenant_id found in DB.")
    return token_instance.tenant_id

def get_token() -> Optional[Dict[str, Any]]:
    """Get a valid token, refreshing if needed."""
    token = get_token_internal()
    if token is None:
        return None

    expires_at = token.get("expires_at")
    if expires_at:
        expires_at_datetime = datetime.fromtimestamp(expires_at, tz=timezone.utc)
        if datetime.now(timezone.utc) > expires_at_datetime:
            # Token expired; attempt to refresh
            token = refresh_token()
            if not token:
                logger.error("Failed to refresh token after expiration.")
                raise Exception("Token refresh failed.")
        return token


def get_authentication_url(state: str) -> str:
    """Construct the URL to initiate the Xero OAuth flow."""
    query_params: Dict[str, str] = {
        "response_type": "code",
        "client_id": settings.XERO_CLIENT_ID,
        "redirect_uri": settings.XERO_REDIRECT_URI,
        "scope": " ".join(XERO_SCOPES),
        "state": state,
    }
    return f"https://login.xero.com/identity/connect/authorize?{urlencode(query_params)}"

def get_tenant_id_from_connections(access_token: str) -> str:
    # Instead of creating a new ApiClient, just use the main api_client
    identity_api = IdentityApi(api_client)  # uses the main api_client already configured
    connections = identity_api.get_connections()
    if not connections:
        logger.error("No Xero tenants found for the given access_token.")
        raise Exception("No Xero tenants found.")
    return connections[0].tenant_id

def exchange_code_for_token(
    code: str, state: Optional[str], session_state: str
) -> Dict[str, Any]:
    if state != session_state:
        logger.error("State mismatch during OAuth callback.")
        return {"error": "State mismatch"}

    token_url = "https://identity.xero.com/connect/token"
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.XERO_REDIRECT_URI,
        "client_id": settings.XERO_CLIENT_ID,
        "client_secret": settings.XERO_CLIENT_SECRET,
    }

    response = requests.post(token_url, data=token_data)
    response.raise_for_status()
    token_data = response.json()

    if "access_token" not in token_data:
        logger.error("Token exchange failed: No access_token in response.")
        return {"error": "Token exchange failed. No valid token received."}

    token_data.pop("xero_tenant_id", None)

    # Store token in cache
    store_token(token_data)

    # Now fetch tenant_id using the main api_client (no second client needed)
    xero_tenant_id = get_tenant_id_from_connections(token_data["access_token"])
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])

    XeroToken.objects.update_or_create(
        tenant_id=xero_tenant_id,
        defaults={
            "token_type": token_data["token_type"],
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", ""),
            "expires_at": expires_at,
        },
    )

    return {"success": True}

def refresh_token() -> Optional[Dict[str, Any]]:
    """Refresh the token using the refresh_token."""
    token = get_token_internal()
    if not token or "refresh_token" not in token:
        logger.error("No valid token to refresh - missing refresh_token.")
        return None

    token_api = TokenApi(api_client)
    refreshed_token = token_api.refresh_token(token)
    refreshed_dict = refreshed_token.to_dict()
    store_token(refreshed_dict)
    return refreshed_dict
