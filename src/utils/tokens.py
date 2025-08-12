import time
from ..config.config import *
import src.manager.state as state 
from src.manager.lsnp_controller import LSNPController

# --- Token Management ---
token_blacklist = {}

def generate_token(user_id: str, scope: str = "chat", ttl: int = TOKEN_TTL) -> str:
    timestamp = int(time.time())
    return f"{user_id}|{timestamp + state.ttl}|{scope}"

def validate_token(token: str, required_scope: str = "chat", controller: LSNPController | None = None) -> bool:
    if token in token_blacklist:
        return False
    if controller and hasattr(controller, "revoked_tokens"):
        if token in controller.revoked_tokens:
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