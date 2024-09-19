# workflow/xero/xero.py
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, cast
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.cache import cache
from xero_python.api_client import ApiClient, Configuration
from xero_python.api_client.oauth2 import OAuth2Token, TokenApi
from xero_python.identity import IdentityApi

from workflow.models.xero_token import XeroToken

logger = logging.getLogger(__name__)

# Initialize Xero API client (same as original)
api_client = ApiClient(
    Configuration(
        oauth2_token=OAuth2Token(
            client_id=settings.XERO_CLIENT_ID,
            client_secret=settings.XERO_CLIENT_SECRET,
        ),
    ),
)


@api_client.oauth2_token_saver
def store_token(token: Dict[str, Any]) -> None:
    if not token:
        raise Exception("Invalid token: token is None or empty.")
    cache.set("xero_oauth2_token", token)
    expires_in = token.get("expires_in")
    if expires_in:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        token['expires_at'] = int(expires_at.timestamp())  # Store as a timestamp

    expires_at = datetime.fromtimestamp(token['expires_at'], tz=timezone.utc)
    xero_tenant_id = token.get("xero_tenant_id")
    XeroToken.objects.update_or_create(
        tenant_id=get_tenant_id(),
        defaults={
            'token_type': token['token_type'],
            'access_token': token['access_token'],
            'refresh_token': token['refresh_token'],
            'expires_at': expires_at
        })


@api_client.oauth2_token_getter
def get_token_internal() -> Optional[Dict[str, Any]]:
    # Try to get the token from the cache first
    token = cache.get("xero_oauth2_token")
    if token is not None:
        logger.info("Token retrieved from cache.")
        return token

    # If not found in cache, check the database
    try:
        token_instance = XeroToken.objects.get(tenant_id='your_tenant_id')  # Replace with your tenant_id logic
        token = {
            'token_type': token_instance.token_type,
            'access_token': token_instance.access_token,
            'refresh_token': token_instance.refresh_token,
            'expires_at': int(token_instance.expires_at.timestamp()),
            'xero_tenant_id': token_instance.tenant_id
        }

        # Cache the token after retrieving it from the database for faster future access
        cache.set("xero_oauth2_token", token)

        logger.info(f"Token retrieved from database and cached: {token}")
        return token

    except XeroToken.DoesNotExist:
        logger.info("No OAuth2 token found in database.")
        return None

def get_tenant_id() -> str:
    token_instance = XeroToken.objects.first()
    if token_instance is None:
        identity_api = IdentityApi(api_client)
        connections = identity_api.get_connections()
        if not connections:
            raise Exception("No Xero tenants found.")
        xero_tenant_id = connections[0].tenant_id
    else:
        xero_tenant_id = token_instance.tenant_id

    return xero_tenant_id

def get_token() -> Dict[str, Any]:
    """Auto-refresh expired tokens"""
    token = get_token_internal()
    if token is None:
        return None

    expires_at = token.get("expires_at")
    if expires_at:
        expires_at_datetime = datetime.fromtimestamp(expires_at, tz=timezone.utc)

        if datetime.now(timezone.utc) > expires_at_datetime:
            token = refresh_token(token)
            store_token(token)

    return token


# OAuth Scopes
XERO_SCOPES = [
    "offline_access",
    "openid",
    "profile",
    "email",
    "accounting.contacts",
    "accounting.transactions",
    "accounting.reports.read",
    "accounting.settings",
]


# Xero Authentication URL builder (returns the URL)
def get_authentication_url(state: str) -> str:
    query_params: Dict[str, str] = {
        "response_type": "code",
        "client_id": settings.XERO_CLIENT_ID,
        "redirect_uri": settings.XERO_REDIRECT_URI,
        "scope": " ".join(XERO_SCOPES),
        "state": state,
    }
    authorization_url = (
        f"https://login.xero.com/identity/connect/authorize?{urlencode(query_params)}"
    )
    return authorization_url


# OAuth callback: exchange code for token and return result
def exchange_code_for_token(
    code: str, state: Optional[str], session_state: str
) -> Dict[str, Any]:
    if state != session_state:
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

    # Parse and store token
    token_data = response.json()

    if not token_data or "access_token" not in token_data:
        logger.error("Token exchange failed: No valid token data received.")
        return {"error": "Token exchange failed. No valid token received."}

    store_token(token_data)
    return {"success": True}


def refresh_token() -> Optional[Dict[str, Any]]:
    token = get_token_internal()
    if not token:
        return None

    token_api = TokenApi(api_client)
    refreshed_token = token_api.refresh_token(token)
    store_token(refreshed_token.to_dict())
    return refreshed_token.to_dict()
