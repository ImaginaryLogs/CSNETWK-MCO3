import socket
import threading
import time
from typing import Tuple
from zeroconf import ServiceBrowser, Zeroconf
from .peer_listener import PeerListener
from src.manager.lsnp_controller import LSNPController
from src.utils import parse_kv_message
from src.ui.logging import Logger, LoggerInstance
from src.config import MDNS_SERVICE_TYPE, LSNP_BROADCAST_PERIOD_SECONDS, BUFFER_SIZE
import json
from src.protocol import Peer

class NetworkManager:
  def __init__(self, controller: "LSNPController", logger: "LoggerInstance"):
    self.controller = controller
    self.logger = logger

  def _on_peer_discovered(self, peer: Peer):
    self.controller.ip_tracker.log_new_ip(peer.ip, peer.user_id, "mdns_discovery")
    
    if self.controller.verbose:
        self.logger.info(f"[DISCOVERED] {peer.display_name} ({peer.user_id})")

  def _get_own_ip(self):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except:
        return "127.0.0.1"
    finally:
        s.close()

  def _start_threads(self):
    threading.Thread(target=self._listen, daemon=True).start()
    listener = PeerListener(self.controller.peer_map, self._on_peer_discovered)
    ServiceBrowser(self.controller.zeroconf, MDNS_SERVICE_TYPE, listener)
    if self.controller.verbose:
      self.logger.info("[mDNS] Discovery started")

  def _periodic_profile_broadcast(self):
      while True:
          time.sleep(LSNP_BROADCAST_PERIOD_SECONDS)  # 5 minutes
          if self.controller.peer_map:  # Only broadcast if we have peers
              if self.controller.verbose:
                  self.logger.info("Periodic Broadcast - Starting scheduled profile broadcast.")
              self.controller.command_manager.broadcast_profile()

  def _listen(self):
      while True:
          try:
              data: bytes
              addr: Tuple[str, int]
              data, addr = self.controller.socket.recvfrom(BUFFER_SIZE)
              sender_ip, sender_port = addr
  
              self.controller.ip_tracker.log_connection_attempt(sender_ip, sender_port, success=True)
              raw = data.decode()
              data_size = len(data)
              if self.controller.verbose:
                self.logger.info(f"[RECV] From {addr}: \n{raw[:100]}{'...' if len(raw) > 100 else ''}")
              
              # All messages should be in key-value format now
              if "TYPE: " in raw:
                  kv = parse_kv_message(raw)
                  self.controller.protocol_manager._handle_kv_message(kv, addr)
                  self.controller.ip_tracker.log_message_flow(sender_ip, self.controller.ip, kv.get("TYPE", "UNKNOWN"), data_size)
              else:
                  # Fallback for any legacy JSON messages
                  msg = json.loads(raw)
                  self.controller.protocol_manager._handle_json_message(msg, addr)
                  self.controller.ip_tracker.log_message_flow(sender_ip, self.controller.ip, msg.get("type", "JSON"), data_size)
          except Exception as e:
              if self.controller.verbose:
                  self.logger.info(f"[ERROR] Malformed message from {addr}: {e}")

  