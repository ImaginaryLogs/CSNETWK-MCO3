import os
import threading
import uuid
from src.utils.tokens import validate_token, generate_token
from src.protocol.types.messages.message_formats import make_dm_message, make_ping_message, make_follow_message, make_post_message, make_like_message
from src.config import RETRY_COUNT, RETRY_INTERVAL, LSNP_PORT
from src.manager import state
import time
from src.protocol import make_profile_message, make_unfollow_message
import base64
import shlex
from typing import Dict, List, Tuple
import src.manager.state as state
from src.manager.lsnp_controller import LSNPController
from src.ui.logging import LoggerInstance

class CommandManager:
  def __init__(self, controller: "LSNPController", logger: "LoggerInstance"):
      self.controller = controller
      self.logger = logger
  
  def send_dm(self, recipient_id: str, content: str):
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
      if self.controller.verbose: 
        self.controller.lsnp_logger.info(f"[DM SEND] to {recipient_id}: {content}")
      
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
              self.controller.lsnp_logger.info(f"[DM SEND] Attempt {attempt + 1} to {recipient_id} at {peer.ip}")
          
          if ack_event.wait(RETRY_INTERVAL):
              self.controller.lsnp_logger.info(f"[DM SENT] to {peer.display_name} at {peer.ip}")
              del self.controller.ack_events[message_id]
              return
          
          if self.controller.verbose:
              self.controller.lsnp_logger.info(f"[RETRY] {attempt + 1} for {recipient_id} at {peer.ip}")

      self.controller.lsnp_logger.error(f"[FAILED] DM to {peer.display_name} at {peer.ip}")
      del self.controller.ack_events[message_id]

  def send_ping(self):
      msg = make_ping_message(self.controller.full_user_id)
      # Broadcast ping
      broadcast_addr = self.controller.ip.rsplit('.', 1)[0] + '.255'

      try:
          self.controller.socket.sendto(msg.encode(), (broadcast_addr, self.controller.port))
          self.controller.lsnp_logger.info(f"PING BROADCAST: Sent to {broadcast_addr}:{self.controller.port}")    
          if self.controller.verbose:
              self.controller.lsnp_logger.info(f"[PING] Sent to {broadcast_addr}")
      except Exception as e:
          self.controller.lsnp_logger.error(f"PING BROADCAST FAILED: To {broadcast_addr} - {e}")
  
  def list_peers(self):
      if not self.controller.peer_map:
          self.controller.lsnp_logger.info("No peers discovered yet.")
          return

      self.controller.lsnp_logger.info(f"Peer List: {len(self.controller.peer_map)} peers active.")
      self.controller.lsnp_logger.info("Available peers:")
      for peer in self.controller.peer_map.values():
          # Show both short and full format
          short_id = peer.user_id.split('@')[0]
          self.controller.lsnp_logger.info(f"- {peer.display_name} ({short_id}) at {peer.ip}: {peer.port}")

  def show_inbox(self):
      if not self.controller.inbox:
          self.controller.lsnp_logger.info("No messages in inbox.")
          return
      
      self.controller.lsnp_logger.info("Inbox:")
      for msg in self.controller.inbox:
          self.controller.lsnp_logger.info(msg)

  def show_ip_stats(self):
      """Show IP address statistics"""
      stats = self.controller.ip_tracker.get_ip_stats()
      self.controller.lsnp_logger.info("===| IP Address Statistics |===")
      self.controller.lsnp_logger.info(f"Total known IPs: {stats['total_known_ips']}")
      self.controller.lsnp_logger.info(f"Mapped to users: {stats['mapped_users']}")
      self.controller.lsnp_logger.info(f"Total connection attempts: {stats['total_connection_attempts']}")
      self.controller.lsnp_logger.info(f"Blocked IPs: {stats['blocked_ips']}")
      
      if not stats['top_active_ips']:
          return

      self.controller.lsnp_logger.info("Most active IPs:")
      for ip, count in stats['top_active_ips']:
          user = self.controller.ip_tracker.ip_to_user.get(ip, "Unknown")
          self.controller.lsnp_logger.info(f"  {ip} ({user}): {count} connections")
      
  def follow(self, user_id: str):
      # Resolve user_id to full_user_id if needed
      if "@" not in user_id:
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
      elif user_id == self.controller.full_user_id:
          self.controller.lsnp_logger.warning(f"[FOLLOW] Cannot follow yourself: {user_id}")
          return
      elif user_id in self.controller.following:
          self.controller.lsnp_logger.warning(f"[FOLLOW] Already following {user_id}")
          return

      # ✅ Add to following (not followers)
      self.controller.following.add(user_id)
      self.controller.lsnp_logger.info(f"[FOLLOW] Now following {user_id}")

      peer = self.controller.peer_map[user_id]
      message_id = str(uuid.uuid4())[:8]
      token = generate_token(self.controller.full_user_id, "follow")

      msg = make_follow_message(
          from_id=self.controller.full_user_id,
          to_id=user_id,
          message_id=message_id,
          token=token
      )

      # Inline ACK logic
      ack_event = threading.Event()
      self.controller.ack_events[message_id] = ack_event

      for attempt in range(RETRY_COUNT):
          self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
          if self.controller.verbose:
              self.controller.lsnp_logger.info(f"[FOLLOW SEND] Attempt {attempt + 1} to {peer.display_name} at {peer.ip}")

          if ack_event.wait(RETRY_INTERVAL):
              self.controller.lsnp_logger.info(f"[FOLLOW SENT] to {peer.display_name} at {peer.ip}")
              del self.controller.ack_events[message_id]
              self.controller.following.add(user_id)
              return

          if self.controller.verbose:
              self.controller.lsnp_logger.info(f"[FOLLOW RETRY] {attempt + 1} for {peer.display_name} at {peer.ip}")

      self.controller.lsnp_logger.error(f"[FOLLOW FAILED] Could not send to {peer.display_name} at {peer.ip}")
      del self.controller.ack_events[message_id]

  def unfollow(self, user_id: str):
    if "@" not in user_id:
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
    elif user_id == self.controller.full_user_id:
        self.controller.lsnp_logger.warning(f"[UNFOLLOW] Cannot unfollow yourself: {user_id}")
        return
    elif user_id not in self.controller.following:
        self.controller.lsnp_logger.warning(f"[UNFOLLOW] Not following {user_id}")
        return

    self.controller.lsnp_logger.info(f"[UNFOLLOW] Now unfollowing {user_id}")
    self.controller.following.remove(user_id)

    peer = self.controller.peer_map[user_id]
    message_id = str(uuid.uuid4())[:8]
    token = generate_token(self.controller.full_user_id, "unfollow")

    msg = make_unfollow_message(
        from_id=self.controller.full_user_id,
        to_id=user_id,
        message_id=message_id,
        token=token
    )

    # Inline ACK logic
    ack_event = threading.Event()
    self.controller.ack_events[message_id] = ack_event

    for attempt in range(RETRY_COUNT):
        self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
        if self.controller.verbose:
            self.controller.lsnp_logger.info(f"[UNFOLLOW SEND] Attempt {attempt + 1} to {peer.display_name} at {peer.ip}")

        if ack_event.wait(RETRY_INTERVAL):
            self.controller.lsnp_logger.info(f"[UNFOLLOW SENT] to {peer.display_name} at {peer.ip}")
            del self.controller.ack_events[message_id]
            self.controller.following.remove(user_id)
            return

        if self.controller.verbose:
            self.controller.lsnp_logger.info(f"[UNFOLLOW RETRY] {attempt + 1} for {peer.display_name} at {peer.ip}")

    self.controller.lsnp_logger.error(f"[UNFOLLOW FAILED] Could not send to {peer.display_name} at {peer.ip}")
    del self.controller.ack_events[message_id]

  def broadcast_profile(self):
    # Build the PROFILE message
    msg = make_profile_message(self.controller.display_name, self.controller.full_user_id, self.controller.avatar_path)
  
    preview = None
    if self.controller.avatar_path and os.path.isfile(self.controller.avatar_path):
      try:
        with open(self.controller.avatar_path, "rb") as img_file:
            avatar_base64 = base64.b64encode(img_file.read()).decode('utf-8')
        preview = avatar_base64[:20] + "..." if len(avatar_base64) > 20 else avatar_base64
      except Exception as e:
            self.controller.lsnp_logger.error(f"[DEBUG] Failed to generate avatar preview: {e}")
            

      # Log the message but without showing full AVATAR_DATA
    safe_log_msg = msg
    if "AVATAR_DATA" in safe_log_msg:
        # Replace the full avatar data with a placeholder in the log
        safe_log_msg = safe_log_msg.replace(
            msg.split("AVATAR_DATA: ")[1].split("\n", 1)[0],
            preview if preview else "[hidden]"
        )

    # self.controller.lsnp_logger.info(f"[DEBUG] PROFILE message to send:\n{safe_log_msg}")
        
    # Broadcast to the subnet
    broadcast_addr = self.controller.ip.rsplit('.', 1)[0] + '.255'

    try:
        self.controller.socket.sendto(msg.encode(), (broadcast_addr, self.controller.port))
        self.controller.lsnp_logger.info(f"[PROFILE BROADCAST] Sent to {broadcast_addr}:{self.controller.port}")
    except Exception as e:
        self.controller.lsnp_logger.error(f"[BROADCAST FAILED] {e}")

    if self.controller.verbose:
        self.controller.lsnp_logger.info("[BROADCAST] Profile message sent.")

  def send_post(self, content: str):
    
    if self.controller.verbose:
      self.controller.lsnp_logger.info(f"[POST] Sending post to {len(self.controller.followers)} followers")
      
    if not self.controller.followers:
        self.controller.lsnp_logger.warning("[POST] No followers to send the post to.")
        return

    message_map = {}  # Map follower_id → message_id
    ack_events = {}   # Map message_id → Event

    # 1. Send to all followers first
    
    for follower_id in self.controller.followers:
        if self.controller.verbose:
            self.controller.lsnp_logger.info(f"[POST] Sending post to {follower_id}")
        if follower_id == self.controller.full_user_id:
            if self.controller.verbose:
                self.controller.lsnp_logger.info("[POST] Skipping self")
            continue
        if follower_id not in self.controller.peer_map:
            self.controller.lsnp_logger.warning(f"[POST] Skipped unknown follower: {follower_id}")
            continue

        peer = self.controller.peer_map[follower_id]
        message_id = str(uuid.uuid4())
        token = generate_token(self.controller.full_user_id, "post")
        expiry = int(token.split("|")[1])  # timestamp + ttl
        timestamp = expiry - state.ttl

        msg = make_post_message(
            from_id=self.controller.full_user_id,
            content=content,
            ttl=state.ttl,
            message_id=message_id,
            token=token
        )
    
        # Create event for ACK
        ack_event = threading.Event()
        self.controller.ack_events[message_id] = ack_event
        ack_events[message_id] = ack_event
        message_map[follower_id] = message_id

        # Initial send (Attempt 1)
        try:
            self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
            if self.controller.verbose:
                self.controller.lsnp_logger.info(f"[POST SEND] Initial send to {peer.display_name} at {peer.ip}")
        except Exception as e:
            self.controller.lsnp_logger.error(f"[POST ERROR] Failed to send to {peer.display_name}: {e}")

    # 2. Retry logic for all pending ACKs in batch
    for attempt in range(1, RETRY_COUNT):
        pending = [fid for fid, mid in message_map.items() if not ack_events[mid].is_set()]
        if not pending:
            break  # All ACKed, stop early

        if self.controller.verbose:
            self.controller.lsnp_logger.info(f"[POST RETRY] Attempt {attempt + 1} for {len(pending)} followers")
      
        time.sleep(RETRY_INTERVAL)

        # Resend to those who haven't ACKed
        for follower_id in pending:
            message_id = message_map[follower_id]
      
            if ack_events[message_id].is_set():
              continue  # Already ACKed, skip
          
            peer = self.controller.peer_map[follower_id]
            msg = make_post_message(
                from_id=self.controller.full_user_id,
                content=content,
                ttl=state.ttl,
                message_id=message_id,
                token=generate_token(self.controller.full_user_id, "post")  # regenerate token
            )

            try:
                self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
                if self.controller.verbose:
                    self.controller.lsnp_logger.info(f"[POST RETRY] Resent to {peer.display_name} at {peer.ip}")
            except Exception as e:
                self.controller.lsnp_logger.error(f"[POST ERROR] Retry failed for {peer.display_name}: {e}")

        # Wait before next retry
        time.sleep(RETRY_INTERVAL)

    # 3. Report final result
    sent_count = sum(1 for mid in message_map.values() if ack_events[mid].is_set())
    self.controller.lsnp_logger.info(f"[POST COMPLETE] Sent to {sent_count}/{len(self.controller.followers)} followers")

    # Cleanup ack_events
    for mid in message_map.values():
        if mid in self.controller.ack_events:
            del self.controller.ack_events[mid]

  def toggle_like(self, post_timestamp_id: str, owner_name: str):
    # Resolve short name to full_user_id using peer_map
    full_owner_id = None
    for peer in self.controller.peer_map.values():
        if peer.display_name == owner_name or peer.user_id.startswith(f"{owner_name}@"):
            full_owner_id = peer.user_id
            break

    if not full_owner_id:
        self.controller.lsnp_logger.error(f"[LIKE ERROR] Unknown post owner: {owner_name}")
        return

    peer = self.controller.peer_map[full_owner_id]
    timestamp = str(int(time.time()))

    # Determine action (LIKE or UNLIKE)
    action = "UNLIKE" if post_timestamp_id in self.controller.post_likes else "LIKE"
    token = generate_token(self.controller.full_user_id, "like")

    # Build LIKE message
    msg = make_like_message(
        from_id=self.controller.full_user_id,
        to_id=full_owner_id,
        post_timestamp_id=post_timestamp_id,
        action=action,
        timestamp=timestamp,
        token=token
    )

    # ACK handling
    ack_event = threading.Event()
    self.controller.ack_events[timestamp] = ack_event

    for attempt in range(RETRY_COUNT):
        self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
        if self.controller.verbose:
            self.controller.lsnp_logger.info(f"[{action} SEND] Attempt {attempt + 1} to {peer.display_name} at {peer.ip}")

        if ack_event.wait(RETRY_INTERVAL):
            if action == "LIKE":
                self.controller.post_likes.add(post_timestamp_id)
                self.controller.lsnp_logger.info(f"[LIKE CONFIRMED] Post {post_timestamp_id} by {peer.display_name}")
            else:
                self.controller.post_likes.remove(post_timestamp_id)
                self.controller.lsnp_logger.info(f"[UNLIKE CONFIRMED] Post {post_timestamp_id} by {peer.display_name}")
            del self.controller.ack_events[timestamp]
            return

        if self.controller.verbose:
            self.controller.lsnp_logger.info(f"[{action} RETRY] {attempt + 1} for {peer.display_name}")

    self.controller.lsnp_logger.error(f"[{action} FAILED] Could not send {action} to {peer.display_name}")
    del self.controller.ack_events[timestamp]

  def revoke_token(self, token: str):
    """Revoke a token by removing it from the token store"""
    if not token:
        self.controller.lsnp_logger.error("[ERROR] No token provided for revocation.")
        return
    
    if token in state.tokens:
        del state.tokens[token]
        self.controller.lsnp_logger.info(f"[TOKEN REVOKED] {token}")
    else:
        self.controller.lsnp_logger.warning(f"[TOKEN NOT FOUND] {token} not found in active tokens.")

  def run(self):
    self.controller.lsnp_logger.info(f"LSNP Peer started as {self.controller.full_user_id}")
    self.controller.lsnp_logger.info("Type 'help' for commands.")
    cmd = ""
    while True:
      try:
          cmd = self.controller.lsnp_logger.input("", end="").strip()
          if cmd == "help":
            help_str = ("\nCommands:\n"
                        
              "  help                                         - Show this help message\n"
              "  peers                                        - List discovered peers\n"
              "  dms                                          - Show inbox\n"
              "  dm <user> <msg>                              - Send direct message\n"
              
              "===| Post Commands |===\n"
              "  follow <user>                                - Follow a user\n"
              "  unfollow <user>                              - Unfollow a user\n"
              "  post <msg>                                   - Create a new post to followers\n"
              "  like <post_timestamp_id> <owner_id>          - Like or unlike a post\n"
              "  ttl <seconds>                                - Set TTL for posts (default: 60)\n"
              
              "===| File Transfer Commands |===\n"
              "  sendfile <user> <filepath> [description]                  - Send a file\n"
              "  acceptfile <fileid>                          - Accept a pending file offer\n"
              "  rejectfile <fileid>                          - Reject a pending file offer\n"
              "  pendingfiles                                 - List pending file offers\n"
              "  transfers                                    - List active file transfers\n"
              
              "===| Tic Tac Toe Commands |===\n"
              "  game                                         - Show Tic Tac Toe commands\n"
              "  game list                                    - List active Tic Tac Toe games\n"
              "  game invite <user> <X|O>                     - Invite to Tic Tac Toe game\n"
              "  game move <gameid> <position 0-8>            - Make a move in Tic Tac Toe\n"
              "  game forfeit <gameid>                        - Forfeit a Tic Tac Toe game\n"
              
              "===| Group Commands |===\n"
              "  group list <name>                            - Show details of a group\n"
              "  group create <name> <users>                  - Creates a group with one or more users\n"
              "  group add <name> <user>                      - Adds a user to the group\n"
              "  group remove <name> <user>                   - Removes a user from the group\n"
              "  group message <name> <message>               - Sends a message to the group\n"
              "  Note: Group names and messages must be enclosed in quotation marks.\n"
              "  Note: Users must be separated by comma.\n"
              
              "===| Misc Commands |===\n"
              "  broadcast                                    - Send profile broadcast\n"
              "  ping                                         - Send ping\n"
              "  verbose                                      - Toggle verbose mode\n"
              "  ipstats                                      - Show IP statistics\n"
              "  quit                                         - Exit")
            self.controller.lsnp_logger.info(help_str)
          elif cmd == "peers":
            self.list_peers()
          elif cmd == "dms":
            self.show_inbox()
          elif cmd.startswith("dm "):
            parts = cmd.split(" ", 2)
            if len(parts) < 3:
              self.controller.lsnp_logger.info("Usage: dm <user_id> <message>")
              continue
            _, recipient_id, message = parts
            self.send_dm(recipient_id, message)
          elif cmd.startswith("post "):
            parts = cmd.split(" ", 1)
            if len(parts) < 2:
              self.controller.lsnp_logger.info("Usage: post <message>")
              continue
            _, message = parts
            self.send_post(message)
          elif cmd.startswith("like "):
            parts = cmd.split(" ")
            if len(parts) != 3:
                self.controller.lsnp_logger.info("Usage: like <post_timestamp_id> <owner_id>")
                continue

            _, post_timestamp_id, owner_id = parts
            self.toggle_like(post_timestamp_id, owner_id)
          elif cmd.startswith("ttl "):
            parts = cmd.split(" ", 1)
            if len(parts) < 2 or not parts[1].isdigit():
                self.controller.lsnp_logger.info("Usage: ttl <seconds>")
                continue
            state.ttl = int(parts[1])
            self.controller.lsnp_logger.info(f"[TTL] TTL updated to {state.ttl} seconds")
          elif cmd.startswith("follow "):
            parts = cmd.split(" ", 2)
            if len(parts) < 2:
              self.controller.lsnp_logger.info("Usage: follow <user_id>")
              continue
            _, user_id = parts
            self.follow(user_id)
          elif cmd.startswith("unfollow "):
            parts = cmd.split(" ", 2)
            if len(parts) < 2:
              self.controller.lsnp_logger.info("Usage: unfollow <user_id>")
              continue
            _, user_id = parts
            self.unfollow(user_id)
          elif cmd.startswith("sendfile "):
                parts = cmd.split(" ", 3)
                if len(parts) < 3:
                    self.controller.lsnp_logger.info("Usage: sendfile <user_id> <filepath> [description]")
                    continue
                _, recipient_id, filepath = parts[:3]
                description = parts[3] if len(parts) > 3 else ""
                self.controller.file_manager.send_file(recipient_id, filepath, description)
          elif cmd.startswith("acceptfile "):
              parts = cmd.split(" ", 1)
              if len(parts) < 2:
                  self.controller.lsnp_logger.info("Usage: acceptfile <fileid>")
                  continue
              _, file_id = parts
              self.controller.file_manager.accept_file(file_id)
          elif cmd.startswith("rejectfile "):
              parts = cmd.split(" ", 1)
              if len(parts) < 2:
                  self.controller.lsnp_logger.info("Usage: rejectfile <fileid>")
                  continue
              _, file_id = parts
              self.controller.file_manager.reject_file(file_id)
          elif cmd == "pendingfiles":
              self.controller.file_manager.list_pending_files()
          elif cmd == "transfers":
              self.controller.file_manager.list_active_transfers()
          elif cmd == "broadcast":
              self.broadcast_profile()
          elif cmd.startswith("revoke "):
              parts = cmd.split(" ", 1)
              if len(parts) < 2:
                  self.controller.lsnp_logger.info("Usage: revoke <token>")
                  continue
              _, token = parts
              self.revoke_token(token)
          elif cmd.startswith("group "):
                  # Select "group" command
                  # Select between "help", "create", "add", "remove", "message"
                  if cmd == "group help":
                      group_help_str = ("\nCommands:\n"
                            "  group list <name>              - Show details of a group\n"
                            "  group create <name> <users>    - Creates a group with one or more users\n"
                            "  group add <name> <user>        - Adds a user to the group\n"
                            "  group remove <name> <user>     - Removes a user from the group\n"
                            "  group message <name> <message> - Sends a message to the group\n"
                            "  Note: Group names and messages must be enclosed in quotation marks.\n"
                            "  Note: Users must be separated by comma.")
                      self.controller.lsnp_logger.info(group_help_str)
                      continue
                  parts = shlex.split(cmd)
                  group_index = -1
                  for index, group in enumerate(self.controller.groups):
                      if group.group_name == parts[2]:
                          group_index = index
                          break
                  if group_index == -1 and parts[1] != "create":
                      self.controller.lsnp_logger.info(f"No group exists.")
                      continue
                  if parts[1] == "lists":
                      for group in self.controller.groups:
                          self.controller.lsnp_logger.info(f"Group Name: {group.group_name}, Owner: {group.owner_id}, Members: {len(group.members)}")      
                  elif parts[1] == "list":
                      self.controller.lsnp_logger.info(f"{group_index}")       
                      self.controller.lsnp_logger.info(f"Group Name: {self.controller.groups[group_index].group_name}")
                      self.controller.lsnp_logger.info(f"Group Owner: {self.controller.groups[group_index].owner_id}")
                      self.controller.lsnp_logger.info(f"Group Members:")
                      for member in self.controller.groups[group_index].members:
                          self.controller.lsnp_logger.info(f"{member}")
                      continue
                  if len(parts) != 4:
                      self.controller.lsnp_logger.info("Usage: group <cmd> <name> <args>")
                      continue
                  _, grp_cmd, grp_name, args = parts
                  if grp_cmd == "create":
                      self.controller.group_manager.group_create(grp_name, args)
                  elif grp_cmd == "add":
                      if self.controller.groups[group_index].owner_id != self.controller.full_user_id:
                          self.controller.lsnp_logger.info("No permission to manage group.")
                      else:
                          self.controller.group_manager.group_add(group_index, args)
                  elif grp_cmd == "remove":
                      if self.controller.groups[group_index].owner_id != self.controller.full_user_id:
                          self.controller.lsnp_logger.info("No permission to manage group.")
                      else:
                          self.controller.group_manager.group_remove(group_index, args)
                  elif grp_cmd == "message":
                      self.controller.group_manager.group_message(group_index, args)
                  else:
                      self.controller.lsnp_logger.info("Usage: group <cmd> <args>")
                      continue
          elif cmd == "game":
              self.controller.lsnp_logger.info("Usage: game invite <user> <X|O>, "
                                "game move <gameid> <position 0-8>, "
                                "game forfeit <gameid>")
          elif cmd == "game list":
              if not self.controller.tictactoe_games:
                  self.controller.lsnp_logger.info("No active Tic Tac Toe games.")
              else:
                  self.controller.lsnp_logger.info("Active Tic Tac Toe games:")
                  for gameid, game in self.controller.tictactoe_games.items():
                      self.controller.lsnp_logger.info(f"- Game ID: {gameid}, Opponent: {game['opponent']}, "
                                        f"Symbol: {game['my_symbol']}, Turn: {game['turn']}")
          elif cmd.startswith("game invite "):
              parts = cmd.split(" ")
              if len(parts) != 4:
                  self.controller.lsnp_logger.info("Usage: game invite <user> <X|O>")
              else:
                  _, _, user, symbol = parts
                  self.controller.gamemanager.send_tictactoe_invite(user, symbol)
              
          elif cmd.startswith("game move "):
              parts = cmd.split(" ")
              if len(parts) != 4:
                  self.controller.lsnp_logger.info("Usage: game move <gameid> <position 0-8>")
              else:
                  _, _, gameid, pos = parts
                  self.controller.gamemanager.send_tictactoe_move(gameid, int(pos))

          elif cmd.startswith("game forfeit "):
              parts = cmd.split(" ")
              if len(parts) != 3:
                  self.controller.lsnp_logger.info("Usage: game forfeit <gameid>")
              else:
                  _, _, gameid = parts
                  self.controller.gamemanager.send_forfeit_tictactoe(gameid)
          elif cmd == "ping":
              self.send_ping()
          elif cmd == "verbose":
              self.controller.verbose = not self.controller.verbose
              self.controller.lsnp_logger.info(f"Verbose mode {'on' if self.controller.verbose else 'off'}")
          elif cmd == "ipstats":
              self.show_ip_stats()
          elif cmd == "quit":
              break 
          else:
            self.controller.lsnp_logger.warning("Unknown command. Type 'help' for available commands.")
      except KeyboardInterrupt:
        break
      except Exception as e:
        self.controller.lsnp_logger.error(f"Error: {e}")

    self.controller.zeroconf.close()
    if cmd != "quit": print("") # For better looks

    stats = self.controller.ip_tracker.get_ip_stats()
    self.controller.lsnp_logger.info(f"Session totals - IPs: {stats['total_known_ips']}, "
                  f"Connections: {stats['total_connection_attempts']}")	
    self.controller.lsnp_logger.critical("Peer terminated.")