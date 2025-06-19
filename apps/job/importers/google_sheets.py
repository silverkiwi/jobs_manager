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


def copy_file(template_id: str, name: str, parent_id: Optional[str] = None, make_public_editable: bool = True) -> str:
    """
    Copy a file in Google Drive and optionally set public edit permissions.
    
    By default, copied files are given "anyone with the link can edit" permissions
    to enable easy sharing and collaboration. This is ideal for quote spreadsheets
    that need to be accessible to clients or external collaborators.
    
    Args:
        template_id: Source file ID to copy
        name: Name for the copied file
        parent_id: Optional parent folder ID
        make_public_editable: If True (default), grants "anyone with link can edit" permissions
        
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
        
        # Set public edit permissions if requested
        if make_public_editable:
            _set_public_edit_permissions(copied_id)
        
        logger.info(f"Copied file '{name}' with ID: {copied_id}")
        return copied_id
        
    except HttpError as e:        raise RuntimeError(f"Failed to copy file '{name}': {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error copying file '{name}': {str(e)}")


def _set_public_edit_permissions(file_id: str) -> None:
    """
    Set public edit permissions on a Google Drive file.
    Grants "anyone with the link can edit" access.
    
    Args:
        file_id: Google Drive file ID
        
    Raises:
        RuntimeError: If setting permissions fails
    """
    try:
        drive_service = _svc('drive', 'v3')
        
        permission = {
            'type': 'anyone',
            'role': 'writer'
        }
        
        drive_service.permissions().create(
            fileId=file_id,
            body=permission
        ).execute()
        
        logger.info(f"Set public edit permissions for file: {file_id}")
        
    except HttpError as e:
        logger.warning(f"Failed to set public permissions for file {file_id}: {e.reason}")
        # Don't raise - this is not critical for file functionality
    except Exception as e:
        logger.warning(f"Unexpected error setting permissions for file {file_id}: {str(e)}")
        # Don't raise - this is not critical for file functionality


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


def copy_template_for_job(job) -> tuple[str, str]:
    """
    Copy a quote template for a specific job.
    
    Creates a "Jobs Manager" folder if it doesn't exist, then copies the template
    spreadsheet with a name following the pattern: "Job {job_number} - {job_name}"
    
    Args:
        job: Job instance with job_number, name, and company_defaults
        
    Returns:
        tuple[str, str]: (file_id, web_url) of the copied spreadsheet
        
    Raises:
        RuntimeError: If template copy fails or company defaults missing
    """
    try:
        from apps.client.models import CompanyDefaults
        
        # Get company defaults for the template
        company_defaults = CompanyDefaults.get_current()
        if not company_defaults or not company_defaults.master_quote_template_id:
            raise RuntimeError("No master quote template configured in company defaults")
        
        template_id = extract_file_id(company_defaults.master_quote_template_id)
        
        # Create or find "Jobs Manager" folder
        folder_id = _get_or_create_jobs_manager_folder()
        
        # Generate file name
        file_name = f"Job {job.job_number} - {job.name}"
        
        # Copy template
        copied_file_id = copy_file(
            template_id=template_id,
            name=file_name,
            parent_id=folder_id,
            make_public_editable=True
        )
        
        # Generate web URL
        web_url = f"https://docs.google.com/spreadsheets/d/{copied_file_id}/edit"
        
        logger.info(f"Created quote spreadsheet for job {job.job_number}: {web_url}")
        return copied_file_id, web_url
        
    except Exception as e:
        logger.error(f"Failed to copy template for job {job.job_number}: {str(e)}")
        raise RuntimeError(f"Failed to copy template: {str(e)}")


def _get_or_create_jobs_manager_folder() -> str:
    """
    Get or create the "Jobs Manager" folder in Google Drive.
    
    Returns:
        str: Folder ID
    """
    try:
        drive_service = _svc('drive', 'v3')
        
        # Search for existing "Jobs Manager" folder
        query = "name='Jobs Manager' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        
        folders = results.get('files', [])
        
        if folders:
            folder_id = folders[0]['id']
            logger.debug(f"Found existing Jobs Manager folder: {folder_id}")
            return folder_id
        
        # Create new folder
        folder_id = create_folder("Jobs Manager")
        logger.info(f"Created Jobs Manager folder: {folder_id}")
        return folder_id
        
    except Exception as e:
        logger.error(f"Failed to get/create Jobs Manager folder: {str(e)}")
        raise RuntimeError(f"Failed to access Jobs Manager folder: {str(e)}")


def populate_sheet_from_costset(sheet_id: str, costset) -> None:
    """
    Populate a Google Sheet with data from a CostSet.
    
    Uses Google Sheets API batch_update to efficiently write cost line data to the spreadsheet.
    Maps cost line fields to specific columns:
    - Column B: Quantity
    - Column C: Description
    - Column D: Labour minutes (for time entries)
    - Column K: Unit cost (for material entries)
    
    Args:
        sheet_id: Google Sheets file ID
        costset: CostSet instance with cost_lines
        
    Raises:
        RuntimeError: If sheet update fails
    """
    try:
        sheets_service = _svc('sheets', 'v4')
        
        # Prepare batch update requests
        requests = []
        
        # Process each cost line
        for idx, cost_line in enumerate(costset.cost_lines.all()):
            row = idx + 2  # Start from row 2 (assuming row 1 is headers)
            
            # Common fields - Quantity (Column B)
            requests.append({
                'updateCells': {
                    'range': {
                        'sheetId': 0,  # First sheet
                        'startRowIndex': row - 1,
                        'endRowIndex': row,
                        'startColumnIndex': 1,  # Column B (0-based)
                        'endColumnIndex': 2
                    },
                    'rows': [{
                        'values': [{
                            'userEnteredValue': {'numberValue': float(cost_line.quantity)}
                        }]
                    }],
                    'fields': 'userEnteredValue'
                }
            })
            
            # Description (Column C)
            requests.append({
                'updateCells': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': row - 1,
                        'endRowIndex': row,
                        'startColumnIndex': 2,  # Column C (0-based)
                        'endColumnIndex': 3
                    },
                    'rows': [{
                        'values': [{
                            'userEnteredValue': {'stringValue': cost_line.desc or ""}
                        }]
                    }],
                    'fields': 'userEnteredValue'
                }
            })
            
            # Type-specific fields
            if cost_line.kind == 'time':
                # Labour minutes (Column D)
                labour_minutes = cost_line.meta.get('labour_minutes', 0) if cost_line.meta else 0
                requests.append({
                    'updateCells': {
                        'range': {
                            'sheetId': 0,
                            'startRowIndex': row - 1,
                            'endRowIndex': row,
                            'startColumnIndex': 3,  # Column D (0-based)
                            'endColumnIndex': 4
                        },
                        'rows': [{
                            'values': [{
                                'userEnteredValue': {'numberValue': float(labour_minutes)}
                            }]
                        }],
                        'fields': 'userEnteredValue'
                    }
                })
            elif cost_line.kind == 'material':
                # Unit cost (Column K)
                requests.append({
                    'updateCells': {
                        'range': {
                            'sheetId': 0,
                            'startRowIndex': row - 1,
                            'endRowIndex': row,
                            'startColumnIndex': 10,  # Column K (0-based)
                            'endColumnIndex': 11
                        },
                        'rows': [{
                            'values': [{
                                'userEnteredValue': {'numberValue': float(cost_line.unit_cost)}
                            }]
                        }],
                        'fields': 'userEnteredValue'
                    }
                })
        
        # Execute batch update if we have requests
        if requests:
            body = {'requests': requests}
            
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body=body
            ).execute()
            logger.info(f"Updated {len(requests)} cells in sheet {sheet_id} from cost set {costset.id}")
        else:
            logger.info(f"No cost lines to populate in sheet {sheet_id}")
    
    except Exception as e:
        logger.error(f"Failed to populate sheet {sheet_id}: {str(e)}")
        raise RuntimeError(f"Failed to populate sheet: {str(e)}")
