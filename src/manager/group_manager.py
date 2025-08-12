import time
import uuid
import threading
from src.protocol import Group
from src.protocol.types.messages.message_formats import (
    make_group_create_message,
    make_group_add_message,
    make_group_remove_message,
    make_group_message
)
from src.utils.tokens import generate_token
from src.config import *

class GroupManager():
  def __init__(self, controller, logger):
      self.controller = controller
      self.logger = logger
  
  def group_create(self, group_name: str, members: str):
    parts = members.split(",")

    for i, recipient_id in enumerate(parts):
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
            parts[i] = full_recipient_id

        if parts[i] not in self.controller.peer_map:
            self.controller.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
            return

    group_id = str(uuid.uuid4())
    group = Group(group_id, group_name, self.controller.full_user_id, parts)
    token = generate_token(self.controller.full_user_id, "group")
    self.controller.groups.append(group)

    msg = make_group_create_message(
        from_user_id = self.controller.full_user_id,
        group_id = group.group_id, 
        group_name = group.group_name, 
        members = parts, 
        token = token
    )

    for member in parts:
        peer = self.controller.peer_map[member]
        try:
            self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
            self.controller.lsnp_logger.info(f"[GROUP_CREATE] Added member {peer.ip}:{peer.port}")
        except Exception as e:
            self.controller.lsnp_logger.error("[GROUP_CREATE] FAILED: To add {peer.ip} - {e}")

    self.controller.lsnp_logger.info(f"GROUP CREATE: Group \"{group.group_name}\" successfully created.")

    if self.controller.verbose:
        self.controller.lsnp_logger.info(f"[GROUP_CREATE] Group created with {len(group.members) + 1} members.")

  def group_add(self, group_index: int, members: str):
      parts = members.split(",")

      for i, recipient_id in enumerate(parts):
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
              parts[i] = full_recipient_id

          if parts[i] not in self.controller.peer_map:
              self.controller.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
              return
      
      for member in parts:
          self.controller.groups[group_index].members.append(member)
      token = generate_token(self.controller.full_user_id, "group")

      members_str = ""
      add_str = ""
      for member in self.controller.groups[group_index].members:
          members_str = members_str + member + ","
      for member in parts:
          add_str = add_str + member + ","
      members_str = members_str[:-1]
      add_str = add_str[:-1]

      msg = make_group_add_message(
          from_user_id = self.controller.full_user_id,
          group_id = self.controller.groups[group_index].group_id,
          group_name = self.controller.groups[group_index].group_name,
          add = add_str, 
          members = members_str,
          token = token
      )

      for member in self.controller.groups[group_index].members:
          peer = self.controller.peer_map[member]
          try:
              self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
              if member in parts:
                  self.controller.lsnp_logger.info(f"[GROUP_ADD] Added member {peer.ip}:{peer.port}")
          except Exception as e:
              self.controller.lsnp_logger.error("[GROUP_ADD] FAILED: To add {peer.ip} - {e}")

      self.controller.lsnp_logger.info(f"GROUP ADD: Group \"{self.controller.groups[group_index].group_name}\" successfully added {len(parts)} member(s).")

      if self.controller.verbose:
          self.controller.lsnp_logger.info(f"[GROUP_ADD] Group now contains {len(self.controller.groups[group_index].members) + 1} members.")

  def group_remove(self, group_index: int, members: str):
      parts = members.split(",")

      for i, recipient_id in enumerate(parts):
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
              parts[i] = full_recipient_id

          if parts[i] not in self.controller.peer_map:
              self.controller.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
              return
      
      for member in parts:
          self.controller.groups[group_index].members.remove(member)
      token = generate_token(self.controller.full_user_id, "group")

      remove_str = ""
      for member in parts:
          remove_str = remove_str + member + ","
      remove_str = remove_str[:-1]

      msg = make_group_remove_message(
          from_user_id = self.controller.full_user_id,
          group_id = self.controller.groups[group_index].group_id,
          remove = remove_str, 
          token = token
      )

      for member in parts:
          peer = self.controller.peer_map[member]
          try:
              self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
              self.controller.lsnp_logger.info(f"[GROUP_REMOVE] Removed member {peer.ip}:{peer.port}")
          except Exception as e:
              self.controller.lsnp_logger.error("[GROUP_REMOVE] FAILED: To remove {peer.ip} - {e}")

      for member in self.controller.groups[group_index].members:
          peer = self.controller.peer_map[member]
          try:
              self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
          except Exception as e:
              self.controller.lsnp_logger.error("[GROUP_REMOVE] FAILED: To address {peer.ip} - {e}")

      self.controller.lsnp_logger.info(f"GROUP REMOVE: Group \"{self.controller.groups[group_index].group_name}\" successfully removed {len(parts)} member(s).")

      if self.controller.verbose:
          self.controller.lsnp_logger.info(f"[GROUP_REMOVE] Group now contains {len(self.controller.groups[group_index].members) + 1} members.")

  def group_message(self, group_index: int, content: str):
      for recipient_id in self.controller.groups[group_index].members:
          if recipient_id not in self.controller.peer_map:
              self.controller.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
              return

      if self.controller.groups[group_index].owner_id not in self.controller.peer_map:
          self.controller.lsnp_logger.error(f"[ERROR] Unknown peer: {self.controller.groups[group_index].owner_id}")
          return
          
      message_id = str(uuid.uuid4())
      token = generate_token(self.controller.full_user_id, "group")

      msg = make_group_message(
          from_user_id = self.controller.full_user_id,
          group_id = self.controller.groups[group_index].group_id,
          content = content,
          message_id = message_id,
          token = token
      )

      ack_event = threading.Event()
      self.controller.ack_events[message_id] = ack_event

      for member in self.controller.groups[group_index].members:
          peer = self.controller.peer_map[member]
          try:
              for attempt in range(RETRY_COUNT):
                  self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
                  if self.controller.verbose:
                      self.controller.lsnp_logger.info(f"[GROUP MESSAGE SEND] Attempt {attempt + 1} to \"{self.controller.groups[group_index].group_name}\" for {member} at {peer.ip}")
                  
                  if ack_event.wait(RETRY_INTERVAL):
                      self.controller.lsnp_logger.info(f"[GROUP MESSAGE SENT] to \"{self.controller.groups[group_index].group_name}\" for {member} at {peer.ip}")
                      break
                  
                  if self.controller.verbose:
                      self.controller.lsnp_logger.info(f"[RETRY] {attempt + 1} to \"{self.controller.groups[group_index].group_name}\" for {member} at {peer.ip}")
          except Exception as e:
              self.controller.lsnp_logger.error(f"[FAILED] Group Message to \"{self.controller.groups[group_index].group_name}\" for {member} at {peer.ip}")
              del self.controller.ack_events[message_id] 

      peer = self.controller.peer_map[self.controller.groups[group_index].owner_id]
      try:
          for attempt in range(RETRY_COUNT):
              self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
              if self.controller.verbose:
                  self.controller.lsnp_logger.info(f"[GROUP MESSAGE SEND] Attempt {attempt + 1} to \"{self.controller.groups[group_index].group_name}\" for {self.controller.groups[group_index].owner_id} at {peer.ip}")
              
              if ack_event.wait(RETRY_INTERVAL):
                  self.controller.lsnp_logger.info(f"[GROUP MESSAGE SENT] to \"{self.controller.groups[group_index].group_name}\" for {self.controller.groups[group_index].owner_id} at {peer.ip}")
                  break
              
              if self.controller.verbose:
                  self.controller.lsnp_logger.info(f"[RETRY] {attempt + 1} to \"{self.controller.groups[group_index].group_name}\" for {self.controller.groups[group_index].owner_id} at {peer.ip}")
      except Exception as e:
              self.controller.lsnp_logger.error(f"[FAILED] Group Message to \"{self.controller.groups[group_index].group_name}\" for {self.controller.groups[group_index].owner_id} at {peer.ip}")
              del self.controller.ack_events[message_id] 
      
      del self.controller.ack_events[message_id]
