from datetime import timezone
import uuid
from zoneinfo import ZoneInfo
from django.contrib.messages import get_messages
import logging


logger = logging.getLogger(__name__)

def extract_messages(request):
    """
    Extracts messages from the request object and returns them as a list of
    dictionaries.
    Each dictionary contains the message level tag and the message text.

    Args:
        request: The HTTP request object containing the messages

    Returns:
        list: A list of dictionaries, where each dictionary has:
            - level (str): The message level tag (e.g. 'info', 'error')
            - message (str): The message text
    """

    return [
        {"level": message.level_tag, "message": message.message}
        for message in get_messages(request)
    ]

def is_valid_uuid(value: str) -> bool:
    """Check if the given string is a valid UUID."""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError):
        return False

def get_nz_tz() -> timezone | ZoneInfo:
    """
    Gets the New Zealand timezone object using either zoneinfo or pytz.

    Returns:
        timezone | ZoneInfo: A timezone object for Pacific/Auckland,
        using ZoneInfo if available (Python 3.9+) or falling back to pytz
    """
    try:
        from zoneinfo import ZoneInfo
        nz_timezone = ZoneInfo('Pacific/Auckland')
    except ImportError:
        import pytz
        nz_timezone = pytz.timezone('Pacific/Auckland')
    return nz_timezone

def get_machine_id(path="/etc/machine-id"):
    """
    Reads the machine ID from the specified path.
    Defaults to /etc/machine-id for Linux systems.
    """
    try:
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.warning(f"Machine ID file not found at {path}. Cannot determine production environment based on machine ID.")
        return None
    except Exception as e:
        logger.error(f"Error reading machine ID file {path}: {e}")
        return None
    