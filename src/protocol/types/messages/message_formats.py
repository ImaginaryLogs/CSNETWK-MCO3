import time
import uuid
from src.utils import *

def make_profile_message(name: str, user_id: str, ip: str):
    return format_kv_message({
        "TYPE": "PROFILE",
        "USER_ID": f"{user_id}@{ip}",
        "DISPLAY_NAME": name,
        "TIMESTAMP": int(time.time()),
        "MESSAGE_ID": str(uuid.uuid4())
    })

def make_dm_message(from_user_id: str, to_user_id: str, content: str, message_id: str, token: str):
    return format_kv_message({
        "TYPE": "DM",
        "FROM": from_user_id,
        "TO": to_user_id,
        "CONTENT": content,
        "TIMESTAMP": int(time.time()),
        "MESSAGE_ID": message_id,
        "TOKEN": token
    })

def make_ack_message(message_id: str):
    return format_kv_message({
        "TYPE": "ACK",
        "MESSAGE_ID": message_id,
        "STATUS": "RECEIVED"
    })

def make_ping_message(user_id: str):
    return format_kv_message({
        "TYPE": "PING",
        "USER_ID": user_id
    })