import logging
import uuid
from typing import Any, Dict, List, Optional, cast
from urllib.parse import urlencode

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from xero_python.accounting import AccountingApi  # type: ignore
from xero_python.api_client import ApiClient  # type: ignore
from xero_python.api_client.oauth2 import TokenApi  # type: ignore
from xero_python.identity import IdentityApi  # type: ignore

logger = logging.getLogger(__name__)

XERO_SCOPES = [
    "offline_access",
    "openid",
    "profile",
    "email",
    "accounting.transactions",
    "accounting.reports.read",
]


# Store token (simple storage in os.environ for this example)
def store_token(token: Dict[str, Any]) -> None:
    if not token:
        raise Exception("Invalid token: token is None or empty.")
    cache.set("xero_oauth2_token", token)


# Retrieve token
def get_token() -> Dict[str, Any]:
    token = cache.get("xero_oauth2_token")
    if token is None:
        raise Exception("No OAuth2 token found.")
    token_dict = cast(Dict[str, Any], token)
    return token_dict


# Initialize Xero API client
def get_api_client() -> ApiClient:
    return ApiClient(oauth2_token_getter=get_token, oauth2_token_saver=store_token)


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
    api_client: ApiClient = get_api_client()
    authorization_url: str = api_client.auth_code_url(
        client_id=settings.XERO_CLIENT_ID,
        redirect_uri=settings.XERO_REDIRECT_URI,
        scope=" ".join(XERO_SCOPES),
    )
    return redirect(authorization_url)


# Callback view after user authorizes with Xero
def xero_oauth_callback(request: HttpRequest) -> HttpResponse:
    api_client: ApiClient = get_api_client()

    code: Optional[str] = request.GET.get("code")
    state: Optional[str] = request.GET.get("state")

    if state != request.session.get("oauth_state"):
        return render(
            request,
            "workflow/xero_auth_error.html",
            {"error_message": "State does not match."},
        )

    try:
        token_response: Dict[str, Any] = api_client.generate_token(
            client_id=settings.XERO_CLIENT_ID,
            client_secret=settings.XERO_CLIENT_SECRET,
            grant_type="authorization_code",
            code=code,
            redirect_uri=settings.XERO_REDIRECT_URI,
        )

        store_token(token_response)
    except Exception as e:
        return render(
            request, "workflow/xero_auth_error.html", {"error_message": str(e)}
        )

    identity_api: IdentityApi = IdentityApi(api_client)
    try:
        tenants: List[Any] = identity_api.get_connections()
        logger.info(f"Tenants: {tenants}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return render(
            request, "workflow/xero_auth_error.html", {"error_message": str(e)}
        )

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

    api_client: ApiClient = get_api_client()
    api_client.set_oauth2_token(token)
    accounting_api: AccountingApi = AccountingApi(api_client)

    try:
        contacts: Any = accounting_api.get_contacts()
        return render(request, "workflow/xero_contacts.html", {"contacts": contacts})
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return redirect("xero_auth_error")


# Refresh Xero OAuth Token (when token expires)
def refresh_xero_token(request: HttpRequest) -> HttpResponse:
    token: Dict[str, Any] = get_token()
    if not token:
        return redirect("xero_authenticate")

    api_client: ApiClient = get_api_client()
    token_api: TokenApi = TokenApi(api_client)

    try:
        refreshed_token: Any = token_api.refresh_token(token)
        store_token(refreshed_token.to_dict())
        return redirect("xero_get_contacts")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return redirect("xero_auth_error")
