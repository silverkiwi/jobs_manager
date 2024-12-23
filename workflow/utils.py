from django.contrib.messages import get_messages


def extract_messages(request):
    """
    Extracts messages from the request object and returns them as a list of dictionaries.
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


def get_rate_type_label(multiplier):
    """
    Converts a pay rate multiplier to its corresponding label.

    Args:
        multiplier (float or str): The pay rate multiplier value (0.0, 1.0, 1.5, or 2.0)

    Returns:
        str: The label corresponding to the multiplier:
            - 'Unpaid' for 0.0
            - 'Ord' (Ordinary) for 1.0 
            - 'Ovt' (Overtime) for 1.5
            - 'Dt' (Double Time) for 2.0
            - 'Ord' as default for any other value

    Examples:
        >>> get_rate_type_label(1.5)
        'Ovt'
        >>> get_rate_type_label(0.0) 
        'Unpaid'
    """

    rate_map = {
        0.0: 'Unpaid',
        1.0: 'Ord',
        1.5: 'Ovt',
        2.0: 'Dt'
    }
    
    return rate_map.get(float(multiplier), 'Ord')  # Default to 'Ord' if not found
