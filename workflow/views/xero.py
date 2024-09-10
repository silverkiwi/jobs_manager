import uuid
from urllib.parse import urlencode, quote

from django.shortcuts import redirect, render
from django.conf import settings
from django.urls import reverse
from xero_python.api_client import ApiClient, Configuration
from xero_python.accounting import AccountingApi
import os
import logging
from xero_python.identity import IdentityApi
from xero_python.api_client.oauth2 import OAuth2Token

import uuid
from django.shortcuts import redirect, render
from django.conf import settings
from xero_python.api_client import ApiClient, Configuration
from xero_python.api_client.oauth2 import TokenApi
import os

import logging

logger = logging.getLogger(__name__)


# Store token (simple storage in os.environ for this example)
def store_token(token):
    os.environ['XERO_ACCESS_TOKEN'] = token['access_token']

# Retrieve token
def get_token():
    return os.environ.get('XERO_ACCESS_TOKEN')

# Initialize Xero API client
def get_xero_client():
    config = Configuration(debug=settings.DEBUG)
    api_client = ApiClient(configuration=config)
    return api_client

# Xero Authentication (Step 1: Redirect user to Xero OAuth2 login)
def xero_authenticate(request):
    # Generate UUID for the state parameter
    state = str(uuid.uuid4())

    # Save state in session for later verification (optional step to prevent CSRF)
    request.session['oauth_state'] = state

    # Generate the callback URL (similar to Flask's url_for with _external=True)
    redirect_url = request.build_absolute_uri(reverse('xero_oauth_callback')).replace("http://", "https://")
    logger.info(f"Redirect URL before fix: {redirect_url}")


    # Properly encode the redirect_uri

    # Log the relevant data using logging
    logger.info(f"Redirect URL before encoding: {redirect_url}")
    logger.info(f"State: {state}")
    logger.info(f"Client ID: {settings.XERO_CLIENT_ID}")
    logger.info(f"Redirect URI: {settings.XERO_REDIRECT_URI}")

    # Manually construct the authorization URL (aligning with the xero.authorize approach in Flask)
    query_params = {
        'response_type': 'code',
        'client_id': settings.XERO_CLIENT_ID,
        'redirect_uri': redirect_url,
        'scope': ' '.join(["openid", "profile", "email", "accounting.transactions", "offline_access"]),
        'state': state
    }
    authorization_url = f"https://login.xero.com/identity/connect/authorize?{urlencode(query_params)}"

    # Log the final authorization URL
    logger.info(f"Authorization URL: {authorization_url}")

    # Redirect the user to the Xero login page
    return redirect(authorization_url)

# Xero OAuth Callback (Step 2: Handle callback from Xero and exchange code for token)
def xero_oauth_callback(request):
    # Initialize API client
    config = Configuration(debug=settings.DEBUG)
    api_client = ApiClient(configuration=config)

    oauth2_token = OAuth2Token(
        client_id=settings.XERO_CLIENT_ID,
        client_secret=settings.XERO_CLIENT_SECRET
    )

    # Retrieve the authorization code and state from the callback
    code = request.GET.get('code')
    state = request.GET.get('state')

    # Validate the state to prevent CSRF attacks
    if state != request.session.get('oauth_state'):
        return render(request, 'workflow/xero_auth_error.html', {"error_message": "State does not match."})

    try:
        # Get the OAuth2 token using the authorization code
        token_response = api_client.get_oauth2_token(
            client_id=settings.XERO_CLIENT_ID,
            client_secret=settings.XERO_CLIENT_SECRET,
            grant_type='authorization_code',
            code=code,
            redirect_uri=settings.XERO_REDIRECT_URI
        )

        # Update the OAuth2 token object with the token response
        oauth2_token.update_token(**token_response)
    except Exception as e:
        return render(request, 'workflow/xero_auth_error.html', {"error_message": str(e)})

    # Store the token securely
    store_token(oauth2_token.token)

    # Retrieve tenant information using the IdentityApi
    identity_api = IdentityApi(api_client)
    try:
        tenants = identity_api.get_connections()
        # Process tenants as needed
    except Exception as e:
        return render(request, 'workflow/xero_auth_error.html', {"error_message": str(e)})

    return redirect('xero_connection_success')

# Xero connection success view
def xero_connection_success(request):
    return render(request, 'workflow/xero_connection_success.html')

# Error handling view for OAuth
def xero_auth_error(request):
    return render(request, 'workflow/xero_auth_error.html')

# Get Xero contacts
def get_xero_contacts(request):
    token = get_token()
    if not token:
        return redirect('xero_authenticate')

    api_client = get_xero_client()
    api_client.set_oauth2_token(token)
    accounting_api = AccountingApi(api_client)

    # Fetch contacts
    try:
        contacts = accounting_api.get_contacts()
        return render(request, 'workflow/xero_contacts.html', {'contacts': contacts})
    except Exception as e:
        return redirect('xero_auth_error')

# Refresh Xero OAuth Token (when token expires)
def refresh_xero_token(request):
    token = get_token()
    if not token:
        return redirect('xero_authenticate')

    api_client = get_xero_client()
    token_api = TokenApi(api_client)

    # Refresh the token
    try:
        refreshed_token = token_api.refresh_token(token)
        store_token(refreshed_token.to_dict())
        return redirect('xero_get_contacts')
    except Exception as e:
        return redirect('xero_auth_error')
