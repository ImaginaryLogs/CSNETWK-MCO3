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

class LSNPController:
	def __init__(self, user_id: str, display_name: str, port: int = LSNP_PORT, verbose: bool = True):
		self.user_id = user_id
		self.display_name = display_name
		self.port = port
		self.verbose = verbose
		self.ip = self._get_own_ip()
		self.full_user_id = f"{self.user_id}@{self.ip}"
		self.peer_map: Dict[str, Peer] = {}
		self.inbox: List[str] = []
		self.ack_events: Dict[str, threading.Event] = {}

		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.socket.bind(("", self.port))

		self.zeroconf = Zeroconf()
		self._register_mdns()
		self._start_threads()

		self.ip_tracker = IPAddressTracker()

		if self.verbose:
			lsnp_logger.info(f"[INIT] Peer initialized: {self.full_user_id}")

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
		threading.Thread(target=self._periodic_profile_broadcast, daemon=True).start()
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
			ip = addr[0]
			port = addr[1]

			self.ip_tracker.log_new_ip(sender_ip, from_id, "profile_message")

			if from_id not in self.peer_map:
				peer = Peer(from_id, display_name, ip, port)
				self.peer_map[from_id] = peer
				
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

	def broadcast_profile(self):
		msg = make_profile_message(self.display_name, self.user_id, self.ip)
		broadcast_count = 0
	
		for peer in self.peer_map.values():
			try:
				self.socket.sendto(msg.encode(), (peer.ip, peer.port))
				broadcast_count += 1
				lsnp_logger.info(f"[BROADCAST] Sent to {peer.ip}:{peer.port}")
			except Exception as e:
				lsnp_logger.error("[BROADCAST] FAILED: To {peer.ip} - {e}")
				
		lsnp_logger.info(f"PROFILE BROADCAST: Sent to {broadcast_count} peers")
	
		if self.verbose:
			lsnp_logger_v.info("[BROADCAST] Profile message sent.")


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
		self.socket.sendto(msg.encode(), (broadcast_addr, self.port))
  
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
 
		lsnp_logger.info(f"Peer List: {self.peer_map} peers active.")
		lsnp_logger.info("Available peers:")
		for peer in self.peer_map.values():
			# Show both short and full format
			short_id = peer.user_id.split('@')[0]
			lsnp_logger.info(f"- {peer.display_name} ({short_id}) [{peer.user_id}] at {peer.ip}: {peer.port}")

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

	def run(self):
		lsnp_logger.info(f"LSNP Peer started as {self.full_user_id}")
		lsnp_logger.info("Type 'help' for commands.")
		cmd = ""
		while True:
			try:
				cmd = lsnp_logger.input("", end="").strip()
				if cmd == "help":
					help_str = "\nCommands:\n  peers           - List discovered peers\n  dms             - Show inbox\n  dm <user> <msg> - Send direct message\n  broadcast       - Send profile broadcast\n  ping            - Send ping\n  verbose         - Toggle verbose mode\n  quit            - Exit"
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
				elif cmd == "broadcast":
					self.broadcast_profile()
				elif cmd == "ping":
					self.send_ping()
				elif cmd == "verbose":
					self.verbose = not self.verbose
					lsnp_logger.info(f"Verbose mode {'on' if self.verbose else 'off'}")
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

