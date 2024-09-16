import logging
import uuid
from typing import Any, Dict, Optional, cast
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from xero_python.accounting import AccountingApi  # type: ignore
from xero_python.api_client import ApiClient, Configuration  # type: ignore
from xero_python.api_client.oauth2 import OAuth2Token, TokenApi  # type: ignore
from xero_python.identity import IdentityApi  # type: ignore

logger = logging.getLogger(__name__)

XERO_SCOPES = [
    "offline_access",
    "openid",
    "profile",
    "email",
    "accounting.contacts",
    "accounting.transactions",
    "accounting.reports.read",
]


# Initialize Xero API client
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
def get_token() -> Dict[str, Any]:
    token = cache.get("xero_oauth2_token")
    if token is None:
        raise Exception("No OAuth2 token found.")
    token_dict = cast(Dict[str, Any], token)
    return token_dict


# Xero Authentication (Step 1: Redirect user to Xero OAuth2 login)
def xero_authenticate(request: HttpRequest) -> HttpResponse:
    state: str = str(uuid.uuid4())

    request.session["oauth_state"] = state
    redirect_url = settings.XERO_REDIRECT_URI

    logger.info(f"State: {state}")
    logger.info(f"Client ID: {settings.XERO_CLIENT_ID}")
    logger.info(f"Redirect URI: {settings.XERO_REDIRECT_URI}")

    query_params: Dict[str, str] = {
        "response_type": "code",
        "client_id": settings.XERO_CLIENT_ID,
        "redirect_uri": redirect_url,
        "scope": " ".join(XERO_SCOPES),
        "state": state,
    }
    authorization_url: str = (
        f"https://login.xero.com/identity/connect/authorize?{urlencode(query_params)}"
    )

    logger.info(f"Authorization URL: {authorization_url}")

    return redirect(authorization_url)


# Authorization view (redirect user to Xero's authorization URL)
def xero_authorize(request: HttpRequest) -> HttpResponse:
    authorization_url: str = api_client.auth_code_url(
        client_id=settings.XERO_CLIENT_ID,
        redirect_uri=settings.XERO_REDIRECT_URI,
        scope=" ".join(XERO_SCOPES),
    )
    return redirect(authorization_url)


# Callback view after user authorizes with Xero
def xero_oauth_callback(request: HttpRequest) -> HttpResponse:
    code: Optional[str] = request.GET.get("code")
    state: Optional[str] = request.GET.get("state")

    if state != request.session.get("oauth_state"):
        return render(
            request,
            "workflow/xero_auth_error.html",
            {"error_message": "State does not match."},
        )

    # Exchange authorization code for access token
    token_url = "https://identity.xero.com/connect/token"
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.XERO_REDIRECT_URI,
        "client_id": settings.XERO_CLIENT_ID,
        "client_secret": settings.XERO_CLIENT_SECRET,
    }

    # Send a POST request to Xero's token endpoint
    token_response = requests.post(token_url, data=token_data)
    token_response.raise_for_status()

    # Parse the token response
    token_data = token_response.json()
    store_token(token_data)

    return redirect("xero_connection_success")


# Xero connection success view
def xero_connection_success(request: HttpRequest) -> HttpResponse:
    return render(request, "workflow/xero_connection_success.html")


# Error handling view for OAuth
def xero_auth_error(request: HttpRequest) -> HttpResponse:
    return render(request, "workflow/xero_auth_error.html")


# Get Xero contacts
def get_xero_contacts(request: HttpRequest) -> HttpResponse:
    token: Dict[str, Any] = get_token()
    if not token:
        return redirect("xero_authenticate")

    accounting_api: AccountingApi = AccountingApi(api_client)
    # Get Xero tenant ID
    identity_api: IdentityApi = IdentityApi(api_client)
    connections = identity_api.get_connections()
    if not connections:
        raise Exception("No Xero tenants found.")

    xero_tenant_id = connections[0].tenant_id

    # Fetch contacts using the tenant ID
    contacts: Any = accounting_api.get_contacts(xero_tenant_id)
    return render(
        request, "workflow/xero_contacts.html", {"contacts": contacts.contacts}
    )


# Refresh Xero OAuth Token (when token expires)
def refresh_xero_token(request: HttpRequest) -> HttpResponse:
    token: Dict[str, Any] = get_token()
    if not token:
        return redirect("xero_authenticate")

    token_api: TokenApi = TokenApi(api_client)

    try:
        refreshed_token: Any = token_api.refresh_token(token)
        store_token(refreshed_token.to_dict())
        return redirect("xero_get_contacts")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return redirect("xero_auth_error")

