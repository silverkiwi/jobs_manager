"""
Google Sheets Integration Module

Provides utilities for interacting with Google Sheets and Drive APIs.
Includes functions for:
- Creating folders and copying files
- Extracting file IDs from URLs
- Fetching sheet data as pandas DataFrames
"""

import logging
import os
import re
from typing import Optional, Dict, Any

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings

logger = logging.getLogger(__name__)

# Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets.readonly'
]

# Global credentials - initialized on first use
CREDS = None


def _get_credentials():
    """
    Get Google API credentials from service account file.
    
    Returns:
        service_account.Credentials: Authenticated credentials
        
    Raises:
        RuntimeError: If credentials file not found or invalid
    """
    global CREDS
    
    if CREDS is None:
        try:
            key_file = os.getenv('GSHEETS_KEY_FILE')
            if not key_file:
                raise RuntimeError("GSHEETS_KEY_FILE environment variable not set")
            
            if not os.path.exists(key_file):
                raise RuntimeError(f"Google service account key file not found: {key_file}")
            
            CREDS = service_account.Credentials.from_service_account_file(
                key_file, scopes=SCOPES
            )
            
            logger.info(f"Google API credentials loaded from {key_file}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load Google API credentials: {str(e)}")
    
    return CREDS


def _svc(api: str, version: str):
    """
    Create a Google API service client.
    
    Args:
        api: API name (e.g., 'drive', 'sheets')
        version: API version (e.g., 'v3', 'v4')
        
    Returns:
        googleapiclient.discovery.Resource: Service client
        
    Raises:
        RuntimeError: If service creation fails
    """
    try:
        credentials = _get_credentials()
        service = build(api, version, credentials=credentials, cache_discovery=False)
        logger.debug(f"Created {api} {version} service client")
        return service
        
    except Exception as e:
        raise RuntimeError(f"Failed to create {api} {version} service: {str(e)}")


def extract_file_id(url_or_id: str) -> str:
    """
    Extract Google Drive file ID from URL or return ID if already extracted.
    
    Args:
        url_or_id: Google Drive URL or file ID
        
    Returns:
        str: File ID
        
    Raises:
        RuntimeError: If file ID cannot be extracted
    """
    if not url_or_id:
        raise RuntimeError("URL or ID cannot be empty")
    
    # If it's already a file ID (no slashes or domains), return as-is
    if '/' not in url_or_id and '.' not in url_or_id:
        return url_or_id
    
    # Extract from various Google Drive URL formats
    patterns = [
        r'/file/d/([a-zA-Z0-9-_]+)',  # /file/d/FILE_ID
        r'/spreadsheets/d/([a-zA-Z0-9-_]+)',  # /spreadsheets/d/FILE_ID
        r'id=([a-zA-Z0-9-_]+)',  # ?id=FILE_ID
        r'([a-zA-Z0-9-_]{25,})',  # Fallback: any long alphanumeric string
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            file_id = match.group(1)
            logger.debug(f"Extracted file ID: {file_id}")
            return file_id
    
    raise RuntimeError(f"Could not extract file ID from: {url_or_id}")


def create_folder(name: str, parent_id: Optional[str] = None) -> str:
    """
    Create a folder in Google Drive.
    
    Args:
        name: Folder name
        parent_id: Optional parent folder ID
        
    Returns:
        str: Created folder ID
        
    Raises:
        RuntimeError: If folder creation fails
    """
    try:
        drive_service = _svc('drive', 'v3')
        
        folder_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            folder_metadata['parents'] = [parent_id]
        
        folder = drive_service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()
        
        folder_id = folder.get('id')
        logger.info(f"Created folder '{name}' with ID: {folder_id}")
        return folder_id
        
    except HttpError as e:
        raise RuntimeError(f"Failed to create folder '{name}': {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error creating folder '{name}': {str(e)}")


def copy_file(template_id: str, name: str, parent_id: Optional[str] = None) -> str:
    """
    Copy a file in Google Drive.
    
    Args:
        template_id: Source file ID to copy
        name: Name for the copied file
        parent_id: Optional parent folder ID
        
    Returns:
        str: Copied file ID
        
    Raises:
        RuntimeError: If file copy fails
    """
    try:
        drive_service = _svc('drive', 'v3')
        
        copy_metadata = {'name': name}
        
        if parent_id:
            copy_metadata['parents'] = [parent_id]
        
        copied_file = drive_service.files().copy(
            fileId=template_id,
            body=copy_metadata,
            fields='id'
        ).execute()
        
        copied_id = copied_file.get('id')
        logger.info(f"Copied file '{name}' with ID: {copied_id}")
        return copied_id
        
    except HttpError as e:
        raise RuntimeError(f"Failed to copy file '{name}': {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error copying file '{name}': {str(e)}")


def fetch_sheet_df(sheet_id: str, sheet_range: str = "Primary Details") -> pd.DataFrame:
    """
    Fetch data from a Google Sheet as a pandas DataFrame.
    
    Args:
        sheet_id: Google Sheets file ID
        sheet_range: Sheet range to fetch (default: "Primary Details")
        
    Returns:
        pd.DataFrame: Sheet data
        
    Raises:
        RuntimeError: If data fetch fails
    """
    try:
        sheets_service = _svc('sheets', 'v4')
        
        # Fetch the data
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=sheet_range
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            logger.warning(f"No data found in sheet {sheet_id} range {sheet_range}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        # First row is typically headers
        if len(values) > 1:
            df = pd.DataFrame(values[1:], columns=values[0])
        else:
            # Only headers, no data
            df = pd.DataFrame(columns=values[0])
        
        logger.info(f"Fetched {len(df)} rows from sheet {sheet_id} range {sheet_range}")
        return df
        
    except HttpError as e:
        raise RuntimeError(f"Failed to fetch sheet data: {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error fetching sheet data: {str(e)}")
