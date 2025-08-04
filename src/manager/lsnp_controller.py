import socket
import threading
import time
import json
from typing import Dict, List, Callable, Tuple
from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser, ServiceListener
from src.ui import logging
from src.config import *
from src.protocol import Peer
from src.utils import *

LSNP_CODENAME =  'LSNPCON'
LSNP_PREFIX = None # f'[green][{LSNP_CODENAME}][/]'
LSNP_BROADCAST_PERIOD_SECONDS = 300

# Co
logger = logging.Logger()

class LSNPController:
	def __init__(self, user_id: str, display_name: str, port: int = LSNP_PORT, verbose: bool = True):
		self.user_id = user_id
		self.display_name = display_name
		self.verbose = verbose
		self.port = port
		
		
		self.peer_map: Dict[str, Peer] = {}
		self.inbox: List[str] = []
		self.following: set[str] = set()
		self.followers: set[str] = set()
		self.post_likes: set[str] = set()
		self.ack_events: Dict[str, threading.Event] = {}
  
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) # Enables broadcasting
		self.socket.bind(("", self.port))

		self.zeroconf = Zeroconf()

		from src.network import IPAddressTracker
		self.ip_tracker = IPAddressTracker()
		self.ip = self.ip_tracker.get_own_ip()
		self.full_user_id = f"{self.user_id}@{self.ip}"
  
		from src.network.network_manager import NetworkManager
		self.network_manager = NetworkManager(self)
  
		from src.protocol import MessageHandler
		self.message_handler = MessageHandler(self)
  
		from src.network import BroadcastModule
		self.broadcast_handler = BroadcastModule(self)
  
		from src.ui import CommandHandler
		self.command_handler = CommandHandler(self)
		logger_name =  f'[blue]{self.user_id}[/]' if LSNP_PREFIX is None else LSNP_PREFIX
		self.lsnp_logger = logger.get_logger(logger_name)
		self.lsnp_logger_v = logger.get_logger(f'{logger_name} |:')
  
		if self.verbose:
			self.lsnp_logger.info(f"[INIT] Peer initialized: {self.full_user_id}")

	def run(self):
		self.network_manager._register_mdns()
		self.network_manager._start_threads()
		self.command_handler.run()
  
   
	

