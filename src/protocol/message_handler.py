import json
import uuid
import threading
from typing import Dict, Tuple, TYPE_CHECKING
from src.protocol import *
from src.utils import *
from src.manager.lsnp_controller import LSNPController

RETRY_COUNT = 10
RETRY_INTERVAL = 5

class MessageHandler:
  def __init__(self, controller: 'LSNPController') -> None:
    self.controller = controller
    pass

  def _handle_kv_message(self, kv: dict, addr: Tuple[str, int]):
    msg_type = kv.get("TYPE")
    sender_ip, sender_port = addr

    
    if msg_type == "PROFILE":
      from_id = kv.get("USER_ID", "")
      display_name = kv.get("DISPLAY_NAME", "")
      ip = addr[0]
      port = addr[1]

      self.controller.ip_tracker.log_new_ip(sender_ip, from_id, "profile_message")

      if from_id not in self.controller.peer_map:
        peer = Peer(from_id, display_name, ip, port)
        self.controller.peer_map[from_id] = peer
        
        if self.controller.verbose:
          self.controller.lsnp_logger_v.info(f"[PROFILE] {display_name} ({from_id}) joined from {ip}")
    
    elif msg_type == "DM":
      from_id = kv.get("FROM", "")
      to_id = kv.get("TO", "")
      token = kv.get("TOKEN", "")
      
      # Verify this message is for us
      if to_id != self.controller.full_user_id:
        if self.controller.verbose:
          self.controller.lsnp_logger_v.info(f"[DM IGNORED] Not for us: {to_id}")
        return
      
      if not validate_token(token, "chat"):
        if self.controller.verbose:
          self.controller.lsnp_logger_v.info(f"[DM REJECTED] Invalid token from {from_id}")
        return
      
      content = kv.get("CONTENT", "")
      message_id = kv.get("MESSAGE_ID", "")
      timestamp = kv.get("TIMESTAMP", "")
      
      # Get display name for prettier output
      display_name = from_id.split('@')[0]  # Default to username part
      
      # Check if it's from ourselves
      if from_id == self.controller.full_user_id:
        display_name = self.controller.display_name
      else:
        # Look up in peer_map for other peers
        for peer in self.controller.peer_map.values():
          if peer.user_id == from_id:
            display_name = peer.display_name
            break
      
      self.controller.lsnp_logger.info(f"{display_name}: {content}")
      self.controller.inbox.append(f"[{timestamp}] {display_name}: {content}")
      self._send_ack(message_id, addr)
   
    elif msg_type == "FOLLOW":
      from_id = kv.get("USER_ID", "")
      display_name = kv.get("DISPLAY_NAME", "")
      self.controller.lsnp_logger.info(f"[NOTIFY] {display_name} ({from_id}) is now following you.")
      self.controller.inbox.append(f"User {display_name} started following you.")

    elif msg_type == "UNFOLLOW":
        from_id = kv.get("USER_ID", "")
        display_name = kv.get("DISPLAY_NAME", "")
        self.controller.lsnp_logger.info(f"[NOTIFY] {display_name} ({from_id}) has unfollowed you.")
        self.controller.inbox.append(f"User {display_name} unfollowed you.")
      
    elif msg_type == "ACK":
      message_id = kv.get("MESSAGE_ID", "")
      if message_id in self.controller.ack_events:
        self.controller.ack_events[message_id].set()
        if self.controller.verbose:
          self.controller.lsnp_logger_v.info(f"[ACK] Received for message {message_id}")
    
    elif msg_type == "PING":
      user_id = kv.get("USER_ID", "")
      if self.controller.verbose:
        self.controller.lsnp_logger_v.info(f"[PING] From {user_id}")

  def _handle_json_message(self, msg: dict, addr):
    # Legacy handler for any remaining JSON messages
    msg_type = msg.get("type")
    sender_id = msg.get("user_id")

    if msg_type == "DM":
      token = msg.get("token", "")
      if not validate_token(token):
        self.controller.lsnp_logger.warning(f"[DM REJECTED] Invalid token from {sender_id}")
        return
      content = msg.get("content")
      message_id = msg.get("message_id")
      timestamp = msg.get("timestamp")
      self.controller.lsnp_logger_v.info(f"{sender_id}: {content}")
      self.controller.inbox.append(f"[{timestamp}] {sender_id}: {content}")
      self._send_ack_json(sender_id, addr, message_id)

    elif msg_type == "ACK":
      message_id = msg.get("message_id")
      if message_id in self.controller.ack_events:
        self.controller.ack_events[message_id].set()

  def _send_ack(self, message_id: str, addr):
    ack_msg = make_ack_message(message_id)
    self.controller.socket.sendto(ack_msg.encode(), addr)
    
    if self.controller.verbose:
      self.controller.lsnp_logger_v.info(f"[ACK SENT] For message {message_id} to {addr}")

  def _send_ack_json(self, sender_id, addr, message_id):
    # Legacy JSON ACK for compatibility
    ack = {
      "type": "ACK",
      "user_id": self.controller.user_id,
      "message_id": message_id
    }
    self.controller.socket.sendto(json.dumps(ack).encode(), addr)

  def _send_dm(self, recipient_id: str, content: str):
    # Accept both formats: "user" or "user@ip"
    if "@" not in recipient_id:
      # Find the full user_id in peer_map
      full_recipient_id = None
      for user_id in self.controller.peer_map:
        if user_id.startswith(f"{recipient_id}@"):
          full_recipient_id = user_id
          break
      if not full_recipient_id:
        self.controller.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
        return
      recipient_id = full_recipient_id

    if recipient_id not in self.controller.peer_map:
      self.controller.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
      return

    peer = self.controller.peer_map[recipient_id]
    message_id = str(uuid.uuid4())
    token = generate_token(self.controller.full_user_id, "chat")

    msg = make_dm_message(
      from_user_id=self.controller.full_user_id,
      to_user_id=recipient_id,
      content=content,
      message_id=message_id,
      token=token
    )

    ack_event = threading.Event()
    self.controller.ack_events[message_id] = ack_event

    for attempt in range(RETRY_COUNT):
      self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
      if self.controller.verbose:
        self.controller.lsnp_logger_v.info(f"[DM SEND] Attempt {attempt + 1} to {recipient_id} at {peer.ip}")
      
      if ack_event.wait(RETRY_INTERVAL):
        self.controller.lsnp_logger.info(f"[DM SENT] to {peer.display_name} at {peer.ip}")
        del self.controller.ack_events[message_id]
        return
      
      if self.controller.verbose:
        self.controller.lsnp_logger_v.info(f"[RETRY] {attempt + 1} for {recipient_id} at {peer.ip}")

    self.controller.lsnp_logger.error(f"[FAILED] DM to {peer.display_name} at {peer.ip}")
    del self.controller.ack_events[message_id]
  
  def _send_post(self, user_id: str):
    # for user_id in self.controller.followers:
    pass
      
  def _follow(self, user_id: str):
    if "@" not in user_id:
      # Find the full user_id in peer_map
      full_user_id = None
      for id in self.controller.peer_map:
        if id.startswith(f"{user_id}@"):
          full_user_id = id
          break
      if not full_user_id:
        self.controller.lsnp_logger.error(f"[ERROR] Unknown peer: {user_id}")
        return
      user_id = full_user_id
   
    if user_id not in self.controller.peer_map:
      self.controller.lsnp_logger.error(f"[ERROR] Unknown peer: {user_id}") 
      return
    elif user_id in self.controller.followers:
      self.controller.lsnp_logger.warning(f"[FOLLOW] Already following {user_id}")
      return
    else:
      self.controller.lsnp_logger.info(f"[FOLLOW] Now following {user_id}")
      self.controller.followers.append(user_id)
  
      peer = self.controller.peer_map[user_id]
      msg = f"TYPE: FOLLOW\nUSER_ID: {self.controller.full_user_id}\nDISPLAY_NAME: {self.controller.display_name}\n\n"
      
      try:
        self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
        self.controller.lsnp_logger.info(f"[FOLLOW SENT] To {peer.display_name} ({peer.ip})")
        if self.controller.verbose:
          self.controller.lsnp_logger_v.info(f"[FOLLOW MSG] {msg.strip()}")
      except Exception as e:
        self.controller.lsnp_logger.error(f"[FOLLOW FAILED] To {peer.ip} - {e}")
   
  def _unfollow(self, user_id: str):
    if "@" not in user_id:
      # Find the full user_id in peer_map
      full_user_id = None
      for id in self.controller.peer_map:
        if id.startswith(f"{user_id}@"):
          full_user_id = id
          break
      if not full_user_id:
        self.controller.lsnp_logger.error(f"[ERROR] Unknown peer: {user_id}")
        return
      user_id = full_user_id
   
    if user_id not in self.controller.peer_map:
      self.controller.lsnp_logger.error(f"[ERROR] Unknown peer: {user_id}") 
      return
    elif user_id not in self.controller.followers:
      self.controller.lsnp_logger.warning(f"[FOLLOW] Not following {user_id}")
      return
    else:
      self.controller.lsnp_logger.info(f"[FOLLOW] Now unfollowing {user_id}")
      self.controller.followers.remove(user_id) 
   
      peer = self.controller.peer_map[user_id]
      msg = f"TYPE: UNFOLLOW\nUSER_ID: {self.controller.full_user_id}\nDISPLAY_NAME: {self.controller.display_name}\n\n"
      try:
        self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
        self.controller.lsnp_logger.info(f"[UNFOLLOW SENT] To {peer.display_name} ({peer.ip})")
        if self.controller.verbose:
          self.controller.lsnp_logger_v.info(f"[UNFOLLOW MSG] {msg.strip()}")
      except Exception as e:
        self.controller.lsnp_logger.error(f"[UNFOLLOW FAILED] To {peer.ip} - {e}")
  
  def send_dm_cmd(self, cmd: str):
    parts = cmd.split(" ", 2)
    if len(parts) < 3:
      self.controller.lsnp_logger.info("Usage: dm <user_id> <message>")
      return
    _, recipient_id, message = parts
    self._send_dm(recipient_id, message)
   
  def follow_cmd(self, cmd: str):
    parts = cmd.split(" ", 2)
    if len(parts) < 2:
      self.controller.lsnp_logger.info("Usage: follow <user_id>")
      return
    _, user_id = parts
    self.controller.lsnp_logger.debug(user_id)
    self._follow(user_id)
  
  def unfollow_cmd(self, cmd: str):
    parts = cmd.split(" ", 2)
    if len(parts) < 2:
      self.controller.lsnp_logger.info("Usage: unfollow <user_id>")
      return
    _, user_id = parts
    self._unfollow(user_id)
  
  def post_cmd(self, cmd: str):
    parts = cmd.split(" ", 2)
    if len(parts) < 2:
      self.controller.lsnp_logger.info("Usage: post <message>")
      return
    _, message = parts
    self._send_post(message)

  