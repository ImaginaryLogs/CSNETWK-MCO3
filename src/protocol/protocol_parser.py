from manager.state import known_peers, posts, dms

# Parses LNSP key-value pairs into a dictionary.
def parse_lsnp_messages(raw_message: str) -> dict:
    lines = raw_message.strip().split('\n')
    message = {}
    for line in lines:
        if line.strip() == '':
            continue
        if ':' in line:
            key, value = line.split(':', 1)
            message[key.strip()] = value.strip()
    return message

# Formats the dictionary made by the parser
def format_lsnp_message(msg_dict: dict) -> str:
    lines = [f"{key}: {value}" for key, value in msg_dict.items()]
    return '\n'.join(lines) + '\n\n'
