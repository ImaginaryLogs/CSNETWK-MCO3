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

import src.manager.state as state

logger = logging.Logger()

LSNP_CODENAME = 'LSNPCON'
LSNP_PREFIX = f'[green][{LSNP_CODENAME}][/]'


class LSNPController:
    def __init__(self, user_id: str, display_name: str, port: int = LSNP_PORT, verbose: bool = True, avatar_path: str|None=""):
      self.user_id = user_id
      self.display_name = display_name
      self.port = port
      self.avatar_path = avatar_path
      self.verbose = verbose
      
      
      self.peer_map: Dict[str, Peer] = {}
      self.inbox: List[str] = []
      
      self.groups: List[Group] = []
      self.followers: List[str] = []
      self.ack_events: Dict[str, threading.Event] = {}
      
      
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
      
      self.tictactoe_games = {}  
      self.lsnp_logger = logger.get_logger(user_id)
      self.ip_tracker = IPAddressTracker()
      
      from src.protocol.protocol_manager import ProtocolManager
      self.protocol_manager = ProtocolManager(self, self.lsnp_logger)
      
      from src.manager.peer_manager import PeerManager
      self.peer_manager = PeerManager(self, self.lsnp_logger)
      
      from src.network.network_manager import NetworkManager
      self.network_manager = NetworkManager(self, self.lsnp_logger) 
      self.ip = self.network_manager._get_own_ip()
      self.peer_manager._register_mdns()
      self.network_manager._start_threads()
      self.full_user_id = f"{self.user_id}@{self.ip}"
      from src.manager.file_manager import FileManager
      self.file_manager = FileManager(self, self.lsnp_logger)
      self.project_root = self.file_manager._get_project_root()
      
      from src.manager.group_manager import GroupManager
      self.group_manager = GroupManager(self, self.lsnp_logger)
      
      from src.game.tictactoe import GameManager
      self.gamemanager = GameManager(self, self.lsnp_logger)
      
      from src.manager import CommandManager
      self.command_manager = CommandManager(self, self.lsnp_logger)
    
      
      self.revoked_tokens = set()
      
      if self.verbose:
          self.lsnp_logger.info(f"[INIT] Peer initialized: {self.full_user_id}")
    
    def run(self):
        self.command_manager.run()

