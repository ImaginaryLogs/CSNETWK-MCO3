def format_kv_message(fields: dict) -> str:
    """Formats fields in a dict to a key-value string separated with '\\n'. Helps with sending information correctly to a network
    
    Example:
    >>> dict = { key1: value1, key2: value2 }
    >>> format_kv_message(dict)
    "key1: value1\\nkey2: value2\\n\\n"

    Args:
        fields (dict): dictionary containing key-value pairs

    Returns:
        str: string format of the dict
    """
    return "\n".join(f"{key}: {value}" for key, value in fields.items()) + "\n\n"

def parse_kv_message(msg: str) -> dict:
    """Reparses key-value dict strings back to their original dict type

    Args:
        msg (str): string format of a key-value dict

    Returns:
        dict: key-value dict format of a string
    """
    lines = msg.strip().splitlines()
    return dict(line.split(": ", 1) for line in lines if ": " in line)