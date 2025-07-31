from src.manager.state import known_peers, posts, dms

def parse_lsnp_messages(raw_message: str, verbose: bool) -> dict:
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
        verbose (bool): If True, print debug information

    Returns:
        dict: A dictionary of key-value pairs extracted from the message.
    '''
    if verbose:
        print("[DEBUG] Raw LSNP message to parse:")
        print(raw_message)
        print("=" * 40)
        
    lines = raw_message.strip().split('\n')
    message = {}
    
    for line in lines:
        if line.strip() == '':
            continue
        if ':' in line:
            key, value = line.split(':', 1)
            message[key.strip()] = value.strip()
            if verbose:
                print(f"[DEBUG] Parsed Key: '{key}' | Value: '{value}'")
            else:
                if verbose:
                    print(f"[WARNING] Ignored malformed line: '{line}'")
                    
    if verbose:
        print("=" * 40)
        print("[DEBUG] Final Parsed Message Dictionary:", message)

    return message


def format_lsnp_message(msg_dict: dict, verbose: bool) -> str:
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
        verbose (bool): If True, print debug information
    
    Returns:
        str: The LSNP-formatted message string.
    '''
    if verbose:
        print("[DEBUG] Formatting dictionary into LSNP message:")
        print(msg_dict)
        print("=" * 40)

    lines = []
    for key, value in msg_dict.items():
        line = f"{key}: {value}"
        lines.append(line)
        if verbose:
            print(f"[DEBUG] Added line: '{line}'")

    formatted_message = '\n'.join(lines) + '\n\n'

    if verbose:
        print("=" * 40)
        print("[DEBUG] Final LSNP Message String:")
        print(formatted_message)

    return formatted_message
