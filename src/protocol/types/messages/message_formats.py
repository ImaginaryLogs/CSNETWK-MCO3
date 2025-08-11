import time
import uuid
import os
import base64
import mimetypes
from src.utils import *
from typing import TypedDict, Optional, List

class ProfileMessageDict(TypedDict, total=False):
    TYPE: str
    USER_ID: str
    DISPLAY_NAME: str
    TIMESTAMP: int
    MESSAGE_ID: str
    AVATAR_TYPE: str
    AVATAR_ENCODING: str
    AVATAR_DATA: str

class DMMessageDict(TypedDict):
    TYPE: str
    FROM: str
    TO: str
    CONTENT: str
    TIMESTAMP: int
    MESSAGE_ID: str
    TOKEN: str

class AckMessageDict(TypedDict):
    TYPE: str
    MESSAGE_ID: str
    STATUS: str

class PingMessageDict(TypedDict):
    TYPE: str
    USER_ID: str

class FollowMessageDict(TypedDict):
    TYPE: str
    MESSAGE_ID: str
    FROM: str
    TO: str
    TIMESTAMP: int
    TOKEN: str

class PostMessageDict(TypedDict):
    TYPE: str
    USER_ID: str
    CONTENT: str
    TTL: int
    MESSAGE_ID: str
    TIMESTAMP: int
    TOKEN: str

class LikeMessageDict(TypedDict):
    TYPE: str
    FROM: str
    TO: str
    POST_TIMESTAMP: str
    ACTION: str
    TIMESTAMP: str
    TOKEN: str

class GroupCreateMessageDict(TypedDict):
    TYPE: str
    FROM: str
    GROUP_ID: str
    GROUP_NAME: str
    MEMBERS: str
    TIMESTAMP: int
    TOKEN: str

class GroupAddMessageDict(TypedDict):
    TYPE: str
    FROM: str
    GROUP_ID: str
    GROUP_NAME: str
    ADD: str
    MEMBERS: str
    TIMESTAMP: int
    TOKEN: str

class GroupRemoveMessageDict(TypedDict):
    TYPE: str
    FROM: str
    GROUP_ID: str
    REMOVE: str
    TIMESTAMP: int
    TOKEN: str

class GroupMessageDict(TypedDict):
    TYPE: str
    FROM: str
    GROUP_ID: str
    MESSAGE_ID: str
    CONTENT: str
    TIMESTAMP: int
    TOKEN: str


def make_profile_message(name: str, user_id: str, avatar_path: str|None = None) -> str:
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


def make_dm_message(from_user_id: str, to_user_id: str, content: str, message_id: str, token: str) -> str:
    return format_kv_message({
        "TYPE": "DM",
        "FROM": from_user_id,
        "TO": to_user_id,
        "CONTENT": content,
        "TIMESTAMP": int(time.time()),
        "MESSAGE_ID": message_id,
        "TOKEN": token
    })

def make_ack_message(message_id: str) -> str:
    return format_kv_message({
        "TYPE": "ACK",
        "MESSAGE_ID": message_id,
        "STATUS": "RECEIVED"
    })

def make_ping_message(user_id: str) -> str:
    return format_kv_message({
        "TYPE": "PING",
        "USER_ID": user_id
    })
    
def make_follow_message(from_id: str, to_id: str, message_id: str, token: str) -> str:
    return format_kv_message({
        "TYPE": "FOLLOW",
        "MESSAGE_ID": message_id,
        "FROM": from_id,
        "TO": to_id,
        "TIMESTAMP": int(time.time()),
        "TOKEN": token
    })

def make_post_message(from_id: str, content: str, ttl: int, message_id: str, token: str) -> str:
    return format_kv_message({
        "TYPE": "POST",
        "USER_ID": from_id,
        "CONTENT": content,
        "TTL": ttl,  
        "MESSAGE_ID": message_id,
        "TIMESTAMP": int(time.time()),
        "TOKEN": token
    })
    
def make_like_message(from_id: str, to_id: str, post_timestamp_id: str, action: str, timestamp: str, token: str) -> str:
    return format_kv_message({
        "TYPE": "LIKE",
        "FROM": from_id,
        "TO": to_id,
        "POST_TIMESTAMP": post_timestamp_id,
        "ACTION": action,
        "TIMESTAMP": timestamp,
        "TOKEN": token
    })
    
def make_group_create_message(from_user_id: str, group_id: str, group_name: str, members: list[str], token: str) -> str:
    return format_kv_message({
        "TYPE": "GROUP_CREATE",
        "FROM": from_user_id,
        "GROUP_ID": group_id,
        "GROUP_NAME": group_name,
        "MEMBERS": ",".join(members),
        "TIMESTAMP": int(time.time()),
        "TOKEN": token
    })

def make_group_add_message(from_user_id: str, group_id: str, group_name: str, add: str, members: str, token: str) -> str:
    return format_kv_message({
        "TYPE": "GROUP_ADD",
        "FROM": from_user_id,
        "GROUP_ID": group_id,
        "GROUP_NAME": group_name,
        "ADD": add,
        "MEMBERS": members,
        "TIMESTAMP": int(time.time()),
        "TOKEN": token
    })      

def make_group_remove_message(from_user_id: str, group_id: str, remove: str, token: str) -> str:
    return format_kv_message({
        "TYPE": "GROUP_REMOVE",
        "FROM": from_user_id,
        "GROUP_ID": group_id,
        "REMOVE": remove,
        "TIMESTAMP": int(time.time()),
        "TOKEN": token
    })

def make_group_message(from_user_id: str, group_id: str, message_id: str, content: str, token: str) -> str:
    return format_kv_message({
        "TYPE": "GROUP_MESSAGE",
        "FROM": from_user_id,
        "GROUP_ID": group_id,
        "MESSAGE_ID": message_id,
        "CONTENT": content,
        "TIMESTAMP": int(time.time()),
        "TOKEN": token
    })
