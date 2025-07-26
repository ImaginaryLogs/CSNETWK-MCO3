import time
from ..config.config import *

# --- Token Management ---
token_blacklist = {}

def generate_token(user_id: str, scope: str = "chat", ttl: int = TOKEN_TTL) -> str:
    timestamp = int(time.time())
    return f"{user_id}|{timestamp}|{scope}"

def validate_token(token: str, required_scope: str = "chat") -> bool:
    if token in token_blacklist:
        return False
    try:
        user_id, timestamp_str, scope = token.split("|")
        if int(time.time()) - int(timestamp_str) > TOKEN_TTL:
            return False
        return scope == required_scope
    except:
        return False

def revoke_token(token: str):
    token_blacklist[token] = True