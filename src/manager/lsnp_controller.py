import socket
import threading
import time
import json
import uuid
import base64
import os
import math
import shlex
from typing import Dict, List, Callable, Tuple, Optional, Set
from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser, ServiceListener
from src.protocol.types.messages.message_formats import *
from src.ui import logging
from src.config import *
from src.protocol import *
from src.utils import *
from src.network import *
from src.game import *

import src.manager.state as state

logger = logging.Logger()

LSNP_CODENAME = 'LSNPCON'
LSNP_PREFIX = f'[green][{LSNP_CODENAME}][/]'



LSNP_BROADCAST_PERIOD_SECONDS = 300
MAX_CHUNK_SIZE = 1024  # Maximum chunk size in bytes

class FileTransfer:
    def __init__(self, file_id: str, filename: str, filesize: int, filetype: str, 
                 total_chunks: int, sender_id: str, description: str = ""):
        self.file_id = file_id
        self.filename = filename
        self.filesize = filesize
        self.filetype = filetype
        self.total_chunks = total_chunks
        self.sender_id = sender_id
        self.description = description
        self.chunks: Dict[int, bytes] = {}
        self.received_chunks = 0
        self.accepted = False
        self.completed = False
        self.timestamp = int(time.time())
        

    def add_chunk(self, chunk_index: int, data: bytes) -> bool:
        if not self.accepted:
            return False
        
        if chunk_index not in self.chunks:
            self.chunks[chunk_index] = data
            self.received_chunks += 1
        
        if self.received_chunks == self.total_chunks:
            self.completed = True
        
        return True

    def get_assembled_data(self) -> Optional[bytes]:
        if not self.completed:
            return None
        
        assembled = b''
        for i in range(self.total_chunks):
            if i not in self.chunks:
                return None
            assembled += self.chunks[i]
        
        return assembled


class Group:
    def __init__(self, group_id: str, group_name: str, owner_id: str, members: List[str]):
        self.group_id: str = group_id
        self.group_name: str = group_name
        self.owner_id: str = owner_id
        self.members: List[str] = members
        self.created_at: str = str(int(time.time()))

class LSNPController:
    def __init__(self, user_id: str, display_name: str, port: int = LSNP_PORT, verbose: bool = True, avatar_path: str|None=""):
      self.user_id = user_id
      self.display_name = display_name
      self.port = port
      self.avatar_path = avatar_path
      self.verbose = verbose
      self.ip = self._get_own_ip()
      self.full_user_id = f"{self.user_id}@{self.ip}"
      self.peer_map: Dict[str, Peer] = {}
      self.inbox: List[str] = []
      
      self.groups: List[Group] = []
      self.followers: List[str] = []
      self.ack_events: Dict[str, threading.Event] = {}
      self.project_root = self._get_project_root()
      
      # File transfer management
      self.active_transfers: Dict[str, FileTransfer] = {}
      self.pending_offers: Dict[str, FileTransfer] = {}

      self.file_response_events: Dict[str, threading.Event] = {}
      self.file_responses: Dict[str, str] = {}

      self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) # Enables broadcasting
      self.socket.bind(("", self.port))
      self.following: Set[str] = set()      # Who we are following
      self.post_likes: Set[str] = set()
      self.zeroconf = Zeroconf()
      self._register_mdns()
      self._start_threads()
      
      self.tictactoe_games = {}  
      self.lsnp_logger = logger.get_logger(user_id)
      self.gamemanager = GameManager(self.lsnp_logger)
      self.ip_tracker = IPAddressTracker()

      if self.verbose:
          self.lsnp_logger.info(f"[INIT] Peer initialized: {self.full_user_id}")


    def _get_project_root(self):
        """Get the project root directory (CSNETWK-MCO3)"""
        # Start from current file location
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Go up directories until we find the project root
        while current_dir != os.path.dirname(current_dir):  # Stop at filesystem root
            if os.path.basename(current_dir) == "CSNETWK-MCO3":
                return current_dir
            # Also check if we're in the project by looking for key files/folders
            if os.path.exists(os.path.join(current_dir, "pyproject.toml")) and \
               os.path.exists(os.path.join(current_dir, "src")) and \
               os.path.exists(os.path.join(current_dir, "files")):
                return current_dir
            current_dir = os.path.dirname(current_dir)
        
        # Fallback: assume we're running from src/manager and go up two levels
        return os.path.dirname(os.path.dirname(current_dir))

    def _get_own_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except:
            return "127.0.0.1"
        finally:
            s.close()

    def _register_mdns(self):
      info = ServiceInfo(
        MDNS_SERVICE_TYPE,
        f"{self.user_id}_at_{self.ip.replace('.', '_')}.{MDNS_SERVICE_TYPE}",
        addresses=[socket.inet_aton(self.ip)],
        port=self.port,
        properties={
          "user_id": self.user_id,
          "display_name": self.display_name
        }
      )
      self.zeroconf.register_service(info)
      if self.verbose:
        self.lsnp_logger.info(f"[mDNS] Registered: {info.name}")

    def _start_threads(self):
      threading.Thread(target=self._listen, daemon=True).start()
      listener = PeerListener(self.peer_map, self._on_peer_discovered)
      ServiceBrowser(self.zeroconf, MDNS_SERVICE_TYPE, listener)
      if self.verbose:
        self.lsnp_logger.info("[mDNS] Discovery started")

    def _listen(self):
        while True:
            try:
                data: bytes
                addr: Tuple[str, int]
                data, addr = self.socket.recvfrom(BUFFER_SIZE)
                sender_ip, sender_port = addr
    
                self.ip_tracker.log_connection_attempt(sender_ip, sender_port, success=True)
                raw = data.decode()
                data_size = len(data)
                if self.verbose:
                  self.lsnp_logger.info(f"[RECV] From {addr}: \n{raw[:100]}{'...' if len(raw) > 100 else ''}")
                
                # All messages should be in key-value format now
                if "TYPE: " in raw:
                    kv = parse_kv_message(raw)
                    self._handle_kv_message(kv, addr)
                    self.ip_tracker.log_message_flow(sender_ip, self.ip, kv.get("TYPE", "UNKNOWN"), data_size)
                else:
                    # Fallback for any legacy JSON messages
                    msg = json.loads(raw)
                    self._handle_json_message(msg, addr)
                    self.ip_tracker.log_message_flow(sender_ip, self.ip, msg.get("type", "JSON"), data_size)
            except Exception as e:
                if self.verbose:
                    self.lsnp_logger.info(f"[ERROR] Malformed message from {addr}: {e}")

    def _failed_security_check(self, from_id: str, sender_ip: str) -> bool:
        if from_id and "@" in from_id:
            from_ip = from_id.split("@")[-1]
            if from_ip != sender_ip:
                self.lsnp_logger.warning(f"[SECURITY] FROM field IP {from_ip} does not match sender IP {sender_ip}. Dropping message.")
                return True
            return False
        return True

    def _handle_kv_message(self, kv: dict, addr: Tuple[str, int]):
        msg_type = kv.get("TYPE")
        sender_ip, sender_port = addr

        if msg_type == "PROFILE":
            from_id = kv.get("USER_ID", "")
            display_name = kv.get("DISPLAY_NAME", "")
            avatar_data = kv.get("AVATAR_DATA")
            avatar_type = kv.get("AVATAR_TYPE")

            ip = addr[0]
            port = addr[1]


            self.ip_tracker.log_new_ip(sender_ip, from_id, "profile_message")
            if from_id not in self.peer_map:
                peer = Peer(from_id, display_name, ip, port)
                peer.avatar_data = avatar_data
                peer.avatar_type = avatar_type
                self.peer_map[from_id] = peer
            else:
                # Update existing peer
                self.peer_map[from_id].display_name = display_name
                self.peer_map[from_id].avatar_data = avatar_data
                self.peer_map[from_id].avatar_type = avatar_type

            if self.verbose:
                self.lsnp_logger.info(f"[PROFILE] {display_name} ({from_id}) joined from {ip}")
                
        elif msg_type == "DM":
            from_id = kv.get("FROM", "")
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            to_id = kv.get("TO", "")
            token = kv.get("TOKEN", "")

            # Verify this message is for us
            if self.verbose:
                self.lsnp_logger.info(f"[DM] Received from ${from_id} to ${to_id}")
            if to_id != self.full_user_id:
                if self.verbose:
                    self.lsnp_logger.info(f"[DM IGNORED] Not for us: {to_id}")
                return
                
            if not validate_token(token, "chat"):
                if self.verbose:
                    self.lsnp_logger.info(f"[DM REJECTED] Invalid token from {from_id}")
                return
            content = kv.get("CONTENT", "")
            message_id = kv.get("MESSAGE_ID", "")
            timestamp = kv.get("TIMESTAMP", "")
            
            # Get display name for prettier output
            display_name = from_id.split('@')[0]  # Default to username part
            if self.verbose:
                self.lsnp_logger.info(f"{display_name}: {content}")
            # Check if it's from ourselves
            if from_id == self.full_user_id:
                display_name = self.display_name
            else:
                # Look up in peer_map for other peers
                for peer in self.peer_map.values():
                    if peer.user_id == from_id:
                        display_name = peer.display_name
                        break
            
            self.lsnp_logger.info(f"{display_name}: {content}")
            self.inbox.append(f"[{timestamp}] {display_name}: {content}")
            self.lsnp_logger.debug(f"Send Ack")
            self._send_ack(message_id, addr)
  
        elif msg_type == "FOLLOW":
            from_id = kv.get("FROM", "")
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            to_id = kv.get("TO", "")
            message_id = kv.get("MESSAGE_ID", "")
            display_name = from_id.split('@')[0]
            
            if to_id == self.full_user_id:
                self.lsnp_logger.info(f"[NOTIFY] {display_name} ({from_id}) is now following you.")
                self.inbox.append(f"User {display_name} started following you.")
                self._send_ack(message_id, addr)
                self.followers.append(from_id)

        elif msg_type == "UNFOLLOW":
            from_id = kv.get("FROM", "")
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            message_id = kv.get("MESSAGE_ID", "")
            display_name = from_id.split('@')[0]
            self.lsnp_logger.info(f"[NOTIFY] {display_name} ({from_id}) has unfollowed you.")
            self.inbox.append(f"User {display_name} unfollowed you.")
            self._send_ack(message_id, addr)
            self.followers.remove(from_id)
        
        elif msg_type == "POST":
            from_id = kv.get("USER_ID", "")
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            token = kv.get("TOKEN", "")
            message_id = kv.get("MESSAGE_ID", "")
            if not validate_token(token, "post"):
                    self.lsnp_logger.warning(f"[POST REJECTED] Invalid token from {from_id}")
                    return
            content = kv.get("CONTENT", "")
            timestamp = kv.get("TIMESTAMP", "")
            display_name = None
            for peer in self.peer_map.values():
                    if peer.user_id == from_id:
                            display_name = peer.display_name
                            break
            if not display_name:
              display_name = from_id.split('@')[0]
            self.lsnp_logger.info(f"[POST] {display_name}: {content}")
            self.inbox.append(f"[{timestamp}] {display_name} (POST): {content}")
            self._send_ack(message_id, addr)

        # File transfer message handlers
        elif msg_type == "FILE_OFFER":
            from_id = kv.get("FROM", "")
            if self._failed_security_check(from_id, sender_ip):
                return
            
            self._handle_file_offer(kv, addr)
            
        elif msg_type == "FILE_CHUNK":
            from_id = kv.get("FROM", "")
            if self._failed_security_check(from_id, sender_ip):
                return
            
            self._handle_file_chunk(kv, addr)
            
        elif msg_type == "FILE_RECEIVED":
            from_id = kv.get("FROM", "")
            if self._failed_security_check(from_id, sender_ip):
                return
            
            self._handle_file_received(kv, addr)

        elif msg_type == "ACK":
            
            
            message_id = kv.get("MESSAGE_ID", "")
            if message_id in self.ack_events:
                self.ack_events[message_id].set()
                if self.verbose:
                    self.lsnp_logger.info(f"[ACK] Received for message {message_id}")
        
        elif msg_type == "PING":
            
            
            user_id = kv.get("USER_ID", "")
            if self.verbose:
                self.lsnp_logger.info(f"[PING] From {user_id}")

        elif msg_type == "FILE_ACCEPT":
            from_id = kv.get("FROM", "")
            if self._failed_security_check(from_id, sender_ip):
                return
            
            to_id = kv.get("TO", "")
            file_id = kv.get("FILEID", "")
            token = kv.get("TOKEN", "")
            
            if to_id != self.full_user_id:
                return
            
            if not validate_token(token, "file"):
                del self.pending_offers[file_id] 
                if self.verbose:
                    self.lsnp_logger.info(f"[FILE_ACCEPT REJECTED] Invalid token from {from_id}")
                
                return
            
            # Signal that file was accepted
            if file_id in self.file_response_events:
                self.file_responses[file_id] = "ACCEPTED"
                self.file_response_events[file_id].set()
                if self.verbose:
                    self.lsnp_logger.info(f"[FILE_ACCEPT] Received for {file_id}")

        elif msg_type == "FILE_REJECT":
            from_id = kv.get("FROM", "")
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            to_id = kv.get("TO", "")
            file_id = kv.get("FILEID", "")
            token = kv.get("TOKEN", "")
            
            if to_id != self.full_user_id:
                return
            
            if not validate_token(token, "file"):
                del self.pending_offers[file_id] 
                if self.verbose:
                    self.lsnp_logger.info(f"[FILE_REJECT REJECTED] Invalid token from {from_id}")
                    
                return
            
            # Signal that file was rejected
            if file_id in self.file_response_events:
                self.file_responses[file_id] = "REJECTED"
                self.file_response_events[file_id].set()
                if self.verbose:
                    self.lsnp_logger.info(f"[FILE_REJECT] Received for {file_id}")
        elif msg_type == "LIKE":
            from_id = kv.get("FROM", "");
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            to_id = kv.get("TO", "")
            post_timestamp = kv.get("POST_TIMESTAMP", "")
            action = kv.get("ACTION", "")
            timestamp = kv.get("TIMESTAMP", "")
            token = kv.get("TOKEN", "")
            
            
          
        elif msg_type == "TICTACTOE_INVITE":
            from_id = str(kv.get("FROM"))
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            gameid = str(kv.get("GAMEID"))
            symbol = str(kv.get("SYMBOL"))
            
            self.lsnp_logger.info(f"{from_id.split('@')[0]} is inviting you to play tic-tac-toe.")
            
            self.tictactoe_games[gameid] = {
                "board": [" "] * 9,
                "my_symbol": "O" if symbol == "X" else "X",
                "opponent": from_id,
                "turn": 0,
                "active": True
            }
            self.gamemanager._print_ttt_board(self.tictactoe_games[gameid]["board"])

        elif msg_type == "TICTACTOE_MOVE":
            from_id = str(kv.get("FROM"))
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            gameid = str(kv.get("GAMEID"))
            pos = int(str(kv.get("POSITION")))
            sym = kv.get("SYMBOL")
            game = self.tictactoe_games.get(gameid)
            if game:
                game["board"][pos] = sym
                game["turn"] = int(str(kv.get("TURN")))
                self.gamemanager._print_ttt_board(game["board"])
                winner, line = self.gamemanager._check_ttt_winner(game["board"])
                if winner:
                    self.send_tictactoe_result(gameid, winner, line)

        elif msg_type == "TICTACTOE_RESULT":
            from_id = str(kv.get("FROM"))
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            gameid = kv.get("GAMEID")
            result = kv.get("RESULT")
            line = kv.get("WINNING_LINE", "")
            self.lsnp_logger.info(f"Game {gameid} result: {result}")
            self.lsnp_logger.info(f"Winning line: {line}")
            self.gamemanager._print_ttt_board(self.tictactoe_games[gameid]["board"])
            
            self.tictactoe_games[gameid]["active"] = False
            del self.tictactoe_games[gameid]

        elif msg_type == "GROUP_CREATE":
            from_id: str = kv.get("FROM", "")
            
            from_id = str(kv.get("FROM"))
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            group_id: str = kv.get("GROUP_ID", "")
            group_name: str = kv.get("GROUP_NAME", "")
            members: str = kv.get("MEMBERS", "")
            token: str = kv.get("TOKEN", "")

            parts = members.split(",")

            if self.full_user_id not in parts:
                return
            
            if not validate_token(token, "group"):
                if self.verbose:
                    self.lsnp_logger.info(f"[GROUP_CREATE REJECTED] Invalid token from {from_id}")
                return
            
            group = Group(group_id, group_name, from_id, parts)
            self.groups.append(group)

            self.lsnp_logger.info(f"[GROUP_CREATE] You've been added to \"{group_name}\"")
            if self.verbose:
                self.lsnp_logger.info(f"[GROUP_CREATE] Owner: {from_id}")
                self.lsnp_logger.info(f"[GROUP_CREATE] Members: {members}")

        elif msg_type == "GROUP_ADD":
            from_id: str = kv.get("FROM", "")
            from_id = str(kv.get("FROM"))
            
            if self._failed_security_check(from_id, sender_ip):
                return
            group_id: str = kv.get("GROUP_ID", "")
            group_name: str = kv.get("GROUP_NAME", "")
            add: str = kv.get("ADD", "")
            members: str = kv.get("MEMBERS", "")
            token: str = kv.get("TOKEN", "")

            add_parts = add.split(",")
            member_parts = members.split(",")

            if self.full_user_id not in member_parts:
                return
                            
            if not validate_token(token, "group"):
                if self.verbose:
                    self.lsnp_logger.info(f"[GROUP_ADD REJECTED] Invalid token from {from_id}")
                return

            if self.full_user_id in add_parts:
                group = Group(group_id, group_name, from_id, member_parts)
                self.groups.append(group)
                self.lsnp_logger.info(f"[GROUP_ADD] You've been added to \"{group_name}\"")
            else:
                group_index = -1
                for index, group in enumerate(self.groups):
                    if group.group_id == group_id:
                        group_index = index
                        break
                self.groups[group_index].members = member_parts
                self.lsnp_logger.info(f"[GROUP_ADD] The group \"{self.groups[group_index].group_name}\" member list was updated.")
            if self.verbose:
                self.lsnp_logger.info(f"[GROUP_ADD] Owner: {from_id}")
                self.lsnp_logger.info(f"[GROUP_ADD] Members: {members}")

        elif msg_type == "GROUP_REMOVE":
            from_id: str = kv.get("FROM", "")
            from_id = str(kv.get("FROM"))
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            group_id: str = kv.get("GROUP_ID", "")
            remove: str = kv.get("REMOVE", "")
            token: str = kv.get("TOKEN", "")

            remove_parts = remove.split(",")

            group_index = -1
            for index, group in enumerate(self.groups):
                if group.group_id == group_id:
                    group_index = index
                    break

            if group_index == -1:
                return

            if self.full_user_id not in self.groups[group_index].members:
                return
            
            if not validate_token(token, "group"):
                if self.verbose:
                    self.lsnp_logger.info(f"[GROUP_REMOVE REJECTED] Invalid token from {from_id}")
                return
            
            if self.full_user_id in remove_parts:
                self.lsnp_logger.info(f"[GROUP_REMOVE] You've been removed from \"{self.groups[group_index].group_name}\"")
                self.groups.pop(group_index)
            else:
                for member in remove_parts:
                    self.groups[group_index].members.remove(member)
                self.lsnp_logger.info(f"[GROUP_REMOVE] The group \"{self.groups[group_index].group_name}\" member list was updated.")
            
            if self.verbose:
                members_str = ""
                for member in self.groups[group_index].members:
                    members_str = members_str + ","
                members_str = members_str[:-1]
                self.lsnp_logger.info(f"[GROUP_REMOVE] Owner: {from_id}")
                self.lsnp_logger.info(f"[GROUP_REMOVE] Members: {members_str}")

        elif msg_type == "GROUP_MESSAGE":
            from_id = kv.get("FROM", "")
            
            from_id = str(kv.get("FROM"))
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            group_id: str = kv.get("GROUP_ID", "")
            content = kv.get("CONTENT", "")
            message_id = kv.get("MESSAGE_ID", "")
            token = kv.get("TOKEN", "")

            group_index = -1
            for index, group in enumerate(self.groups):
                if group.group_id == group_id:
                    group_index = index
                    break
            
            if group_index == -1:
                return
            
            if not validate_token(token, "group"):
                if self.verbose:
                    self.lsnp_logger.info(f"[GROUP MESSAGE REJECTED] Invalid token from {from_id}")
                return
            
            self.lsnp_logger.info(f"[\"{self.groups[group_index].group_name}\"] {from_id}: {content}")
            self._send_ack(message_id, addr)


    def _handle_file_offer(self, kv: dict, addr: Tuple[str, int]):
        from_id = kv.get("FROM", "")
        to_id = kv.get("TO", "")
        token = kv.get("TOKEN", "")
        
        # Verify this message is for usf
        if to_id != self.full_user_id:
            if self.verbose:
                self.lsnp_logger.info(f"[FILE_OFFER IGNORED] Not for us: {to_id}")
            return
        
        if not validate_token(token, "file"):
            if self.verbose:
                self.lsnp_logger.info(f"[FILE_OFFER REJECTED] Invalid token from {from_id}")
            return
        
        filename = kv.get("FILENAME", "")
        filesize = int(kv.get("FILESIZE", "0"))
        filetype = kv.get("FILETYPE", "")
        file_id = kv.get("FILEID", "")
        description = kv.get("DESCRIPTION", "")
        
        # Calculate total chunks needed
        total_chunks = math.ceil(filesize / MAX_CHUNK_SIZE)
        
        # Create file transfer object
        transfer = FileTransfer(file_id, filename, filesize, filetype, 
                              total_chunks, from_id, description)
        
        self.pending_offers[file_id] = transfer
        
        # Get sender display name
        sender_name = from_id.split('@')[0]
        for peer in self.peer_map.values():
            if peer.user_id == from_id:
                sender_name = peer.display_name
                break
        
        self.lsnp_logger.info(f"User {sender_name} is sending you a file do you accept?")
        if self.verbose:
            self.lsnp_logger.info(f"[FILE_OFFER] {filename} ({filesize} bytes) from {sender_name}")

    def _handle_file_chunk(self, kv: dict, addr: Tuple[str, int]):
        from_id = kv.get("FROM", "")
        to_id = kv.get("TO", "")
        token = kv.get("TOKEN", "")
        
        # Verify this message is for us
        if to_id != self.full_user_id:
            return
        
        if not validate_token(token, "file"):
            if self.verbose:
                self.lsnp_logger.info(f"[FILE_CHUNK REJECTED] Invalid token from {from_id}")
            return
        
        file_id = kv.get("FILEID", "")
        chunk_index = int(kv.get("CHUNK_INDEX", "0"))
        total_chunks = int(kv.get("TOTAL_CHUNKS", "0"))
        chunk_size = int(kv.get("CHUNK_SIZE", "0"))
        data_b64 = kv.get("DATA", "")
        
        # Check if we have an active transfer for this file
        transfer = self.active_transfers.get(file_id)
        if not transfer:
            # Ignore chunks for files we haven't accepted
            if self.verbose:
                self.lsnp_logger.info(f"[FILE_CHUNK IGNORED] No active transfer for {file_id}")
            return
        
        try:
            chunk_data = base64.b64decode(data_b64)
            success = transfer.add_chunk(chunk_index, chunk_data)
            
            if self.verbose:
                self.lsnp_logger.info(f"[FILE_CHUNK] {chunk_index+1}/{total_chunks} for {transfer.filename}")
            
            # Check if transfer is complete
            if transfer.completed:
                self._complete_file_transfer(transfer, addr)
                
        except Exception as e:
            if self.verbose:
                self.lsnp_logger.info(f"[FILE_CHUNK ERROR] Failed to process chunk: {e}")

    def _handle_file_received(self, kv: dict, addr: Tuple[str, int]):
        file_id = kv.get("FILEID", "")
        status = kv.get("STATUS", "")
        
        if self.verbose:
            self.lsnp_logger.info(f"[FILE_RECEIVED] {file_id} - {status}")

    def _complete_file_transfer(self, transfer: FileTransfer, sender_addr: Tuple[str, int]):
        """Complete a file transfer and save the file"""
        try:
            assembled_data = transfer.get_assembled_data()
            if not assembled_data:
                return
            
            # Create user-specific downloads directory at project root
            user_downloads_dir = os.path.join(self.project_root, "lsnp_data", self.full_user_id, "downloads")
            os.makedirs(user_downloads_dir, exist_ok=True)
            
            # Save the file
            file_path = os.path.join(user_downloads_dir, transfer.filename)
            with open(file_path, 'wb') as f:
                f.write(assembled_data)
            
            self.lsnp_logger.info(f"File transfer of {transfer.filename} is complete")
            self.lsnp_logger.info(f"File saved to: {file_path}")
            
            # Send FILE_RECEIVED confirmation
            self._send_file_received(transfer.file_id, transfer.sender_id, "COMPLETE")
            
            # Clean up
            if transfer.file_id in self.active_transfers:
                del self.active_transfers[transfer.file_id]
                
        except Exception as e:
            self.lsnp_logger.error(f"[FILE_TRANSFER ERROR] Failed to complete transfer: {e}")

    def _send_file_received(self, file_id: str, recipient_id: str, status: str):
        """Send FILE_RECEIVED message"""
        if recipient_id not in self.peer_map:
            return
        
        peer = self.peer_map[recipient_id]
        timestamp = int(time.time())
        
        msg = f"TYPE: FILE_RECEIVED\nFROM: {self.full_user_id}\nTO: {recipient_id}\nFILEID: {file_id}\nSTATUS: {status}\nTIMESTAMP: {timestamp}\n"
        
        try:
            self.socket.sendto(msg.encode(), (peer.ip, peer.port))
            if self.verbose:
                self.lsnp_logger.info(f"[FILE_RECEIVED SENT] {file_id} - {status}")
        except Exception as e:
            if self.verbose:
                self.lsnp_logger.info(f"[FILE_RECEIVED ERROR] {e}")

    def _handle_json_message(self, msg: dict, addr):
        # Legacy handler for any remaining JSON messages
        msg_type = msg.get("type")
        sender_id = msg.get("user_id")

        if msg_type == "DM":
            token = msg.get("token", "")
            if not validate_token(token):
                self.lsnp_logger.warning(f"[DM REJECTED] Invalid token from {sender_id}")
                return
            content = msg.get("content")
            message_id = msg.get("message_id")
            timestamp = msg.get("timestamp")
            self.lsnp_logger.info(f"{sender_id}: {content}")
            self.inbox.append(f"[{timestamp}] {sender_id}: {content}")
            self._send_ack_json(sender_id, addr, message_id)

        elif msg_type == "ACK":
            message_id = msg.get("message_id")
            if message_id in self.ack_events:
                self.ack_events[message_id].set()

    def _send_ack(self, message_id: str, addr):
        ack_msg = make_ack_message(message_id)
        self.socket.sendto(ack_msg.encode(), addr)
        
        if self.verbose:
            self.lsnp_logger.info(f"[ACK SENT] For message {message_id} to {addr}")

    def _send_ack_json(self, sender_id, addr, message_id):
        # Legacy JSON ACK for compatibility
        ack = {
            "type": "ACK",
            "user_id": self.user_id,
            "message_id": message_id
        }
        self.socket.sendto(json.dumps(ack).encode(), addr)

    def _on_peer_discovered(self, peer: Peer):
        self.ip_tracker.log_new_ip(peer.ip, peer.user_id, "mdns_discovery")
        
        if self.verbose:
            self.lsnp_logger.info(f"[DISCOVERED] {peer.display_name} ({peer.user_id})")

    def _send_file_response(self, recipient_id: str, file_id: str, response_type: str):
        """Send FILE_ACCEPT or FILE_REJECT message"""
        if recipient_id not in self.peer_map:
            return
        
        peer = self.peer_map[recipient_id]
        timestamp = int(time.time())
        token = generate_token(self.full_user_id, "file")
        
        msg = (f"TYPE: {response_type}\n"
            f"FROM: {self.full_user_id}\n"
            f"TO: {recipient_id}\n"
            f"FILEID: {file_id}\n"
            f"TOKEN: {token}\n"
            f"TIMESTAMP: {timestamp}\n")
        
        try:
            self.socket.sendto(msg.encode(), (peer.ip, peer.port))
            if self.verbose:
                self.lsnp_logger.info(f"[{response_type} SENT] {file_id}")
        except Exception as e:
            if self.verbose:
                self.lsnp_logger.info(f"[{response_type} ERROR] {e}")

    def accept_file(self, file_id: str):
        """Accept a pending file offer"""
        if file_id not in self.pending_offers:
            self.lsnp_logger.error(f"[ERROR] No pending file offer with ID: {file_id}")
            return
        
        transfer = self.pending_offers[file_id]
        transfer.accepted = True
        self.active_transfers[file_id] = transfer
        del self.pending_offers[file_id]
        
        # Send FILE_ACCEPT message to sender
        self._send_file_response(transfer.sender_id, file_id, "FILE_ACCEPT")
        
        self.lsnp_logger.info(f"[FILE ACCEPTED] {transfer.filename} from {transfer.sender_id.split('@')[0]}")

    def reject_file(self, file_id: str):
        """Reject a pending file offer"""
        if file_id not in self.pending_offers:
            self.lsnp_logger.error(f"[ERROR] No pending file offer with ID: {file_id}")
            return
        
        transfer = self.pending_offers[file_id]
        
        # Send FILE_REJECT message to sender
        self._send_file_response(transfer.sender_id, file_id, "FILE_REJECT")
        
        del self.pending_offers[file_id]
        
        self.lsnp_logger.info(f"[FILE REJECTED] {transfer.filename} from {transfer.sender_id.split('@')[0]}")

    def send_file(self, recipient_id: str, file_path: str, description: str = ""):
        """Send a file to another user"""
        # Accept both formats: "user" or "user@ip"
        if "@" not in recipient_id:
            # Find the full user_id in peer_map
            full_recipient_id = None
            for user_id in self.peer_map:
                if user_id.startswith(f"{recipient_id}@"):
                    full_recipient_id = user_id
                    break
            if not full_recipient_id:
                self.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
                return
            recipient_id = full_recipient_id

        if recipient_id not in self.peer_map:
            self.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
            return

        # Check if file_path is absolute or relative
        if not os.path.isabs(file_path):
            # If relative, first check in the 'files' folder at project root
            files_folder_path = os.path.join(self.project_root, "files", file_path)
            if os.path.exists(files_folder_path):
                file_path = files_folder_path
            else:
                # If not in files folder, make it relative to project root
                project_file_path = os.path.join(self.project_root, file_path)
                if os.path.exists(project_file_path):
                    file_path = project_file_path
                else:
                    self.lsnp_logger.error(f"[ERROR] File not found: {file_path}")
                    self.lsnp_logger.info(f"[HINT] Place files in: {os.path.join(self.project_root, 'files')}")
                    return

        if not os.path.exists(file_path):
            self.lsnp_logger.error(f"[ERROR] File not found: {file_path}")
            return

        peer = self.peer_map[recipient_id]
        
        try:
            # Read file
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            
            # Generate file metadata
            file_id = str(uuid.uuid4())
            filename = os.path.basename(file_path)
            filesize = len(file_data)
            filetype = self._get_file_type(filename)
            timestamp = int(time.time())
            token = generate_token(self.full_user_id, "file")
            response_event = threading.Event()
            self.file_response_events[file_id] = response_event
            self.file_responses[file_id] = ""
            
            # Calculate chunks
            total_chunks = math.ceil(filesize / MAX_CHUNK_SIZE)
            
            # Send FILE_OFFER
            offer_msg = (f"TYPE: FILE_OFFER\n"
                        f"FROM: {self.full_user_id}\n"
                        f"TO: {recipient_id}\n"
                        f"FILENAME: {filename}\n"
                        f"FILESIZE: {filesize}\n"
                        f"FILETYPE: {filetype}\n"
                        f"FILEID: {file_id}\n"
                        f"DESCRIPTION: {description}\n"
                        f"TIMESTAMP: {timestamp}\n"
                        f"TOKEN: {token}\n")
            
            self.socket.sendto(offer_msg.encode(), (peer.ip, peer.port))
            self.lsnp_logger.info(f"[FILE OFFER SENT] {filename} to {peer.display_name}")
            
            # Wait a bit for the recipient to accept (in a real implementation, 
            # you might want to wait for an acceptance message)
            if response_event.wait(timeout=60):  # 60 second timeout
                response = self.file_responses.get(file_id)
                
                if response == "ACCEPTED":
                    self.lsnp_logger.info(f"[FILE ACCEPTED] Sending {filename} to {peer.display_name}")
                    
                    # Send file chunks
                    for chunk_index in range(total_chunks):
                        start = chunk_index * MAX_CHUNK_SIZE
                        end = min(start + MAX_CHUNK_SIZE, filesize)
                        chunk_data = file_data[start:end]
                        chunk_b64 = base64.b64encode(chunk_data).decode()
                        
                        chunk_msg = (f"TYPE: FILE_CHUNK\n"
                                f"FROM: {self.full_user_id}\n"
                                f"TO: {recipient_id}\n"
                                f"FILEID: {file_id}\n"
                                f"CHUNK_INDEX: {chunk_index}\n"
                                f"TOTAL_CHUNKS: {total_chunks}\n"
                                f"CHUNK_SIZE: {len(chunk_data)}\n"
                                f"TOKEN: {token}\n"
                                f"DATA: {chunk_b64}\n")
                        
                        self.socket.sendto(chunk_msg.encode(), (peer.ip, peer.port))
                        
                        if self.verbose:
                            self.lsnp_logger.info(f"[FILE CHUNK SENT] {chunk_index+1}/{total_chunks} to {peer.display_name}")
                        
                        time.sleep(0.1)  # Small delay between chunks
                    
                    self.lsnp_logger.info(f"[FILE TRANSFER COMPLETE] {filename} sent to {peer.display_name}")
                    
                elif response == "REJECTED":
                    self.lsnp_logger.info(f"[FILE REJECTED] {peer.display_name} rejected {filename}")
                else:
                    self.lsnp_logger.error(f"[FILE ERROR] Unknown response: {response}")
            else:
                self.lsnp_logger.error(f"[FILE TIMEOUT] No response from {peer.display_name} for {filename}")
            
            # Clean up
            if file_id in self.file_response_events:
                del self.file_response_events[file_id]
            if file_id in self.file_responses:
                del self.file_responses[file_id]
                
        except Exception as e:
            self.lsnp_logger.error(f"[FILE SEND ERROR] {e}")
            # Clean up on error
            if file_id in self.file_response_events:
                del self.file_response_events[file_id]
            if file_id in self.file_responses:
                del self.file_responses[file_id]

    def _get_file_type(self, filename: str) -> str:
        """Get MIME type based on file extension"""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        mime_types = {
            'txt': 'text/plain',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'pdf': 'application/pdf',
            'mp3': 'audio/mpeg',
            'mp4': 'video/mp4',
            'zip': 'application/zip'
        }
        return mime_types.get(ext, 'application/octet-stream')

    def list_pending_files(self):
        """List pending file offers"""
        if not self.pending_offers:
            self.lsnp_logger.info("No pending file offers.")
            return
        
        self.lsnp_logger.info("Pending file offers:")
        for file_id, transfer in self.pending_offers.items():
            sender_name = transfer.sender_id.split('@')[0]
            self.lsnp_logger.info(f"- {transfer.filename} ({transfer.filesize} bytes) from {sender_name}")
            self.lsnp_logger.info(f"  File ID: {file_id}")
            if transfer.description:
                self.lsnp_logger.info(f"  Description: {transfer.description}")

    def list_active_transfers(self):
        """List active file transfers"""
        if not self.active_transfers:
            self.lsnp_logger.info("No active file transfers.")
            return
        
        self.lsnp_logger.info("Active file transfers:")
        for file_id, transfer in self.active_transfers.items():
            sender_name = transfer.sender_id.split('@')[0]
            progress = f"{transfer.received_chunks}/{transfer.total_chunks}"
            self.lsnp_logger.info(f"- {transfer.filename} from {sender_name}: {progress} chunks")

    def send_dm(self, recipient_id: str, content: str):
        # Accept both formats: "user" or "user@ip"
        if "@" not in recipient_id:
            # Find the full user_id in peer_map
            full_recipient_id = None
            for user_id in self.peer_map:
                if user_id.startswith(f"{recipient_id}@"):
                    full_recipient_id = user_id
                    break
            if not full_recipient_id:
                self.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
                return
            recipient_id = full_recipient_id

        if recipient_id not in self.peer_map:
            self.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
            return
        if self.verbose: 
          self.lsnp_logger.info(f"[DM SEND] to {recipient_id}: {content}")
        
        peer = self.peer_map[recipient_id]
        message_id = str(uuid.uuid4())
        token = generate_token(self.full_user_id, "chat")

        msg = make_dm_message(
            from_user_id=self.full_user_id,
            to_user_id=recipient_id,
            content=content,
            message_id=message_id,
            token=token
        )

        ack_event = threading.Event()
        self.ack_events[message_id] = ack_event

        for attempt in range(RETRY_COUNT):
            self.socket.sendto(msg.encode(), (peer.ip, peer.port))
            if self.verbose:
                self.lsnp_logger.info(f"[DM SEND] Attempt {attempt + 1} to {recipient_id} at {peer.ip}")
            
            if ack_event.wait(RETRY_INTERVAL):
                self.lsnp_logger.info(f"[DM SENT] to {peer.display_name} at {peer.ip}")
                del self.ack_events[message_id]
                return
            
            if self.verbose:
                self.lsnp_logger.info(f"[RETRY] {attempt + 1} for {recipient_id} at {peer.ip}")

        self.lsnp_logger.error(f"[FAILED] DM to {peer.display_name} at {peer.ip}")
        del self.ack_events[message_id]

    def play_tictactoe(self, recipient_id: str):
        # Accept both formats: "user" or "user@ip"
        if "@" not in recipient_id:
            # Find the full user_id in peer_map
            full_recipient_id = None
            for user_id in self.peer_map:
                if user_id.startswith(f"{recipient_id}@"):
                    full_recipient_id = user_id
                    break
            if not full_recipient_id:
                self.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
                return
            recipient_id = full_recipient_id

        if recipient_id not in self.peer_map:
            self.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
            return

    def _periodic_profile_broadcast(self):
        while True:
            time.sleep(LSNP_BROADCAST_PERIOD_SECONDS)  # 5 minutes
            if self.peer_map:  # Only broadcast if we have peers
                if self.verbose:
                    self.lsnp_logger.info("Periodic Broadcast - Starting scheduled profile broadcast.")
                self.broadcast_profile()

    def send_ping(self):
        msg = make_ping_message(self.full_user_id)
        # Broadcast ping
        broadcast_addr = self.ip.rsplit('.', 1)[0] + '.255'
  
        try:
            self.socket.sendto(msg.encode(), (broadcast_addr, self.port))
            self.lsnp_logger.info(f"PING BROADCAST: Sent to {broadcast_addr}:{self.port}")    
            if self.verbose:
                self.lsnp_logger.info(f"[PING] Sent to {broadcast_addr}")
        except Exception as e:
            self.lsnp_logger.error(f"PING BROADCAST FAILED: To {broadcast_addr} - {e}")
   
    def list_peers(self):
        if not self.peer_map:
            self.lsnp_logger.info("No peers discovered yet.")
            return
 
        self.lsnp_logger.info(f"Peer List: {len(self.peer_map)} peers active.")
        self.lsnp_logger.info("Available peers:")
        for peer in self.peer_map.values():
            # Show both short and full format
            short_id = peer.user_id.split('@')[0]
            self.lsnp_logger.info(f"- {peer.display_name} ({short_id}) at {peer.ip}: {peer.port}")

    def group_create(self, group_name: str, members: str):
        parts = members.split(",")

        for i, recipient_id in enumerate(parts):
            if "@" not in recipient_id:
                # Find the full user_id in peer_map
                full_recipient_id = None
                for user_id in self.peer_map:
                    if user_id.startswith(f"{recipient_id}@"):
                        full_recipient_id = user_id
                        break
                if not full_recipient_id:
                    self.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
                    return
                parts[i] = full_recipient_id

            if parts[i] not in self.peer_map:
                self.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
                return

        group_id = str(uuid.uuid4())
        group = Group(group_id, group_name, self.full_user_id, parts)
        token = generate_token(self.full_user_id, "group")
        self.groups.append(group)

        msg = make_group_create_message(
            from_user_id = self.full_user_id,
            group_id = group.group_id, 
            group_name = group.group_name, 
            members = parts, 
            token = token
        )

        for member in parts:
            peer = self.peer_map[member]
            try:
                self.socket.sendto(msg.encode(), (peer.ip, peer.port))
                self.lsnp_logger.info(f"[GROUP_CREATE] Added member {peer.ip}:{peer.port}")
            except Exception as e:
                self.lsnp_logger.error("[GROUP_CREATE] FAILED: To add {peer.ip} - {e}")

        self.lsnp_logger.info(f"GROUP CREATE: Group \"{group.group_name}\" successfully created.")
    
        if self.verbose:
            self.lsnp_logger.info(f"[GROUP_CREATE] Group created with {len(group.members) + 1} members.")

    def group_add(self, group_index: int, members: str):
        parts = members.split(",")

        for i, recipient_id in enumerate(parts):
            if "@" not in recipient_id:
                # Find the full user_id in peer_map
                full_recipient_id = None
                for user_id in self.peer_map:
                    if user_id.startswith(f"{recipient_id}@"):
                        full_recipient_id = user_id
                        break
                if not full_recipient_id:
                    self.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
                    return
                parts[i] = full_recipient_id

            if parts[i] not in self.peer_map:
                self.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
                return
        
        for member in parts:
            self.groups[group_index].members.append(member)
        token = generate_token(self.full_user_id, "group")

        members_str = ""
        add_str = ""
        for member in self.groups[group_index].members:
            members_str = members_str + member + ","
        for member in parts:
            add_str = add_str + member + ","
        members_str = members_str[:-1]
        add_str = add_str[:-1]

        msg = make_group_add_message(
            from_user_id = self.full_user_id,
            group_id = self.groups[group_index].group_id,
            group_name = self.groups[group_index].group_name,
            add = add_str, 
            members = members_str,
            token = token
        )

        for member in self.groups[group_index].members:
            peer = self.peer_map[member]
            try:
                self.socket.sendto(msg.encode(), (peer.ip, peer.port))
                if member in parts:
                    self.lsnp_logger.info(f"[GROUP_ADD] Added member {peer.ip}:{peer.port}")
            except Exception as e:
                self.lsnp_logger.error("[GROUP_ADD] FAILED: To add {peer.ip} - {e}")

        self.lsnp_logger.info(f"GROUP ADD: Group \"{self.groups[group_index].group_name}\" successfully added {len(parts)} member(s).")
    
        if self.verbose:
            self.lsnp_logger.info(f"[GROUP_ADD] Group now contains {len(self.groups[group_index].members) + 1} members.")

    def group_remove(self, group_index: int, members: str):
        parts = members.split(",")

        for i, recipient_id in enumerate(parts):
            if "@" not in recipient_id:
                # Find the full user_id in peer_map
                full_recipient_id = None
                for user_id in self.peer_map:
                    if user_id.startswith(f"{recipient_id}@"):
                        full_recipient_id = user_id
                        break
                if not full_recipient_id:
                    self.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
                    return
                parts[i] = full_recipient_id

            if parts[i] not in self.peer_map:
                self.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
                return
        
        for member in parts:
            self.groups[group_index].members.remove(member)
        token = generate_token(self.full_user_id, "group")

        remove_str = ""
        for member in parts:
            remove_str = remove_str + member + ","
        remove_str = remove_str[:-1]

        msg = make_group_remove_message(
            from_user_id = self.full_user_id,
            group_id = self.groups[group_index].group_id,
            remove = remove_str, 
            token = token
        )

        for member in parts:
            peer = self.peer_map[member]
            try:
                self.socket.sendto(msg.encode(), (peer.ip, peer.port))
                self.lsnp_logger.info(f"[GROUP_REMOVE] Removed member {peer.ip}:{peer.port}")
            except Exception as e:
                self.lsnp_logger.error("[GROUP_REMOVE] FAILED: To remove {peer.ip} - {e}")

        for member in self.groups[group_index].members:
            peer = self.peer_map[member]
            try:
                self.socket.sendto(msg.encode(), (peer.ip, peer.port))
            except Exception as e:
                self.lsnp_logger.error("[GROUP_REMOVE] FAILED: To address {peer.ip} - {e}")

        self.lsnp_logger.info(f"GROUP REMOVE: Group \"{self.groups[group_index].group_name}\" successfully removed {len(parts)} member(s).")
    
        if self.verbose:
            self.lsnp_logger.info(f"[GROUP_REMOVE] Group now contains {len(self.groups[group_index].members) + 1} members.")

    def group_message(self, group_index: int, content: str):
        for recipient_id in self.groups[group_index].members:
            if recipient_id not in self.peer_map:
                self.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
                return

        if self.groups[group_index].owner_id not in self.peer_map:
            self.lsnp_logger.error(f"[ERROR] Unknown peer: {self.groups[group_index].owner_id}")
            return
            
        message_id = str(uuid.uuid4())
        token = generate_token(self.full_user_id, "group")

        msg = make_group_message(
            from_user_id = self.full_user_id,
            group_id = self.groups[group_index].group_id,
            content = content,
            message_id = message_id,
            token = token
        )

        ack_event = threading.Event()
        self.ack_events[message_id] = ack_event

        for member in self.groups[group_index].members:
            peer = self.peer_map[member]
            try:
                for attempt in range(RETRY_COUNT):
                    self.socket.sendto(msg.encode(), (peer.ip, peer.port))
                    if self.verbose:
                        self.lsnp_logger.info(f"[GROUP MESSAGE SEND] Attempt {attempt + 1} to \"{self.groups[group_index].group_name}\" for {member} at {peer.ip}")
                    
                    if ack_event.wait(RETRY_INTERVAL):
                        self.lsnp_logger.info(f"[GROUP MESSAGE SENT] to \"{self.groups[group_index].group_name}\" for {member} at {peer.ip}")
                        break
                    
                    if self.verbose:
                        self.lsnp_logger.info(f"[RETRY] {attempt + 1} to \"{self.groups[group_index].group_name}\" for {member} at {peer.ip}")
            except Exception as e:
                self.lsnp_logger.error(f"[FAILED] Group Message to \"{self.groups[group_index].group_name}\" for {member} at {peer.ip}")
                del self.ack_events[message_id] 

        peer = self.peer_map[self.groups[group_index].owner_id]
        try:
            for attempt in range(RETRY_COUNT):
                self.socket.sendto(msg.encode(), (peer.ip, peer.port))
                if self.verbose:
                    self.lsnp_logger.info(f"[GROUP MESSAGE SEND] Attempt {attempt + 1} to \"{self.groups[group_index].group_name}\" for {self.groups[group_index].owner_id} at {peer.ip}")
                
                if ack_event.wait(RETRY_INTERVAL):
                    self.lsnp_logger.info(f"[GROUP MESSAGE SENT] to \"{self.groups[group_index].group_name}\" for {self.groups[group_index].owner_id} at {peer.ip}")
                    break
                
                if self.verbose:
                    self.lsnp_logger.info(f"[RETRY] {attempt + 1} to \"{self.groups[group_index].group_name}\" for {self.groups[group_index].owner_id} at {peer.ip}")
        except Exception as e:
                self.lsnp_logger.error(f"[FAILED] Group Message to \"{self.groups[group_index].group_name}\" for {self.groups[group_index].owner_id} at {peer.ip}")
                del self.ack_events[message_id] 
        
        del self.ack_events[message_id]

    def show_inbox(self):
        if not self.inbox:
            self.lsnp_logger.info("No messages in inbox.")
            return
        
        self.lsnp_logger.info("Inbox:")
        for msg in self.inbox:
            self.lsnp_logger.info(msg)

    def show_ip_stats(self):
        """Show IP address statistics"""
        stats = self.ip_tracker.get_ip_stats()
        self.lsnp_logger.info("===| IP Address Statistics |===")
        self.lsnp_logger.info(f"Total known IPs: {stats['total_known_ips']}")
        self.lsnp_logger.info(f"Mapped to users: {stats['mapped_users']}")
        self.lsnp_logger.info(f"Total connection attempts: {stats['total_connection_attempts']}")
        self.lsnp_logger.info(f"Blocked IPs: {stats['blocked_ips']}")
        
        if not stats['top_active_ips']:
            return
 
        self.lsnp_logger.info("Most active IPs:")
        for ip, count in stats['top_active_ips']:
            user = self.ip_tracker.ip_to_user.get(ip, "Unknown")
            self.lsnp_logger.info(f"  {ip} ({user}): {count} connections")
        
    def follow(self, user_id: str):
        # Resolve user_id to full_user_id if needed
        if "@" not in user_id:
            full_user_id = None
            for id in self.peer_map:
                if id.startswith(f"{user_id}@"):
                    full_user_id = id
                    break
            if not full_user_id:
                self.lsnp_logger.error(f"[ERROR] Unknown peer: {user_id}")
                return
            user_id = full_user_id

        if user_id not in self.peer_map:
            self.lsnp_logger.error(f"[ERROR] Unknown peer: {user_id}")
            return
        elif user_id == self.full_user_id:
            self.lsnp_logger.warning(f"[FOLLOW] Cannot follow yourself: {user_id}")
            return
        elif user_id in self.following:
            self.lsnp_logger.warning(f"[FOLLOW] Already following {user_id}")
            return

        # ✅ Add to following (not followers)
        self.following.add(user_id)
        self.lsnp_logger.info(f"[FOLLOW] Now following {user_id}")

        peer = self.peer_map[user_id]
        message_id = str(uuid.uuid4())[:8]
        token = generate_token(self.full_user_id, "follow")

        msg = make_follow_message(
            from_id=self.full_user_id,
            to_id=user_id,
            message_id=message_id,
            token=token
        )

        # Inline ACK logic
        ack_event = threading.Event()
        self.ack_events[message_id] = ack_event

        for attempt in range(RETRY_COUNT):
            self.socket.sendto(msg.encode(), (peer.ip, peer.port))
            if self.verbose:
                self.lsnp_logger.info(f"[FOLLOW SEND] Attempt {attempt + 1} to {peer.display_name} at {peer.ip}")

            if ack_event.wait(RETRY_INTERVAL):
                self.lsnp_logger.info(f"[FOLLOW SENT] to {peer.display_name} at {peer.ip}")
                del self.ack_events[message_id]
                self.following.add(user_id)
                return

            if self.verbose:
                self.lsnp_logger.info(f"[FOLLOW RETRY] {attempt + 1} for {peer.display_name} at {peer.ip}")

        self.lsnp_logger.error(f"[FOLLOW FAILED] Could not send to {peer.display_name} at {peer.ip}")
        del self.ack_events[message_id]

    def unfollow(self, user_id: str):
      if "@" not in user_id:
          full_user_id = None
          for id in self.peer_map:
              if id.startswith(f"{user_id}@"):
                  full_user_id = id
                  break
          if not full_user_id:
              self.lsnp_logger.error(f"[ERROR] Unknown peer: {user_id}")
              return
          user_id = full_user_id

      if user_id not in self.peer_map:
          self.lsnp_logger.error(f"[ERROR] Unknown peer: {user_id}")
          return
      elif user_id == self.full_user_id:
          self.lsnp_logger.warning(f"[UNFOLLOW] Cannot unfollow yourself: {user_id}")
          return
      elif user_id not in self.following:
          self.lsnp_logger.warning(f"[UNFOLLOW] Not following {user_id}")
          return

      self.lsnp_logger.info(f"[UNFOLLOW] Now unfollowing {user_id}")
      self.following.remove(user_id)

      peer = self.peer_map[user_id]
      message_id = str(uuid.uuid4())[:8]
      token = generate_token(self.full_user_id, "unfollow")

      msg = make_unfollow_message(
          from_id=self.full_user_id,
          to_id=user_id,
          message_id=message_id,
          token=token
      )

      # Inline ACK logic
      ack_event = threading.Event()
      self.ack_events[message_id] = ack_event

      for attempt in range(RETRY_COUNT):
          self.socket.sendto(msg.encode(), (peer.ip, peer.port))
          if self.verbose:
              self.lsnp_logger.info(f"[UNFOLLOW SEND] Attempt {attempt + 1} to {peer.display_name} at {peer.ip}")

          if ack_event.wait(RETRY_INTERVAL):
              self.lsnp_logger.info(f"[UNFOLLOW SENT] to {peer.display_name} at {peer.ip}")
              del self.ack_events[message_id]
              self.following.remove(user_id)
              return

          if self.verbose:
              self.lsnp_logger.info(f"[UNFOLLOW RETRY] {attempt + 1} for {peer.display_name} at {peer.ip}")

      self.lsnp_logger.error(f"[UNFOLLOW FAILED] Could not send to {peer.display_name} at {peer.ip}")
      del self.ack_events[message_id]


    def broadcast_profile(self):
      # Build the PROFILE message
      msg = make_profile_message(self.display_name, self.full_user_id, self.avatar_path)
    
      preview = None
      if self.avatar_path and os.path.isfile(self.avatar_path):
        try:
          with open(self.avatar_path, "rb") as img_file:
              avatar_base64 = base64.b64encode(img_file.read()).decode('utf-8')
          preview = avatar_base64[:20] + "..." if len(avatar_base64) > 20 else avatar_base64
        except Exception as e:
              self.lsnp_logger.error(f"[DEBUG] Failed to generate avatar preview: {e}")
              

        # Log the message but without showing full AVATAR_DATA
      safe_log_msg = msg
      if "AVATAR_DATA" in safe_log_msg:
          # Replace the full avatar data with a placeholder in the log
          safe_log_msg = safe_log_msg.replace(
              msg.split("AVATAR_DATA: ")[1].split("\n", 1)[0],
              preview if preview else "[hidden]"
          )

      # self.lsnp_logger.info(f"[DEBUG] PROFILE message to send:\n{safe_log_msg}")
          
      # Broadcast to the subnet
      broadcast_addr = self.ip.rsplit('.', 1)[0] + '.255'

      try:
          self.socket.sendto(msg.encode(), (broadcast_addr, self.port))
          self.lsnp_logger.info(f"[PROFILE BROADCAST] Sent to {broadcast_addr}:{self.port}")
      except Exception as e:
          self.lsnp_logger.error(f"[BROADCAST FAILED] {e}")

      if self.verbose:
          self.lsnp_logger.info("[BROADCAST] Profile message sent.")

    def send_post(self, content: str):
      
      if self.verbose:
        self.lsnp_logger.info(f"[POST] Sending post to {len(self.followers)} followers")
        
      if not self.followers:
          self.lsnp_logger.warning("[POST] No followers to send the post to.")
          return

      message_map = {}  # Map follower_id → message_id
      ack_events = {}   # Map message_id → Event

      # 1. Send to all followers first
      
      for follower_id in self.followers:
          if self.verbose:
              self.lsnp_logger.info(f"[POST] Sending post to {follower_id}")
          if follower_id == self.full_user_id:
              if self.verbose:
                  self.lsnp_logger.info("[POST] Skipping self")
              continue
          if follower_id not in self.peer_map:
              self.lsnp_logger.warning(f"[POST] Skipped unknown follower: {follower_id}")
              continue

          peer = self.peer_map[follower_id]
          message_id = str(uuid.uuid4())
          token = generate_token(self.full_user_id, "post")
          expiry = int(token.split("|")[1])  # timestamp + ttl
          timestamp = expiry - state.ttl

          msg = make_post_message(
              from_id=self.full_user_id,
              content=content,
              ttl=state.ttl,
              message_id=message_id,
              token=token
          )
      
          # Create event for ACK
          ack_event = threading.Event()
          self.ack_events[message_id] = ack_event
          ack_events[message_id] = ack_event
          message_map[follower_id] = message_id

          # Initial send (Attempt 1)
          try:
              self.socket.sendto(msg.encode(), (peer.ip, peer.port))
              if self.verbose:
                  self.lsnp_logger.info(f"[POST SEND] Initial send to {peer.display_name} at {peer.ip}")
          except Exception as e:
              self.lsnp_logger.error(f"[POST ERROR] Failed to send to {peer.display_name}: {e}")

      # 2. Retry logic for all pending ACKs in batch
      for attempt in range(1, RETRY_COUNT):
          pending = [fid for fid, mid in message_map.items() if not ack_events[mid].is_set()]
          if not pending:
              break  # All ACKed, stop early

          if self.verbose:
              self.lsnp_logger.info(f"[POST RETRY] Attempt {attempt + 1} for {len(pending)} followers")
        
          time.sleep(RETRY_INTERVAL)

          # Resend to those who haven't ACKed
          for follower_id in pending:
              message_id = message_map[follower_id]
        
              if ack_events[message_id].is_set():
                continue  # Already ACKed, skip
            
              peer = self.peer_map[follower_id]
              msg = make_post_message(
                  from_id=self.full_user_id,
                  content=content,
                  ttl=state.ttl,
                  message_id=message_id,
                  token=generate_token(self.full_user_id, "post")  # regenerate token
              )

              try:
                  self.socket.sendto(msg.encode(), (peer.ip, peer.port))
                  if self.verbose:
                      self.lsnp_logger.info(f"[POST RETRY] Resent to {peer.display_name} at {peer.ip}")
              except Exception as e:
                  self.lsnp_logger.error(f"[POST ERROR] Retry failed for {peer.display_name}: {e}")

          # Wait before next retry
          time.sleep(RETRY_INTERVAL)

      # 3. Report final result
      sent_count = sum(1 for mid in message_map.values() if ack_events[mid].is_set())
      self.lsnp_logger.info(f"[POST COMPLETE] Sent to {sent_count}/{len(self.followers)} followers")

      # Cleanup ack_events
      for mid in message_map.values():
          if mid in self.ack_events:
              del self.ack_events[mid]

    def toggle_like(self, post_timestamp_id: str, owner_name: str):
      # Resolve short name to full_user_id using peer_map
      full_owner_id = None
      for peer in self.peer_map.values():
          if peer.display_name == owner_name or peer.user_id.startswith(f"{owner_name}@"):
              full_owner_id = peer.user_id
              break

      if not full_owner_id:
          self.lsnp_logger.error(f"[LIKE ERROR] Unknown post owner: {owner_name}")
          return

      peer = self.peer_map[full_owner_id]
      timestamp = str(int(time.time()))

      # Determine action (LIKE or UNLIKE)
      action = "UNLIKE" if post_timestamp_id in self.post_likes else "LIKE"
      token = generate_token(self.full_user_id, "like")

      # Build LIKE message
      msg = make_like_message(
          from_id=self.full_user_id,
          to_id=full_owner_id,
          post_timestamp_id=post_timestamp_id,
          action=action,
          timestamp=timestamp,
          token=token
      )

      # ACK handling
      ack_event = threading.Event()
      self.ack_events[timestamp] = ack_event

      for attempt in range(RETRY_COUNT):
          self.socket.sendto(msg.encode(), (peer.ip, peer.port))
          if self.verbose:
              self.lsnp_logger.info(f"[{action} SEND] Attempt {attempt + 1} to {peer.display_name} at {peer.ip}")

          if ack_event.wait(RETRY_INTERVAL):
              if action == "LIKE":
                  self.post_likes.add(post_timestamp_id)
                  self.lsnp_logger.info(f"[LIKE CONFIRMED] Post {post_timestamp_id} by {peer.display_name}")
              else:
                  self.post_likes.remove(post_timestamp_id)
                  self.lsnp_logger.info(f"[UNLIKE CONFIRMED] Post {post_timestamp_id} by {peer.display_name}")
              del self.ack_events[timestamp]
              return

          if self.verbose:
              self.lsnp_logger.info(f"[{action} RETRY] {attempt + 1} for {peer.display_name}")

      self.lsnp_logger.error(f"[{action} FAILED] Could not send {action} to {peer.display_name}")
      del self.ack_events[timestamp]

    def send_tictactoe_invite(self, recipient_id: str, symbol: str):
      symbol = symbol.upper()
      if symbol not in ("X", "O"):
          self.lsnp_logger.error("Symbol must be X or O.")
          return

      if "@" not in recipient_id:
          for uid in self.peer_map:
              if uid.startswith(f"{recipient_id}@"):
                  recipient_id = uid
                  break
      if recipient_id not in self.peer_map:
          self.lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
          return
      
      gameid = f"g{len(self.tictactoe_games) % 256}"
      message_id = str(uuid.uuid4())[:8]
      token = generate_token(self.full_user_id, "game")
      timestamp = int(time.time())

      self.tictactoe_games[gameid] = {
          "board": [" "] * 9,
          "my_symbol": symbol,
          "opponent": recipient_id,
          "turn": 0,
          "active": True
      }

      msg = make_tictaceto_invite_message(
          from_user_id=self.full_user_id,
          to_user_id=recipient_id,
          game_id=gameid,
          msg_id=message_id,
          symbol=symbol,
          timestamp=timestamp,
          token=token
      )

      peer = self.peer_map[recipient_id]
      self.socket.sendto(msg.encode(), (peer.ip, peer.port))
      self.lsnp_logger.info(f"Sent Tic Tac Toe invite to {recipient_id.split('@')[0]} as {symbol}")

  
    def send_tictactoe_move(self, gameid: str, position: int):
      game = self.tictactoe_games.get(gameid)
      if not game or not game.get("active"):
          self.lsnp_logger.error(f"No active game: {gameid}")
          return
      if position < 0 or position > 8 or game["board"][position] != " ":
          self.lsnp_logger.error("Invalid move")
          return

      game["board"][position] = game["my_symbol"]
      game["turn"] += 1

      winner, line = self.gamemanager._check_ttt_winner(game["board"])
      peer_id = game["opponent"]
      message_id = str(uuid.uuid4())[:8]
      token = generate_token(self.full_user_id, "game")

      move_msg = make_tictactoe_move_message(
            from_user_id=self.full_user_id,
            to_user_id=peer_id,
            gameid=gameid,
            message_id=message_id,
            position=position,
            symbol=game["my_symbol"],
            turn=game["turn"],
            token=token
      )
          


      peer = self.peer_map[peer_id]
      self.socket.sendto(move_msg.encode(), (peer.ip, peer.port))
      self.gamemanager._print_ttt_board(game["board"])

      if winner:
          self.send_tictactoe_result(gameid, winner, line)

    def send_tictactoe_result(self, gameid: str, winner, line):
      game = self.tictactoe_games.get(gameid)
      if not game:
          return
      peer_id = game["opponent"]
      result = "DRAW" if winner == "DRAW" else ("WIN" if winner == game["my_symbol"] else "LOSS")

      message_id = str(uuid.uuid4())[:8]
      timestamp = int(time.time())
      win_line_str = ",".join(map(str, line)) if line else ""

      msg = make_tictactoe_result_message(
          from_id=self.full_user_id,
          to_id=peer_id,
          gameid=gameid,
          result=result,
          symbol=game["my_symbol"],
          win_line_str=win_line_str,
          message_id=message_id,
          timestamp=timestamp,
          token=generate_token(self.full_user_id, "game")
      )
      
      
      peer = self.peer_map[peer_id]
      self.socket.sendto(msg.encode(), (peer.ip, peer.port))
      self.lsnp_logger.info(f"Game {gameid} ended: {result}")
      game["active"] = False

    def forfeit_tictactoe(self, gameid: str):
      self.send_tictactoe_result(gameid, "LOSS", None)


    def run(self):
      self.lsnp_logger.info(f"LSNP Peer started as {self.full_user_id}")
      self.lsnp_logger.info("Type 'help' for commands.")
      cmd = ""
      while True:
        try:
            cmd = self.lsnp_logger.input("", end="").strip()
            if cmd == "help":
              help_str = ("\nCommands:\n"
                "  peers                                        - List discovered peers\n"
                "  dms                                          - Show inbox\n"
                "  dm <user> <msg>                              - Send direct message\n"
                "  post <msg>                                   - Create a new post to followers\n"
                "  follow <user>                                - Follow a user\n"
                "  unfollow <user>                              - Unfollow a user\n"
                "  sendfile <user> <filepath> [description]                 - Send a file\n"
                "  acceptfile <fileid>                          - Accept a pending file offer\n"
                "  rejectfile <fileid>                          - Reject a pending file offer\n"
                "  pendingfiles                                 - List pending file offers\n"
                "  transfers                                    - List active file transfers\n"
                "  broadcast                                    - Send profile broadcast\n"
                "  ttl <seconds>                                - Set TTL for posts (default: 60)\n"
                "  tictactoe list                               - List active Tic Tac Toe games\n"
                "  tictactoe invite <user> <X|O>                - Invite to Tic Tac Toe game\n"
                "  tictactoe move <gameid> <position 0-8>       - Make a move in Tic Tac Toe\n"
                "  tictactoe forfeit <gameid>                   - Forfeit a Tic Tac Toe game\n"
                "  group list <name>                            - Show details of a group\n"
                "  group create <name> <users>                  - Creates a group with one or more users\n"
                "  group add <name> <user>                      - Adds a user to the group\n"
                "  group remove <name> <user>                   - Removes a user from the group\n"
                "  group message <name> <message>               - Sends a message to the group\n"
                "  Note: Group names and messages must be enclosed in quotation marks.\n"
                "  Note: Users must be separated by comma.\n"
                "  ping                                         - Send ping\n"
                "  verbose                                      - Toggle verbose mode\n"
                "  ipstats                                      - Show IP statistics\n"
                "  quit                                         - Exit")
              self.lsnp_logger.info(help_str)
            elif cmd == "peers":
              self.list_peers()
            elif cmd == "dms":
              self.show_inbox()
            elif cmd.startswith("dm "):
              parts = cmd.split(" ", 2)
              if len(parts) < 3:
                self.lsnp_logger.info("Usage: dm <user_id> <message>")
                continue
              _, recipient_id, message = parts
              self.send_dm(recipient_id, message)
            elif cmd.startswith("post "):
              parts = cmd.split(" ", 1)
              if len(parts) < 2:
                self.lsnp_logger.info("Usage: post <message>")
                continue
              _, message = parts
              self.send_post(message)
            elif cmd.startswith("like "):
              parts = cmd.split(" ")
              if len(parts) != 3:
                  self.lsnp_logger.info("Usage: like <post_timestamp_id> <owner_id>")
                  continue

              _, post_timestamp_id, owner_id = parts
              self.toggle_like(post_timestamp_id, owner_id)
            elif cmd.startswith("ttl "):
              parts = cmd.split(" ", 1)
              if len(parts) < 2 or not parts[1].isdigit():
                  self.lsnp_logger.info("Usage: ttl <seconds>")
                  continue
              state.ttl = int(parts[1])
              self.lsnp_logger.info(f"[TTL] TTL updated to {state.ttl} seconds")
            elif cmd.startswith("follow "):
              parts = cmd.split(" ", 2)
              if len(parts) < 2:
                self.lsnp_logger.info("Usage: follow <user_id>")
                continue
              _, user_id = parts
              self.follow(user_id)
            elif cmd.startswith("unfollow "):
              parts = cmd.split(" ", 2)
              if len(parts) < 2:
                self.lsnp_logger.info("Usage: unfollow <user_id>")
                continue
              _, user_id = parts
              self.unfollow(user_id)
            elif cmd.startswith("sendfile "):
                  parts = cmd.split(" ", 3)
                  if len(parts) < 3:
                      self.lsnp_logger.info("Usage: sendfile <user_id> <filepath> [description]")
                      continue
                  _, recipient_id, filepath = parts[:3]
                  description = parts[3] if len(parts) > 3 else ""
                  self.send_file(recipient_id, filepath, description)
            elif cmd.startswith("acceptfile "):
                parts = cmd.split(" ", 1)
                if len(parts) < 2:
                    self.lsnp_logger.info("Usage: acceptfile <fileid>")
                    continue
                _, file_id = parts
                self.accept_file(file_id)
            elif cmd.startswith("rejectfile "):
                parts = cmd.split(" ", 1)
                if len(parts) < 2:
                    self.lsnp_logger.info("Usage: rejectfile <fileid>")
                    continue
                _, file_id = parts
                self.reject_file(file_id)
            elif cmd == "pendingfiles":
                self.list_pending_files()
            elif cmd == "transfers":
                self.list_active_transfers()
            elif cmd == "broadcast":
                self.broadcast_profile()
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
                        self.lsnp_logger.info(group_help_str)
                        continue
                    parts = shlex.split(cmd)
                    group_index = -1
                    for index, group in enumerate(self.groups):
                        if group.group_name == parts[2]:
                            group_index = index
                            break
                    if group_index == -1 and parts[1] != "create":
                        self.lsnp_logger.info(f"No group exists.")
                        continue
                    if parts[1] == "lists":
                        for group in self.groups:
                            self.lsnp_logger.info(f"Group Name: {group.group_name}, Owner: {group.owner_id}, Members: {len(group.members)}")      
                    elif parts[1] == "list":
                        self.lsnp_logger.info(f"{group_index}")       
                        self.lsnp_logger.info(f"Group Name: {self.groups[group_index].group_name}")
                        self.lsnp_logger.info(f"Group Owner: {self.groups[group_index].owner_id}")
                        self.lsnp_logger.info(f"Group Members:")
                        for member in self.groups[group_index].members:
                            self.lsnp_logger.info(f"{member}")
                        continue
                    if len(parts) != 4:
                        self.lsnp_logger.info("Usage: group <cmd> <name> <args>")
                        continue
                    _, grp_cmd, grp_name, args = parts
                    if grp_cmd == "create":
                        self.group_create(grp_name, args)
                    elif grp_cmd == "add":
                        if self.groups[group_index].owner_id != self.full_user_id:
                            self.lsnp_logger.info("No permission to manage group.")
                        else:
                            self.group_add(group_index, args)
                    elif grp_cmd == "remove":
                        if self.groups[group_index].owner_id != self.full_user_id:
                            self.lsnp_logger.info("No permission to manage group.")
                        else:
                            self.group_remove(group_index, args)
                    elif grp_cmd == "message":
                        self.group_message(group_index, args)
                    else:
                        self.lsnp_logger.info("Usage: group <cmd> <args>")
                        continue
            elif cmd == "tictactoe":
                self.lsnp_logger.info("Usage: tictactoe invite <user> <X|O>, "
                                 "tictactoe move <gameid> <position 0-8>, "
                                 "tictactoe forfeit <gameid>")
            elif cmd == "tictactoe list":
                if not self.tictactoe_games:
                    self.lsnp_logger.info("No active Tic Tac Toe games.")
                else:
                    self.lsnp_logger.info("Active Tic Tac Toe games:")
                    for gameid, game in self.tictactoe_games.items():
                        self.lsnp_logger.info(f"- Game ID: {gameid}, Opponent: {game['opponent']}, "
                                         f"Symbol: {game['my_symbol']}, Turn: {game['turn']}")
            elif cmd.startswith("tictactoe invite "):
                parts = cmd.split(" ")
                if len(parts) != 4:
                    self.lsnp_logger.info("Usage: tictactoe invite <user> <X|O>")
                else:
                    _, _, user, symbol = parts
                    self.send_tictactoe_invite(user, symbol)
                
            elif cmd.startswith("tictactoe move "):
                parts = cmd.split(" ")
                if len(parts) != 4:
                    self.lsnp_logger.info("Usage: tictactoe move <gameid> <position 0-8>")
                else:
                    _, _, gameid, pos = parts
                    self.send_tictactoe_move(gameid, int(pos))

            elif cmd.startswith("tictactoe forfeit "):
                parts = cmd.split(" ")
                if len(parts) != 3:
                    self.lsnp_logger.info("Usage: tictactoe forfeit <gameid>")
                else:
                    _, _, gameid = parts
                    self.forfeit_tictactoe(gameid)
            elif cmd == "ping":
                self.send_ping()
            elif cmd == "verbose":
                self.verbose = not self.verbose
                self.lsnp_logger.info(f"Verbose mode {'on' if self.verbose else 'off'}")
            elif cmd == "ipstats":
                self.show_ip_stats()
            elif cmd == "quit":
                break 
            else:
              self.lsnp_logger.warning("Unknown command. Type 'help' for available commands.")
        except KeyboardInterrupt:
          break
        except Exception as e:
          self.lsnp_logger.error(f"Error: {e}")

      self.zeroconf.close()
      if cmd != "quit": print("") # For better looks

      stats = self.ip_tracker.get_ip_stats()
      self.lsnp_logger.info(f"Session totals - IPs: {stats['total_known_ips']}, "
                    f"Connections: {stats['total_connection_attempts']}")	
      self.lsnp_logger.critical("Peer terminated.")