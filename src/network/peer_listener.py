import socket
import threading
import time
import json
import uuid
from typing import Dict, List, Callable
from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser, ServiceListener
from src.ui import logging
from src.config import *
from src.protocol import *
from src.utils import *


class PeerListener(ServiceListener):
	def __init__(self, peer_map: Dict[str, Peer], on_discover: Callable[[Peer], None]):
		self.peer_map = peer_map
		self.on_discover = on_discover

	def remove_service(self, *args): 
		pass
	
	def update_service(self, *args): 
		pass

	def add_service(self, zeroconf: Zeroconf, type: str, name: str) -> None:
		info: ServiceInfo | None = zeroconf.get_service_info(type, name)
		
		if info is None: return
		
		user_id_raw = info.properties.get(b'user_id', b'')
		user_id = user_id_raw.decode() if user_id_raw is not None else ""
		
		display_name_raw = info.properties.get(b'display_name', b'')
		display_name = display_name_raw.decode() if display_name_raw is not None else ""
		
		ip = socket.inet_ntoa(info.addresses[0])
		port = info.port if info.port is not None else 0
		
		full_user_id = f"{user_id}@{ip}"
		
		if full_user_id in self.peer_map: return
		
		peer = Peer(full_user_id, display_name, ip, port)
		self.peer_map[full_user_id] = peer
		self.on_discover(peer)
