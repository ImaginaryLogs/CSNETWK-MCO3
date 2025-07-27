from src.manager.state import known_peers, posts, dms

def parse_lsnp_messages(raw_message: str) -> dict:
    '''    
    Parses an LSNP-formatted message into a Python dictionary.

    The LSNP (Lightweight Simple Notification Protocol) message should contain
    key-value pairs in the format "Key: Value", separated by newlines.

    Example:
    >>> raw_message = "Type: Request\\nID: 12345\\nPayload: Hello World\\n"
    >>> result = parse_lsnp_messages(raw_message)
    result -> {"Type": "Request", "ID": "12345", "Payload": "Hello World"}

    Args:
        raw_message (str): The raw LSNP message string to parse.

    Returns:
        dict: A dictionary of key-value pairs extracted from the message.
    '''
    lines = raw_message.strip().split('\n')
    message = {}
    for line in lines:
        if line.strip() == '':
            continue
        if ':' in line:
            key, value = line.split(':', 1)
            message[key.strip()] = value.strip()
    return message


def format_lsnp_message(msg_dict: dict) -> str:
    '''
    Formats a dictionary into an LSNP-compliant message string.
    
    Converts key-value pairs into "Key: Value" format, each on a new line.
    Ends with two newline characters.
    
    Example:
    >>> msg_dict = {"Type": "Request", "ID": "12345", "Payload": "Hello World"}
    >>> result = format_lsnp_message(msg_dict)
    result -> "Type: Request\\nID: 12345\\nPayload: Hello World\\n\\n"
    
    Args:
        msg_dict (dict): The dictionary to format.
    
    Returns:
        str: The LSNP-formatted message string.
    '''
    lines = [f"{key}: {value}" for key, value in msg_dict.items()]
    return '\n'.join(lines) + '\n\n'
