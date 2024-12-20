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
