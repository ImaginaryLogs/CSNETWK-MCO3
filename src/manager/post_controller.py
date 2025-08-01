import socket
import threading
import time
import json
import uuid
from typing import Dict, List, Callable, Tuple
from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser, ServiceListener
from src.ui import logging
from src.config import *
from src.protocol import *
from src.utils import *
from src.network import *

logger = logging.Logger()

LSNP_CODENAME = 'LSNPCON'
LSNP_PREFIX = f'[green][{LSNP_CODENAME}][/]'

lsnp_logger = logger.get_logger(LSNP_PREFIX)
lsnp_logger_v = logger.get_logger(f'{LSNP_PREFIX} |:')

LSNP_BROADCAST_PERIOD_SECONDS = 300

def follow(self, user_id: str):
	if "@" not in user_id:
		# Find the full user_id in peer_map
		full_user_id = None
		for id in self.peer_map:	
			if id.startswith(f"{user_id}@"):
				full_user_id = id
				break
		if not full_user_id:
			lsnp_logger.error(f"[ERROR] Unknown peer: {user_id}")
			return
		user_id = full_user_id
   
	if user_id not in self.peer_map:
		lsnp_logger.error(f"[ERROR] Unknown peer: {user_id}") 
		return
	elif user_id in self.followers:
		lsnp_logger.warning(f"[FOLLOW] Already following {user_id}")
		return
	else:
		lsnp_logger.info(f"[FOLLOW] Now following {user_id}")
		self.followers.append(user_id)
	
		peer = self.peer_map[user_id]
		message_id = str(uuid.uuid4())[:8]
		token = generate_token(self.full_user_id, "follow")
  
		msg = make_follow_message(
				from_id=self.full_user_id,
				to_id=user_id,
				message_id=message_id,
				token=token
		)			
		try:
			self.socket.sendto(msg.encode(), (peer.ip, peer.port))
			lsnp_logger.info(f"[FOLLOW SENT] To {peer.display_name} ({peer.ip})")
			if self.verbose:
				lsnp_logger_v.info(f"[FOLLOW MSG] {msg.strip()}")
		except Exception as e:
			lsnp_logger.error(f"[FOLLOW FAILED] To {peer.ip} - {e}")
   
def unfollow(self, user_id: str):
	if "@" not in user_id:
		# Find the full user_id in peer_map
		full_user_id = None
		for id in self.peer_map:
			if id.startswith(f"{user_id}@"):
				full_user_id = id
				break
		if not full_user_id:
			lsnp_logger.error(f"[ERROR] Unknown peer: {user_id}")
			return
		user_id = full_user_id
	
	if user_id not in self.peer_map:
		lsnp_logger.error(f"[ERROR] Unknown peer: {user_id}") 
		return
	elif user_id not in self.followers:
		lsnp_logger.warning(f"[UNFOLLOW] Not following {user_id}")
		return
	else:
		lsnp_logger.info(f"[UNFOLLOW] Now unfollowing {user_id}")
		self.followers.remove(user_id) 
	
		peer = self.peer_map[user_id]
		message_id = str(uuid.uuid4())[:8]
		token = generate_token(self.full_user_id, "unfollow")

		msg = make_unfollow_message(
				from_id=self.full_user_id,
				to_id=user_id,
				message_id=message_id,
				token=token
		)
		try:
			self.socket.sendto(msg.encode(), (peer.ip, peer.port))
			lsnp_logger.info(f"[UNFOLLOW SENT] To {peer.display_name} ({peer.ip})")
			if self.verbose:
				lsnp_logger_v.info(f"[UNFOLLOW MSG] {msg.strip()}")
		except Exception as e:
			lsnp_logger.error(f"[UNFOLLOW FAILED] To {peer.ip} - {e}")   
   
def send_post(self, message: str):
    if not self.followers:
        lsnp_logger.warning("[POST] No followers to send the post to.")
        return

    message_id = str(uuid.uuid4())
    token = generate_token(self.full_user_id, "post")
    msg = make_post_message(
        from_id=self.full_user_id,
        content=message,
        message_id=message_id,
        token=token
    )

    sent_count = 0
    for follower_id in self.followers:
        if follower_id not in self.peer_map:
            lsnp_logger.warning(f"[POST] Skipped unknown follower: {follower_id}")
            continue

        peer = self.peer_map[follower_id]
        try:
            self.socket.sendto(msg.encode(), (peer.ip, peer.port))
            sent_count += 1
            lsnp_logger.info(f"[POST SENT] To {peer.display_name} ({peer.ip})")
            if self.verbose:
                lsnp_logger_v.info(f"[POST MSG] {msg.strip()}")
        except Exception as e:
            lsnp_logger.error(f"[POST FAILED] To {peer.display_name} ({peer.ip}) - {e}")

    lsnp_logger.info(f"[POST COMPLETE] Sent to {sent_count}/{len(self.followers)} followers")

def make_follow_message(from_id: str, to_id: str, message_id: str, token: str) -> str:
    timestamp = int(time.time())
    return (
        f"TYPE:FOLLOW\n"
        f"MESSAGE_ID:{message_id}\n"
        f"FROM:{from_id}\n"
        f"TO:{to_id}\n"
        f"TIMESTAMP:{timestamp}\n"
        f"TOKEN:{token}\n\n"
    )

def make_unfollow_message(from_id: str, to_id: str, message_id: str, token: str) -> str:
    timestamp = int(time.time())
    return (
        f"TYPE:UNFOLLOW\n"
        f"MESSAGE_ID:{message_id}\n"
        f"FROM:{from_id}\n"
        f"TO:{to_id}\n"
        f"TIMESTAMP:{timestamp}\n"
        f"TOKEN:{token}\n\n"
    )
    
def make_post_message(from_id: str, content: str, message_id: str, token: str) -> str:
    timestamp = int(time.time())
    return (
        f"TYPE:POST\n"
        f"MESSAGE_ID:{message_id}\n"
        f"FROM:{from_id}\n"
        f"TIMESTAMP:{timestamp}\n"
        f"TOKEN:{token}\n"
        f"CONTENT:{content}\n\n"
    )
