# workflow/xero/xero.py
import logging
import requests

from urllib.parse import urlencode

from typing import Dict, Any, cast, Optional
from datetime import datetime, timezone

from django.core.cache import cache
from django.conf import settings

from xero_python.api_client import ApiClient, Configuration
from xero_python.api_client.oauth2 import OAuth2Token, TokenApi

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

@api_client.oauth2_token_getter
def get_token_internal() -> Optional[Dict[str, Any]]:
    token = cache.get("xero_oauth2_token")
    if token is None:
        logger.info("No OAuth2 token found in cache.")
        return None  # Return None instead of raising an exception
    token_dict = cast(Dict[str, Any], token)
    logger.info(f"Token retrieved: {token_dict}")
    return token_dict

def get_token() -> Dict[str, Any]:
    """Auto-refresh expired tokens"""
    token = get_token_internal()
    if token is None:
        return None

    expires_at = token.get('expires_at')
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
    authorization_url = f"https://login.xero.com/identity/connect/authorize?{urlencode(query_params)}"
    return authorization_url

# OAuth callback: exchange code for token and return result
def exchange_code_for_token(code: str, state: Optional[str], session_state: str) -> Dict[str, Any]:
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

    if not token_data or 'access_token' not in token_data:
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

