import socket
import threading
import time
import json
import uuid
import base64
import os
import math
from typing import Dict, List, Callable, Tuple, Optional
from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser, ServiceListener
from src.ui import logging
from src.config import *
from src.protocol import *
from src.utils import *
from src.network import *

import src.manager.state as state

logger = logging.Logger()

LSNP_CODENAME = 'LSNPCON'
LSNP_PREFIX = f'[green][{LSNP_CODENAME}][/]'

lsnp_logger = logger.get_logger(LSNP_PREFIX)
lsnp_logger_v = logger.get_logger(f'{LSNP_PREFIX} |:')

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
        self.following = set()      # Who we are following
        self.post_likes = set()
        self.zeroconf = Zeroconf()
        self._register_mdns()
        self._start_threads()

        self.ip_tracker = IPAddressTracker()

        if self.verbose:
            lsnp_logger.info(f"[INIT] Peer initialized: {self.full_user_id}")


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
        lsnp_logger_v.info(f"[mDNS] Registered: {info.name}")

    def _start_threads(self):
      threading.Thread(target=self._listen, daemon=True).start()
      listener = PeerListener(self.peer_map, self._on_peer_discovered)
      ServiceBrowser(self.zeroconf, MDNS_SERVICE_TYPE, listener)
      if self.verbose:
        lsnp_logger_v.info("[mDNS] Discovery started")

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
                    lsnp_logger_v.info(f"[RECV] From {addr}: \n{raw[:100]}{'...' if len(raw) > 100 else ''}")
                
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
                    lsnp_logger_v.info(f"[ERROR] Malformed message from {addr}: {e}")

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
            lsnp_logger_v.info(f"[PROFILE] {display_name} ({from_id}) joined from {ip}")
        
        
            
        elif msg_type == "DM":
          from_id = kv.get("FROM", "")
          to_id = kv.get("TO", "")
          token = kv.get("TOKEN", "")

          # Verify this message is for us
          if to_id != self.full_user_id:
            if self.verbose:
              lsnp_logger_v.info(f"[DM IGNORED] Not for us: {to_id}")
              return
            
            if not validate_token(token, "chat"):
                if self.verbose:
                    lsnp_logger_v.info(f"[DM REJECTED] Invalid token from {from_id}")
                return
            
            content = kv.get("CONTENT", "")
            message_id = kv.get("MESSAGE_ID", "")
            timestamp = kv.get("TIMESTAMP", "")
            
            # Get display name for prettier output
            display_name = from_id.split('@')[0]  # Default to username part
            
            # Check if it's from ourselves
            if from_id == self.full_user_id:
                display_name = self.display_name
            else:
                # Look up in peer_map for other peers
                for peer in self.peer_map.values():
                    if peer.user_id == from_id:
                        display_name = peer.display_name
                        break
            
            lsnp_logger.info(f"{display_name}: {content}")
            self.inbox.append(f"[{timestamp}] {display_name}: {content}")
            self._send_ack(message_id, addr)
  
        elif msg_type == "FOLLOW":
            from_id = kv.get("FROM", "")
            to_id = kv.get("TO", "")
            display_name = from_id.split('@')[0]
            
            if to_id == self.full_user_id:
                    lsnp_logger.info(f"[NOTIFY] {display_name} is now following you.")
                    self.inbox.append(f"User {display_name} started following you.")

        elif msg_type == "UNFOLLOW":
                from_id = kv.get("USER_ID", "")
                display_name = kv.get("DISPLAY_NAME", "")
                lsnp_logger.info(f"[NOTIFY] {display_name} ({from_id}) has unfollowed you.")
                self.inbox.append(f"User {display_name} unfollowed you.")
        
        elif msg_type == "POST":
            from_id = kv.get("FROM", "")
            token = kv.get("TOKEN", "")
            if not validate_token(token, "post"):
                    lsnp_logger.warning(f"[POST REJECTED] Invalid token from {from_id}")
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
            lsnp_logger.info(f"[POST] {display_name}: {content}")
            self.inbox.append(f"[{timestamp}] {display_name} (POST): {content}")

        # File transfer message handlers
        elif msg_type == "FILE_OFFER":
            self._handle_file_offer(kv, addr)
            
        elif msg_type == "FILE_CHUNK":
            self._handle_file_chunk(kv, addr)
            
        elif msg_type == "FILE_RECEIVED":
            self._handle_file_received(kv, addr)

        elif msg_type == "ACK":
            message_id = kv.get("MESSAGE_ID", "")
            if message_id in self.ack_events:
                self.ack_events[message_id].set()
                if self.verbose:
                    lsnp_logger_v.info(f"[ACK] Received for message {message_id}")
        
        elif msg_type == "PING":
            user_id = kv.get("USER_ID", "")
            if self.verbose:
                lsnp_logger_v.info(f"[PING] From {user_id}")

        elif msg_type == "FILE_ACCEPT":
            from_id = kv.get("FROM", "")
            to_id = kv.get("TO", "")
            file_id = kv.get("FILEID", "")
            token = kv.get("TOKEN", "")
            
            if to_id != self.full_user_id:
                return
            
            if not validate_token(token, "file"):
                if self.verbose:
                    lsnp_logger_v.info(f"[FILE_ACCEPT REJECTED] Invalid token from {from_id}")
                return
            
            # Signal that file was accepted
            if file_id in self.file_response_events:
                self.file_responses[file_id] = "ACCEPTED"
                self.file_response_events[file_id].set()
                if self.verbose:
                    lsnp_logger_v.info(f"[FILE_ACCEPT] Received for {file_id}")

        elif msg_type == "FILE_REJECT":
            from_id = kv.get("FROM", "")
            to_id = kv.get("TO", "")
            file_id = kv.get("FILEID", "")
            token = kv.get("TOKEN", "")
            
            if to_id != self.full_user_id:
                return
            
            if not validate_token(token, "file"):
                if self.verbose:
                    lsnp_logger_v.info(f"[FILE_REJECT REJECTED] Invalid token from {from_id}")
                return
            
            # Signal that file was rejected
            if file_id in self.file_response_events:
                self.file_responses[file_id] = "REJECTED"
                self.file_response_events[file_id].set()
                if self.verbose:
                    lsnp_logger_v.info(f"[FILE_REJECT] Received for {file_id}")

    def _handle_file_offer(self, kv: dict, addr: Tuple[str, int]):
        from_id = kv.get("FROM", "")
        to_id = kv.get("TO", "")
        token = kv.get("TOKEN", "")
        
        # Verify this message is for us
        if to_id != self.full_user_id:
            if self.verbose:
                lsnp_logger_v.info(f"[FILE_OFFER IGNORED] Not for us: {to_id}")
            return
        
        if not validate_token(token, "file"):
            if self.verbose:
                lsnp_logger_v.info(f"[FILE_OFFER REJECTED] Invalid token from {from_id}")
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
        
        lsnp_logger.info(f"User {sender_name} is sending you a file do you accept?")
        if self.verbose:
            lsnp_logger_v.info(f"[FILE_OFFER] {filename} ({filesize} bytes) from {sender_name}")

    def _handle_file_chunk(self, kv: dict, addr: Tuple[str, int]):
        from_id = kv.get("FROM", "")
        to_id = kv.get("TO", "")
        token = kv.get("TOKEN", "")
        
        # Verify this message is for us
        if to_id != self.full_user_id:
            return
        
        if not validate_token(token, "file"):
            if self.verbose:
                lsnp_logger_v.info(f"[FILE_CHUNK REJECTED] Invalid token from {from_id}")
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
                lsnp_logger_v.info(f"[FILE_CHUNK IGNORED] No active transfer for {file_id}")
            return
        
        try:
            chunk_data = base64.b64decode(data_b64)
            success = transfer.add_chunk(chunk_index, chunk_data)
            
            if self.verbose:
                lsnp_logger_v.info(f"[FILE_CHUNK] {chunk_index+1}/{total_chunks} for {transfer.filename}")
            
            # Check if transfer is complete
            if transfer.completed:
                self._complete_file_transfer(transfer, addr)
                
        except Exception as e:
            if self.verbose:
                lsnp_logger_v.info(f"[FILE_CHUNK ERROR] Failed to process chunk: {e}")

    def _handle_file_received(self, kv: dict, addr: Tuple[str, int]):
        file_id = kv.get("FILEID", "")
        status = kv.get("STATUS", "")
        
        if self.verbose:
            lsnp_logger_v.info(f"[FILE_RECEIVED] {file_id} - {status}")

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
            
            lsnp_logger.info(f"File transfer of {transfer.filename} is complete")
            lsnp_logger.info(f"File saved to: {file_path}")
            
            # Send FILE_RECEIVED confirmation
            self._send_file_received(transfer.file_id, transfer.sender_id, "COMPLETE")
            
            # Clean up
            if transfer.file_id in self.active_transfers:
                del self.active_transfers[transfer.file_id]
                
        except Exception as e:
            lsnp_logger.error(f"[FILE_TRANSFER ERROR] Failed to complete transfer: {e}")

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
                lsnp_logger_v.info(f"[FILE_RECEIVED SENT] {file_id} - {status}")
        except Exception as e:
            if self.verbose:
                lsnp_logger_v.info(f"[FILE_RECEIVED ERROR] {e}")

    def _handle_json_message(self, msg: dict, addr):
        # Legacy handler for any remaining JSON messages
        msg_type = msg.get("type")
        sender_id = msg.get("user_id")

        if msg_type == "DM":
            token = msg.get("token", "")
            if not validate_token(token):
                lsnp_logger.warning(f"[DM REJECTED] Invalid token from {sender_id}")
                return
            content = msg.get("content")
            message_id = msg.get("message_id")
            timestamp = msg.get("timestamp")
            lsnp_logger_v.info(f"{sender_id}: {content}")
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
            lsnp_logger_v.info(f"[ACK SENT] For message {message_id} to {addr}")

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
            lsnp_logger_v.info(f"[DISCOVERED] {peer.display_name} ({peer.user_id})")

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
                lsnp_logger_v.info(f"[{response_type} SENT] {file_id}")
        except Exception as e:
            if self.verbose:
                lsnp_logger_v.info(f"[{response_type} ERROR] {e}")

    def accept_file(self, file_id: str):
        """Accept a pending file offer"""
        if file_id not in self.pending_offers:
            lsnp_logger.error(f"[ERROR] No pending file offer with ID: {file_id}")
            return
        
        transfer = self.pending_offers[file_id]
        transfer.accepted = True
        self.active_transfers[file_id] = transfer
        del self.pending_offers[file_id]
        
        # Send FILE_ACCEPT message to sender
        self._send_file_response(transfer.sender_id, file_id, "FILE_ACCEPT")
        
        lsnp_logger.info(f"[FILE ACCEPTED] {transfer.filename} from {transfer.sender_id.split('@')[0]}")

    def reject_file(self, file_id: str):
        """Reject a pending file offer"""
        if file_id not in self.pending_offers:
            lsnp_logger.error(f"[ERROR] No pending file offer with ID: {file_id}")
            return
        
        transfer = self.pending_offers[file_id]
        
        # Send FILE_REJECT message to sender
        self._send_file_response(transfer.sender_id, file_id, "FILE_REJECT")
        
        del self.pending_offers[file_id]
        
        lsnp_logger.info(f"[FILE REJECTED] {transfer.filename} from {transfer.sender_id.split('@')[0]}")

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
                lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
                return
            recipient_id = full_recipient_id

        if recipient_id not in self.peer_map:
            lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
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
                    lsnp_logger.error(f"[ERROR] File not found: {file_path}")
                    lsnp_logger.info(f"[HINT] Place files in: {os.path.join(self.project_root, 'files')}")
                    return

        if not os.path.exists(file_path):
            lsnp_logger.error(f"[ERROR] File not found: {file_path}")
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
            lsnp_logger.info(f"[FILE OFFER SENT] {filename} to {peer.display_name}")
            
            # Wait a bit for the recipient to accept (in a real implementation, 
            # you might want to wait for an acceptance message)
            if response_event.wait(timeout=60):  # 60 second timeout
                response = self.file_responses.get(file_id)
                
                if response == "ACCEPTED":
                    lsnp_logger.info(f"[FILE ACCEPTED] Sending {filename} to {peer.display_name}")
                    
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
                            lsnp_logger_v.info(f"[FILE CHUNK SENT] {chunk_index+1}/{total_chunks} to {peer.display_name}")
                        
                        time.sleep(0.1)  # Small delay between chunks
                    
                    lsnp_logger.info(f"[FILE TRANSFER COMPLETE] {filename} sent to {peer.display_name}")
                    
                elif response == "REJECTED":
                    lsnp_logger.info(f"[FILE REJECTED] {peer.display_name} rejected {filename}")
                else:
                    lsnp_logger.error(f"[FILE ERROR] Unknown response: {response}")
            else:
                lsnp_logger.error(f"[FILE TIMEOUT] No response from {peer.display_name} for {filename}")
            
            # Clean up
            if file_id in self.file_response_events:
                del self.file_response_events[file_id]
            if file_id in self.file_responses:
                del self.file_responses[file_id]
                
        except Exception as e:
            lsnp_logger.error(f"[FILE SEND ERROR] {e}")
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
            lsnp_logger.info("No pending file offers.")
            return
        
        lsnp_logger.info("Pending file offers:")
        for file_id, transfer in self.pending_offers.items():
            sender_name = transfer.sender_id.split('@')[0]
            lsnp_logger.info(f"- {transfer.filename} ({transfer.filesize} bytes) from {sender_name}")
            lsnp_logger.info(f"  File ID: {file_id}")
            if transfer.description:
                lsnp_logger.info(f"  Description: {transfer.description}")

    def list_active_transfers(self):
        """List active file transfers"""
        if not self.active_transfers:
            lsnp_logger.info("No active file transfers.")
            return
        
        lsnp_logger.info("Active file transfers:")
        for file_id, transfer in self.active_transfers.items():
            sender_name = transfer.sender_id.split('@')[0]
            progress = f"{transfer.received_chunks}/{transfer.total_chunks}"
            lsnp_logger.info(f"- {transfer.filename} from {sender_name}: {progress} chunks")

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
                lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
                return
            recipient_id = full_recipient_id

        if recipient_id not in self.peer_map:
            lsnp_logger.error(f"[ERROR] Unknown peer: {recipient_id}")
            return

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
                lsnp_logger_v.info(f"[DM SEND] Attempt {attempt + 1} to {recipient_id} at {peer.ip}")
            
            if ack_event.wait(RETRY_INTERVAL):
                lsnp_logger.info(f"[DM SENT] to {peer.display_name} at {peer.ip}")
                del self.ack_events[message_id]
                return
            
            if self.verbose:
                lsnp_logger_v.info(f"[RETRY] {attempt + 1} for {recipient_id} at {peer.ip}")

        lsnp_logger.error(f"[FAILED] DM to {peer.display_name} at {peer.ip}")
        del self.ack_events[message_id]
      

    def _periodic_profile_broadcast(self):
        while True:
            time.sleep(LSNP_BROADCAST_PERIOD_SECONDS)  # 5 minutes
            if self.peer_map:  # Only broadcast if we have peers
                if self.verbose:
                    lsnp_logger_v.info("Periodic Broadcast - Starting scheduled profile broadcast.")
                self.broadcast_profile()

    def send_ping(self):
        msg = make_ping_message(self.full_user_id)
        # Broadcast ping
        broadcast_addr = self.ip.rsplit('.', 1)[0] + '.255'
  
        try:
            self.socket.sendto(msg.encode(), (broadcast_addr, self.port))
            lsnp_logger.info(f"PING BROADCAST: Sent to {broadcast_addr}:{self.port}")    
            if self.verbose:
                lsnp_logger_v.info(f"[PING] Sent to {broadcast_addr}")
        except Exception as e:
            lsnp_logger.error(f"PING BROADCAST FAILED: To {broadcast_addr} - {e}")
   
    def list_peers(self):
        if not self.peer_map:
            lsnp_logger.info("No peers discovered yet.")
            return
 
        lsnp_logger.info(f"Peer List: {len(self.peer_map)} peers active.")
        lsnp_logger.info("Available peers:")
        for peer in self.peer_map.values():
            # Show both short and full format
            short_id = peer.user_id.split('@')[0]
            lsnp_logger.info(f"- {peer.display_name} ({short_id}) at {peer.ip}: {peer.port}")

    def show_inbox(self):
        if not self.inbox:
            lsnp_logger.info("No messages in inbox.")
            return
        
        lsnp_logger.info("Inbox:")
        for msg in self.inbox:
            lsnp_logger.info(msg)

    def show_ip_stats(self):
        """Show IP address statistics"""
        stats = self.ip_tracker.get_ip_stats()
        lsnp_logger.info("===| IP Address Statistics |===")
        lsnp_logger.info(f"Total known IPs: {stats['total_known_ips']}")
        lsnp_logger.info(f"Mapped to users: {stats['mapped_users']}")
        lsnp_logger.info(f"Total connection attempts: {stats['total_connection_attempts']}")
        lsnp_logger.info(f"Blocked IPs: {stats['blocked_ips']}")
        
        if not stats['top_active_ips']:
            return
 
        lsnp_logger.info("Most active IPs:")
        for ip, count in stats['top_active_ips']:
            user = self.ip_tracker.ip_to_user.get(ip, "Unknown")
            lsnp_logger.info(f"  {ip} ({user}): {count} connections")
        
    def follow(self, user_id: str):
        # Resolve user_id to full_user_id if needed
        if "@" not in user_id:
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
        elif user_id == self.full_user_id:
            lsnp_logger.warning(f"[FOLLOW] Cannot follow yourself: {user_id}")
            return
        elif user_id in self.following:
            lsnp_logger.warning(f"[FOLLOW] Already following {user_id}")
            return

        # ✅ Add to following (not followers)
        self.following.add(user_id)
        lsnp_logger.info(f"[FOLLOW] Now following {user_id}")

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
                lsnp_logger_v.info(f"[FOLLOW SEND] Attempt {attempt + 1} to {peer.display_name} at {peer.ip}")

            if ack_event.wait(RETRY_INTERVAL):
                lsnp_logger.info(f"[FOLLOW SENT] to {peer.display_name} at {peer.ip}")
                del self.ack_events[message_id]
                return

            if self.verbose:
                lsnp_logger_v.info(f"[FOLLOW RETRY] {attempt + 1} for {peer.display_name} at {peer.ip}")

        lsnp_logger.error(f"[FOLLOW FAILED] Could not send to {peer.display_name} at {peer.ip}")
        del self.ack_events[message_id]

    def unfollow(self, user_id: str):
      if "@" not in user_id:
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
      elif user_id == self.full_user_id:
          lsnp_logger.warning(f"[UNFOLLOW] Cannot unfollow yourself: {user_id}")
          return
      elif user_id not in self.following:
          lsnp_logger.warning(f"[UNFOLLOW] Not following {user_id}")
          return

      lsnp_logger.info(f"[UNFOLLOW] Now unfollowing {user_id}")
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
              lsnp_logger_v.info(f"[UNFOLLOW SEND] Attempt {attempt + 1} to {peer.display_name} at {peer.ip}")

          if ack_event.wait(RETRY_INTERVAL):
              lsnp_logger.info(f"[UNFOLLOW SENT] to {peer.display_name} at {peer.ip}")
              del self.ack_events[message_id]
              return

          if self.verbose:
              lsnp_logger_v.info(f"[UNFOLLOW RETRY] {attempt + 1} for {peer.display_name} at {peer.ip}")

      lsnp_logger.error(f"[UNFOLLOW FAILED] Could not send to {peer.display_name} at {peer.ip}")
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
              lsnp_logger.error(f"[DEBUG] Failed to generate avatar preview: {e}")
              

        # Log the message but without showing full AVATAR_DATA
      safe_log_msg = msg
      if "AVATAR_DATA" in safe_log_msg:
          # Replace the full avatar data with a placeholder in the log
          safe_log_msg = safe_log_msg.replace(
              msg.split("AVATAR_DATA: ")[1].split("\n", 1)[0],
              preview if preview else "[hidden]"
          )

      # lsnp_logger.info(f"[DEBUG] PROFILE message to send:\n{safe_log_msg}")
          
      # Broadcast to the subnet
      broadcast_addr = self.ip.rsplit('.', 1)[0] + '.255'

      try:
          self.socket.sendto(msg.encode(), (broadcast_addr, self.port))
          lsnp_logger.info(f"[PROFILE BROADCAST] Sent to {broadcast_addr}:{self.port}")
      except Exception as e:
          lsnp_logger.error(f"[BROADCAST FAILED] {e}")

      if self.verbose:
          lsnp_logger_v.info("[BROADCAST] Profile message sent.")

    def send_post(self, content: str):
      if not self.followers:
          lsnp_logger.warning("[POST] No followers to send the post to.")
          return

      message_map = {}  # Map follower_id → message_id
      ack_events = {}   # Map message_id → Event

      # 1. Send to all followers first
      for follower_id in self.followers:
          if follower_id == self.full_user_id:
              if self.verbose:
                  lsnp_logger_v.info("[POST] Skipping self")
              continue
          if follower_id not in self.peer_map:
              lsnp_logger.warning(f"[POST] Skipped unknown follower: {follower_id}")
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
                  lsnp_logger_v.info(f"[POST SEND] Initial send to {peer.display_name} at {peer.ip}")
          except Exception as e:
              lsnp_logger.error(f"[POST ERROR] Failed to send to {peer.display_name}: {e}")

      # 2. Retry logic for all pending ACKs in batch
      for attempt in range(1, RETRY_COUNT):
          pending = [fid for fid, mid in message_map.items() if not ack_events[mid].is_set()]
          if not pending:
              break  # All ACKed, stop early

          if self.verbose:
              lsnp_logger_v.info(f"[POST RETRY] Attempt {attempt + 1} for {len(pending)} followers")
        
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
                      lsnp_logger_v.info(f"[POST RETRY] Resent to {peer.display_name} at {peer.ip}")
              except Exception as e:
                  lsnp_logger.error(f"[POST ERROR] Retry failed for {peer.display_name}: {e}")

          # Wait before next retry
          time.sleep(RETRY_INTERVAL)

      # 3. Report final result
      sent_count = sum(1 for mid in message_map.values() if ack_events[mid].is_set())
      lsnp_logger.info(f"[POST COMPLETE] Sent to {sent_count}/{len(self.followers)} followers")

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
          lsnp_logger.error(f"[LIKE ERROR] Unknown post owner: {owner_name}")
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
              lsnp_logger_v.info(f"[{action} SEND] Attempt {attempt + 1} to {peer.display_name} at {peer.ip}")

          if ack_event.wait(RETRY_INTERVAL):
              if action == "LIKE":
                  self.post_likes.add(post_timestamp_id)
                  lsnp_logger.info(f"[LIKE CONFIRMED] Post {post_timestamp_id} by {peer.display_name}")
              else:
                  self.post_likes.remove(post_timestamp_id)
                  lsnp_logger.info(f"[UNLIKE CONFIRMED] Post {post_timestamp_id} by {peer.display_name}")
              del self.ack_events[timestamp]
              return

          if self.verbose:
              lsnp_logger_v.info(f"[{action} RETRY] {attempt + 1} for {peer.display_name}")

      lsnp_logger.error(f"[{action} FAILED] Could not send {action} to {peer.display_name}")
      del self.ack_events[timestamp]

    def run(self):
      lsnp_logger.info(f"LSNP Peer started as {self.full_user_id}")
      lsnp_logger.info("Type 'help' for commands.")
      cmd = ""
      while True:
        try:
            cmd = lsnp_logger.input("", end="").strip()
            if cmd == "help":
              help_str = ("\nCommands:\n"
                                  "  peers              - List discovered peers\n"
                                  "  dms                - Show inbox\n"
                                  "  dm <user> <msg>    - Send direct message\n"
                                  "  follow <user>      - Follow a user\n"
                                  "  unfollow <user>    - Unfollow a user\n"
                                  "  sendfile <user> <filepath> [description] - Send a file\n"
                                  "  acceptfile <fileid> - Accept a pending file offer\n"
                                  "  rejectfile <fileid> - Reject a pending file offer\n"
                                  "  pendingfiles       - List pending file offers\n"
                                  "  transfers          - List active file transfers\n"
                                  "  broadcast          - Send profile broadcast\n"
                                  "  ping               - Send ping\n"
                                  "  verbose            - Toggle verbose mode\n"
                                  "  ipstats            - Show IP statistics\n"
                                  "  quit               - Exit")
              lsnp_logger.info(help_str)
              lsnp_logger.info(help_str)
            elif cmd == "peers":
              self.list_peers()
            elif cmd == "dms":
              self.show_inbox()
            elif cmd.startswith("dm "):
              parts = cmd.split(" ", 2)
              if len(parts) < 3:
                lsnp_logger.info("Usage: dm <user_id> <message>")
                continue
              _, recipient_id, message = parts
              self.send_dm(recipient_id, message)
            elif cmd.startswith("post "):
              parts = cmd.split(" ", 1)
              if len(parts) < 2:
                lsnp_logger.info("Usage: post <message>")
                continue
              _, message = parts
              self.send_post(message)
            elif cmd.startswith("like "):
              parts = cmd.split(" ")
              if len(parts) != 3:
                  lsnp_logger.info("Usage: like <post_timestamp_id> <owner_id>")
                  continue

              _, post_timestamp_id, owner_id = parts
              self.toggle_like(post_timestamp_id, owner_id)
            elif cmd.startswith("ttl "):
              parts = cmd.split(" ", 1)
              if len(parts) < 2 or not parts[1].isdigit():
                  lsnp_logger.info("Usage: ttl <seconds>")
                  continue
              state.ttl = int(parts[1])
              lsnp_logger.info(f"[TTL] TTL updated to {state.ttl} seconds")
            elif cmd.startswith("follow "):
              parts = cmd.split(" ", 2)
              if len(parts) < 2:
                lsnp_logger.info("Usage: follow <user_id>")
                continue
              _, user_id = parts
              self.follow(user_id)
            elif cmd.startswith("unfollow "):
              parts = cmd.split(" ", 2)
              if len(parts) < 2:
                lsnp_logger.info("Usage: unfollow <user_id>")
                continue
              _, user_id = parts
              self.unfollow(user_id)
            elif cmd.startswith("sendfile "):
                  parts = cmd.split(" ", 3)
                  if len(parts) < 3:
                      lsnp_logger.info("Usage: sendfile <user_id> <filepath> [description]")
                      continue
                  _, recipient_id, filepath = parts[:3]
                  description = parts[3] if len(parts) > 3 else ""
                  self.send_file(recipient_id, filepath, description)
            elif cmd.startswith("acceptfile "):
                parts = cmd.split(" ", 1)
                if len(parts) < 2:
                    lsnp_logger.info("Usage: acceptfile <fileid>")
                    continue
                _, file_id = parts
                self.accept_file(file_id)
            elif cmd.startswith("rejectfile "):
                parts = cmd.split(" ", 1)
                if len(parts) < 2:
                    lsnp_logger.info("Usage: rejectfile <fileid>")
                    continue
                _, file_id = parts
                self.reject_file(file_id)
            elif cmd == "pendingfiles":
                self.list_pending_files()
            elif cmd == "transfers":
                self.list_active_transfers()
            elif cmd == "broadcast":
                self.broadcast_profile()
            elif cmd == "ping":
                self.send_ping()
            elif cmd == "verbose":
                self.verbose = not self.verbose
                lsnp_logger.info(f"Verbose mode {'on' if self.verbose else 'off'}")
            elif cmd == "ipstats":
                self.show_ip_stats()
            elif cmd == "quit":
                break 
            else:
              lsnp_logger.warning("Unknown command. Type 'help' for available commands.")
        except KeyboardInterrupt:
          break
        except Exception as e:
          lsnp_logger.error(f"Error: {e}")

      self.zeroconf.close()
      if cmd != "quit": print("") # For better looks

      stats = self.ip_tracker.get_ip_stats()
      lsnp_logger.info(f"Session totals - IPs: {stats['total_known_ips']}, "
                    f"Connections: {stats['total_connection_attempts']}")	
      lsnp_logger.critical("Peer terminated.")