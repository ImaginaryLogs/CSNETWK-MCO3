from src.manager import LSNPController
from src.protocol.message_handler import Peer
from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser, ServiceListener
from src.config import *
from .peer_listener import PeerListener
import threading
from typing import Dict, List, Callable, Tuple
import socket
import json
from src.utils.parsers import parse_kv_message

class NetworkManager:
  def __init__(self, controller: 'LSNPController'):
    self.controller = controller
    pass
  
  def _on_peer_discovered(self, peer: Peer):
    self.controller.ip_tracker.log_new_ip(peer.ip, peer.user_id, "mdns_discovery")
  
    if self.controller.verbose: self.controller.lsnp_logger_v.info(f"[DISCOVERED] {peer.display_name} ({peer.user_id})")
 
  def _register_mdns(self):
    info = ServiceInfo(
      MDNS_SERVICE_TYPE,
      f"{self.controller.user_id}_at_{self.controller.ip.replace('.', '_')}.{MDNS_SERVICE_TYPE}",
      addresses=[socket.inet_aton(self.controller.ip)],
      port=self.controller.port,
      properties={
        "user_id": self.controller.user_id,
        "display_name": self.controller.display_name
      }
    )
    self.controller.zeroconf.register_service(info)
  
    if self.controller.verbose: self.controller.lsnp_logger_v.info(f"[mDNS] Registered: {info.name}")

  def _start_threads(self):
    listener = PeerListener(self.controller.peer_map, self._on_peer_discovered)
    ServiceBrowser(self.controller.zeroconf, MDNS_SERVICE_TYPE, listener)
    
    threading.Thread(target=self._listen, daemon=True).start()
    
    threading.Thread(target=self.controller.broadcast_handler._periodic_profile_broadcast, daemon=True).start()
  
    if self.controller.verbose: self.controller.lsnp_logger_v.info("[mDNS] Multicast Domain Name System started.")

  

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

        if self.controller.verbose: self.controller.lsnp_logger_v.info(f"[RECV] From {addr}: \n{raw[:100]}{'...' if len(raw) > 100 else ''}")
        
        # All messages should be in key-value format now
        if "TYPE: " in raw:
          kv = parse_kv_message(raw)
          self.controller.message_handler._handle_kv_message(kv, addr)
          self.controller.ip_tracker.log_message_flow(sender_ip, self.controller.ip, kv.get("TYPE", "UNKNOWN"), data_size)
     
        else:
          # Fallback for any legacy JSON messages
          msg = json.loads(raw)
          self.controller.message_handler._handle_json_message(msg, addr)
          self.controller.ip_tracker.log_message_flow(sender_ip, self.controller.ip, msg.get("type", "JSON"), data_size)
     
      except Exception as e:
        if self.controller.verbose:
          self.controller.lsnp_logger_v.info(f"[ERROR] Malformed message from {addr}: {e}")