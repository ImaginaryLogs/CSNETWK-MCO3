
from typing import Dict, List, Callable, Tuple
from src.manager import LSNPController
from src.ui.logging import Logger

class CommandHandler:
  def __init__(self, controller: 'LSNPController'):
    from src.manager import LSNPController

    self.controller = controller
    pass

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
    inbox_str = []
    self.controller.lsnp_logger.info("Inbox:")
    for msg in self.controller.inbox:
      self.controller.lsnp_logger.info(msg)

  def show_ip_stats(self):
    """Show IP address statistics"""
    stats = self.controller.ip_tracker.get_ip_stats()
    show_str: List[str] = [
       "===| IP Address Statistics |===",
      f"Total known IPs: {stats['total_known_ips']}",
      f"Mapped to users: {stats['mapped_users']}",
      f"Total connection attempts: {stats['total_connection_attempts']}",
      f"Blocked IPs: {stats['blocked_ips']}"
    ]
    
    if not stats['top_active_ips']:
      self.controller.lsnp_logger.info('\n'.join(show_str))
      return
 
    show_str.append("Most active IPs:")
  
    for ip, count in stats['top_active_ips']:
        user = self.controller.ip_tracker.ip_to_user.get(ip, "Unknown")
        show_str.append(f"  {ip} ({user}): {count} connections")
    
    self.controller.lsnp_logger.info('\n'.join(show_str))

  def _change_verbose(self):
    self.controller.verbose = not self.controller.verbose
    self.controller.lsnp_logger.info(f"Verbose mode {'on' if self.controller.verbose else 'off'}")
 
  def show_help(self):
    help_str = [
      "Commands:",
      "  peers           - List discovered peers",
      "  dms             - Show inbox",
      "  dm <[green]user[/]> <[blue]msg[/]> - Send direct message",
      "  follow <[green]user[/]>   - Follow a user",
      "  unfollow <[green]user[/]> - Unfollow a user",
      "  broadcast       - Send profile broadcast"
      "  ping            - Send ping",
      "  verbose         - Toggle verbose mode",
      "  ipstats         - Show ip stats",
      "  show            - Show stacked messages",
      "  quit            - Exit"
     ]

    self.controller.lsnp_logger.info("\n".join(help_str))
  
  def show_messages(self):
    parent = self.controller.lsnp_logger._parent_logger
    
    if parent is not None:  
      parent.manual_flush_buffer();
  
  def run(self):
    self.controller.lsnp_logger.info(f"LSNP Peer started as {self.controller.full_user_id}\nType 'help' for commands.")
    cmd = ""
    while True:
      try:
        cmd = self.controller.lsnp_logger.input("", end="").strip()
        if cmd == "help": 								self.show_help()
        elif cmd == "peers":							self.list_peers()
        elif cmd == "dms": 								self.show_inbox()
        elif cmd.startswith("dm "):				self.controller.message_handler.send_dm_cmd(cmd)
        elif cmd.startswith("follow "): 	self.controller.message_handler.follow_cmd(cmd)
        elif cmd.startswith("unfollow "): self.controller.message_handler.unfollow_cmd(cmd)
        elif cmd.startswith("post "):			self.controller.message_handler.post_cmd(cmd)
        elif cmd == "broadcast": 					self.controller.broadcast_handler.broadcast_profile()
        elif cmd == "ping":								self.controller.broadcast_handler.send_ping()
        elif cmd == "verbose":						self._change_verbose()
        elif cmd == "ipstats": 						self.show_ip_stats()
        elif cmd == "show":               self.show_messages()
        elif cmd == "quit":								break
        else: self.controller.lsnp_logger.warning("Unknown command. Type 'help' for available commands.")
      except KeyboardInterrupt: 					break
      except Exception as e: 							self.controller.lsnp_logger.error(f"Error: {e}")

    self.controller.zeroconf.close()
    
    if cmd != "quit": print("") # For better looks
  
    stats = self.controller.ip_tracker.get_ip_stats()
    
    sessions = [f"Session totals - IPs: {stats['total_known_ips']}", f"Connections: {stats['total_connection_attempts']}"]
    
    self.controller.lsnp_logger.info("\n".join(sessions))	
    self.controller.lsnp_logger.critical("Peer terminated.")