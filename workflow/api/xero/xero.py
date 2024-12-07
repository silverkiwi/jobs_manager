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

api_client = ApiClient(
    Configuration(
        oauth2_token=OAuth2Token(
            client_id=settings.XERO_CLIENT_ID,
            client_secret=settings.XERO_CLIENT_SECRET,
        ),
    ),
)

_refresh_lock = threading.Lock()


def get_token_id_api_client(access_token: str) -> IdentityApi:
    temp_oauth2_token = OAuth2Token(
        client_id=settings.XERO_CLIENT_ID,
        client_secret=settings.XERO_CLIENT_SECRET,
    )
    temp_oauth2_token.update_token({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': 1800,
        'scope': ' '.join(XERO_SCOPES)
    })
    temp_api_client = ApiClient(Configuration(oauth2_token=temp_oauth2_token))
    return IdentityApi(temp_api_client)


def get_tenant_id_from_connections(access_token: str) -> str:
    identity_api = get_token_id_api_client(access_token)
    connections = identity_api.get_connections()
    if not connections:
        raise Exception("No Xero tenants found.")
    return connections[0].tenant_id


@api_client.oauth2_token_saver
def store_token(token: Dict[str, Any]) -> None:
    if not token:
        raise Exception("Invalid token: token is None or empty.")

    # Remove fields that are not part of the OAuth2 specification for the SDK
    token.pop("xero_tenant_id", None)

    # Ensure required fields for update_token()
    # If any are missing, set a default or raise an error
    if "access_token" not in token:
        raise Exception("The token must contain an 'access_token'.")

    if "token_type" not in token:
        token["token_type"] = "Bearer"

    if "expires_in" not in token:
        # Provide a default expires_in if not present (30 minutes)
        token["expires_in"] = 1800

    if "scope" not in token:
        # Use the known set of scopes if scope is missing
        token["scope"] = " ".join(XERO_SCOPES)

    # Calculate expires_at based on expires_in
    expires_at_dt = datetime.now(timezone.utc) + timedelta(seconds=token["expires_in"])
    token["expires_at"] = int(expires_at_dt.timestamp())

    # Store the token in cache for faster future access
    cache.set("xero_oauth2_token", token)
    expires_at = datetime.fromtimestamp(token["expires_at"], tz=timezone.utc)

    # Retrieve the tenant_id from the database
    # It must already be set after initial authorization
    token_instance = XeroToken.objects.first()
    if not token_instance:
        # If this occurs, something went wrong during initial auth/token setup
        raise Exception("No tenant_id found in the database. Token storage logic failed.")

    tenant_id = token_instance.tenant_id

    # Update or create the database record with the new token details
    XeroToken.objects.update_or_create(
        tenant_id=tenant_id,
        defaults={
            "token_type": token["token_type"],
            "access_token": token["access_token"],
            "refresh_token": token.get("refresh_token", ""),
            "expires_at": expires_at,
        },
    )


@api_client.oauth2_token_getter
def get_token_internal() -> Optional[Dict[str, Any]]:
    token = cache.get("xero_oauth2_token")
    if token is not None:
        # Ensure required fields are present
        if "access_token" not in token:
            raise Exception("Stored token missing access_token.")

        if "token_type" not in token:
            token["token_type"] = "Bearer"

        if "expires_in" not in token:
            token["expires_in"] = 1800

        if "scope" not in token:
            token["scope"] = " ".join(XERO_SCOPES)

        return token

    # If not in cache, check DB
    try:
        token_instance = XeroToken.get_instance()
        token = {
            "access_token": token_instance.access_token,
            "refresh_token": token_instance.refresh_token,
            "token_type": token_instance.token_type or "Bearer",
            "expires_in": 1800,
            "scope": " ".join(XERO_SCOPES),
            "expires_at": int(token_instance.expires_at.timestamp()),
        }
        cache.set("xero_oauth2_token", token)
        return token
    except XeroToken.DoesNotExist:
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


def get_token() -> Optional[Dict[str, Any]]:
    token = get_token_internal()
    if token is None:
        return None

    expires_at = token.get("expires_at")
    if expires_at:
        expires_at_datetime = datetime.fromtimestamp(expires_at, tz=timezone.utc)
        if datetime.now(timezone.utc) > expires_at_datetime:
            with _refresh_lock:
                token = get_token_internal()
                if token is None:
                    return None
                new_expires_at = token.get("expires_at")
                if new_expires_at:
                    new_expires_at_datetime = datetime.fromtimestamp(new_expires_at,
                                                                     tz=timezone.utc)
                    if datetime.now(timezone.utc) > new_expires_at_datetime:
                        refreshed = refresh_token()
                        if refreshed:
                            token = refreshed
                        else:
                            logger.error("Failed to refresh token.")
                            return None
                else:
                    logger.error("Token missing expires_at after lock check.")
                    return None
    return token


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
    token_data = response.json()

    if not token_data or "access_token" not in token_data:
        logger.error("Token exchange failed: No valid token data received.")
        return {"error": "Token exchange failed. No valid token received."}

    token_data.pop("xero_tenant_id", None)
    store_token(token_data)

    xero_tenant_id = get_tenant_id_from_connections(token_data["access_token"])
    expires_at = datetime.fromtimestamp(token_data["expires_at"], tz=timezone.utc)

    XeroToken.objects.update_or_create(
        tenant_id=xero_tenant_id,
        defaults={
            "token_type": token_data["token_type"],
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"],
            "expires_at": expires_at,
        },
    )

    return {"success": True}


def refresh_token() -> Optional[Dict[str, Any]]:
    token = get_token_internal()
    if not token or "refresh_token" not in token:
        logger.error("No valid token to refresh.")
        return None

    token_api = TokenApi(api_client)
    refreshed_token = token_api.refresh_token(token)
    refreshed_dict = refreshed_token.to_dict()
    store_token(refreshed_dict)
    return refreshed_dict
