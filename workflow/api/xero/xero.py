import json
import logging
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

logger = logging.getLogger("xero")

api_client = ApiClient(
    Configuration(
        debug=False,
        oauth2_token=OAuth2Token(
            client_id=settings.XERO_CLIENT_ID,
            client_secret=settings.XERO_CLIENT_SECRET,
        ),
    ),
)


# Helper function for pretty printing JSON/dict objects
def pretty_print(obj):
    return json.dumps(obj, indent=2, sort_keys=True)


@api_client.oauth2_token_getter
def get_token() -> Optional[Dict[str, Any]]:
    """Get token from cache or database."""
    logger.debug("Getting token from cache")
    token = cache.get("xero_token")
    if token:
        logger.debug("Retrieved token from cache")
        return token

    logger.debug("Token not found in cache, checking database")
    db_token = XeroToken.objects.first()
    if not db_token or not db_token.access_token:
        logger.debug("No valid token found in database")
        return None

    if not db_token.expires_at:
        logger.debug("Token in database has no expiry time")
        return None

    # Convert database token to OAuth2Token format
    token = {
        "access_token": db_token.access_token,
        "refresh_token": db_token.refresh_token,
        "token_type": db_token.token_type,
        "expires_at": db_token.expires_at.timestamp(),
        "scope": db_token.scope,
        "expires_in": int((db_token.expires_at - datetime.now(timezone.utc)).total_seconds())
    }

    # Only cache if not expired
    if token["expires_in"] > 0:
        cache.set("xero_token", token, timeout=token["expires_in"])
        logger.debug("Retrieved valid token from database and cached it")
        return token
    
    logger.debug("Token in database is expired")
    return None


@api_client.oauth2_token_saver
def store_token(token: Dict[str, Any]) -> None:
    """Store token in both cache and database."""
    logger.info("Storing token!")

    # For better logs if needed
    token_data = {
        "id_token": token.get("id_token"),
        "access_token": token.get("access_token"),
        "refresh_token": token.get("refresh_token"),
        "expires_in": token.get("expires_in"),
        "token_type": token.get("token_type"),
        "scope": token.get("scope")  # Use scope from token response
    }

    # Get expiry time from Xero's response
    expires_at = None
    if token.get("expires_in"):
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=token["expires_in"])
        token_data["expires_at"] = expires_at.timestamp()

    # Store in cache - use Xero's expires_in for the cache timeout
    cache_timeout = token.get("expires_in", 1740)  # fallback to 29 minutes if not provided
    cache.set("xero_token", token_data, timeout=cache_timeout)

    # Get tenant ID if available
    try:
        tenant_id = get_tenant_id_from_connections()
    except Exception:
        tenant_id = None
        logger.warning("Could not fetch tenant ID when storing token")

    # Store in database
    try:
        xero_token = XeroToken.objects.first()
        if not xero_token:
            xero_token = XeroToken()
        
        xero_token.access_token = token_data["access_token"]
        xero_token.refresh_token = token_data["refresh_token"]
        xero_token.token_type = token_data["token_type"]
        xero_token.expires_at = expires_at
        xero_token.scope = token_data["scope"]  # Use scope from token response
        if tenant_id:
            xero_token.tenant_id = tenant_id
        xero_token.save()
    except Exception as e:
        logger.error(f"Failed to store token in database: {e}")
        # Don't raise - we still have the token in cache

    logger.debug("Token stored successfully in both cache and database.")


def refresh_token() -> Optional[Dict[str, Any]]:
    """Refresh the token using the refresh_token."""
    logger.debug("Attempting to refresh token")
    token = get_token()
    if not token or "refresh_token" not in token:
        logger.debug("No valid token to refresh")
        return None

    logger.debug("Calling token refresh API")
    token_api = TokenApi(api_client)
    refreshed_token = token_api.refresh_token(token)
    refreshed_dict = refreshed_token.to_dict()
    logger.debug(f"Token refreshed successfully: \n{pretty_print(refreshed_dict)}")
    store_token(refreshed_dict)
    return refreshed_dict


def get_valid_token() -> Optional[Dict[str, Any]]:
    """Get a valid token, refreshing if needed."""
    logger.debug("Getting valid token")
    token = get_token()
    if not token:
        logger.debug("No token found")
        return None

    expires_at = token.get("expires_at")
    if expires_at:
        expires_at_datetime = datetime.fromtimestamp(expires_at, tz=timezone.utc)
        if datetime.now(timezone.utc) > expires_at_datetime:
            logger.debug("Token expired, refreshing")
            token = refresh_token()
    logger.debug("Returning valid token!")
    return token


def get_authentication_url(state: str) -> str:
    """Get the URL for initial Xero OAuth."""
    params = {
        "response_type": "code",
        "client_id": settings.XERO_CLIENT_ID,
        "redirect_uri": settings.XERO_REDIRECT_URI,
        "scope": " ".join(settings.XERO_SCOPES),
        "state": state,
    }
    logger.debug(f"Generating authentication URL with params: \n{pretty_print(params)}")
    url = f"https://login.xero.com/identity/connect/authorize?{urlencode(params)}"
    logger.debug(f"Generated URL: {url}")
    return url


def get_tenant_id_from_connections() -> str:
    """Get tenant ID using current token."""
    logger.debug("Getting tenant ID from connections")
    identity_api = IdentityApi(api_client)
    connections = identity_api.get_connections()
    if not connections:
        logger.debug("No Xero tenants found")
        raise Exception("No Xero tenants found.")
    tenant_id = connections[0].tenant_id
    logger.debug(f"Retrieved tenant ID: {tenant_id}")
    return tenant_id


def exchange_code_for_token(code, state, session_state):
    """
    Exchange authorization code for access and refresh tokens from Xero.
    """
    logger.debug(f"Exchanging code for token. Code: {code}, State: {state}")
    url = "https://identity.xero.com/connect/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.XERO_REDIRECT_URI,
        "client_id": settings.XERO_CLIENT_ID,
        "client_secret": settings.XERO_CLIENT_SECRET,
    }

    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        token = response.json()
        logger.debug("Token received!")

        store_token(token)
        logger.debug("Token stored successfully after exchange!")

        return token
    except requests.exceptions.HTTPError as e:
        logger.debug(f"HTTP Error: {response.status_code} - {response.text}")
        raise e
    except Exception as e:
        logger.debug(f"Unexpected error: {str(e)}")
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
        logger.debug("No valid token found")
        raise Exception(
            "No valid Xero token found. Please complete the authorization workflow."
        )

    if (
        not tenant_id
    ):  # Step 3: If tenant ID is missing, fetch it using the current token.
        logger.debug("No tenant ID in cache, fetching from Xero")
        try:
            tenant_id = get_tenant_id_from_connections()
            logger.debug(f"Caching tenant ID: {tenant_id}")
            cache.set(
                "xero_tenant_id", tenant_id
            )  # Cache the tenant ID for future use.
        except Exception as e:
            logger.debug(f"Failed to fetch tenant ID: {str(e)}")
            raise Exception(f"Failed to fetch tenant ID: {str(e)}")

    logger.debug(f"Returning tenant ID: {tenant_id}")
    return tenant_id
