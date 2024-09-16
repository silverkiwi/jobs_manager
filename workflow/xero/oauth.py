# workflow/xero/oauth.py
import requests
from django.conf import settings

from workflow.views.xero_view import api_client


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

def exchange_code_for_token(code: str, state: str, session_state: str):
    # Verify if the state matches
    if state != session_state:
        return {"error": "State does not match."}

    # Prepare data to exchange authorization code for access token
    token_url = "https://identity.xero.com/connect/token"
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.XERO_REDIRECT_URI,
        "client_id": settings.XERO_CLIENT_ID,
        "client_secret": settings.XERO_CLIENT_SECRET,
    }

    # Make the request to get the token
    response = requests.post(token_url, data=token_data)
    response.raise_for_status()  # Keep the original error handling

    # Return the parsed JSON response
    return response.json()
