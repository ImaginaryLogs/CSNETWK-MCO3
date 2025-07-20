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

# Handles the different type of LSNP messages, 
def handle_lsnp_message(message: dict, verbose=False):
    msg_type = message.get("TYPE")

    if msg_type == "PROFILE":
        handle_profile(message, verbose)
    elif msg_type == "POST":
        handle_post(message, verbose)
    elif msg_type == "DM":
        handle_dm(message, verbose)

# Handles profile protocol
def handle_profile(msg, verbose):
    user_id = msg["USER_ID"] # Assume there's always a USER_ID
    known_peers[user_id] = {
        "display_name": msg.get("DISPLAY_NAME", user_id),
        "status": msg.get("STATUS", ""),
        "avatar_type": msg.get("AVATAR_TYPE", None),
        "avatar_encoding": msg.get("AVATAR_ENCODING", None),
        "avatar_data": msg.get("AVATAR_DATA", None)
    }
    if verbose:
        print(f"<PROFILE> {user_id} = {known_peers[user_id]}")

# Handles posts protocol
def handle_post(msg, verbose):
    user_id = msg["USER_ID"]
    content = msg["CONTENT"]
    ttl = msg.get("TTL", 3600)  # Default the TTL to 3600 if there is no TTL
    message_id = msg["MESSAGE_ID"]  # Assume there's always a MESSAGE_ID
    token = msg["TOKEN"]  # Assume there's always a TOKEN

    # Store the post
    posts.setdefault(user_id, []).append({
        "content": content,
        "message_id": message_id,
        "ttl": ttl,
        "token": token
    })

    name = known_peers.get(user_id, {}).get("display_name", user_id)
    print(f"{name}: {content}")    
    
    if verbose:
        print(f"<POST> {user_id} - Message ID: {message_id}, TTL: {ttl}, Token: {token}")
        print(f"<PROFILE> {user_id} = {known_peers[user_id]}")

# Handles DM protocol
def handle_dm(msg, verbose):
    sender = msg["FROM"]
    recipient = msg["TO"]
    content = msg["CONTENT"]
    timestamp = msg.get("TIMESTAMP")
    message_id = msg.get("MESSAGE_ID") # Assume there's always a MESSAGE_ID
    token = msg.get("TOKEN") # Assume there's always a TOKEN

    # Store the DM
    dms.setdefault(sender, []).append({
        "content": content,
        "timestamp": timestamp,
        "message_id": message_id,
        "token": token
    })

    name = known_peers.get(sender, {}).get("display_name", sender)
    print(f"[DM] {name} says: {content}")

    if verbose:
        print(f"<DM> from {sender} to {recipient} at {timestamp}")
        print(f"Message ID: {message_id}, Token: {token}")
        if sender in known_peers:
            print(f"<PROFILE> {sender} = {known_peers[sender]}")
