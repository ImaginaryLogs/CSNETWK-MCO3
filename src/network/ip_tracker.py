
import socket
import threading
import time
import json
import uuid
from typing import Dict, List, Callable, Set
from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser, ServiceListener
from src.ui import *
from src.config import *
from src.protocol import *
from src.utils import *
from src.network import *

logger = Logger()

IP_LOGGER_CODE_NAME = 'IPTRAKR'

ip_logger = logger.get_logger(f'[cyan][{IP_LOGGER_CODE_NAME}][/]')

class IPAddressTracker:
  """
  Logs IP Information, the data flowing between them, and gives statistics about it.
  """
  def __init__(self) -> None:
    self.known_ips: Set[str] = set()
    self.ip_to_user: Dict[str, str] = {}
    self.connection_attempts: Dict[str, int] = {}
    self.blocked_ips: Set[str] = set()
    
  def log_new_ip(self, ip: str, user_id: str = '', context: str = "discovery") -> None:
    """Log when a new IP address is encountered"""
    if ip in self.known_ips:
      return
    
    self.known_ips.add(ip)
    if user_id:
        self.ip_to_user[ip] = user_id
        ip_logger.info(f"NEW IP: {ip} -> {user_id} (via {context})")
    else:
        ip_logger.info(f"NEW IP: {ip} (via {context})")
  
  def log_connection_attempt(self, ip: str, port: int, success: bool = True):
    """Log connection attempts from specific IPs"""
    
    self.connection_attempts[ip] = self.connection_attempts.get(ip, 0) + 1
    status = "SUCCESS" if success else "FAILED"
    ip_logger.info(f"CONN {status}: {ip}:{port} (attempt #{self.connection_attempts[ip]})")
    
    # Sussy Baka Activity
    if self.connection_attempts[ip] > 10 and not success:
      ip_logger.warning(f"SUSPICIOUS: {ip} has {self.connection_attempts[ip]} failed attempts")
      
  def log_message_flow(self, from_ip: str, to_ip: str, msg_type: str, size: int):
    """Log message traffic between IPs"""
    ip_logger.debug(f"MSG {msg_type}: {from_ip} -> {to_ip} ({size} bytes)")
        
  def get_ip_stats(self) -> Dict:
      """Get statistics about IP activity"""
      return {
          'total_known_ips': len(self.known_ips),
          'mapped_users': len(self.ip_to_user),
          'total_connection_attempts': sum(self.connection_attempts.values()),
          'blocked_ips': len(self.blocked_ips),
          'top_five_active_ips': sorted(
              self.connection_attempts.items(), 
              key=lambda x: x[1], 
              reverse=True
          )[:5]
      }
