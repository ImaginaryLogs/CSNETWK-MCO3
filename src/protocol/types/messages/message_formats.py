import time
import uuid
import os
import base64
import mimetypes
from src.utils import *

def make_profile_message(name: str, user_id: str, avatar_path: str = None):
    message = {
        "TYPE": "PROFILE",
        "USER_ID": user_id,
        "DISPLAY_NAME": name,
        "TIMESTAMP": int(time.time()),
        "MESSAGE_ID": str(uuid.uuid4())
    }

    if avatar_path and os.path.isfile(avatar_path):
        mime_type, _ = mimetypes.guess_type(avatar_path)
        if mime_type:
            with open(avatar_path, "rb") as img_file:
                avatar_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            message["AVATAR_TYPE"] = mime_type
            message["AVATAR_ENCODING"] = "base64"
            message["AVATAR_DATA"] = avatar_base64
                        
    return format_kv_message(message)


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
