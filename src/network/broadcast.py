import time
from src.protocol.types.messages.message_formats import make_ping_message, make_profile_message
from src.manager.lsnp_controller import LSNPController, LSNP_BROADCAST_PERIOD_SECONDS

class BroadcastModule:
  def __init__(self, controller: 'LSNPController'):
    self.controller = controller
  
  def send_ping(self):
    msg = make_ping_message(self.controller.full_user_id)
    # Broadcast ping
    broadcast_addr = self.controller.ip.rsplit('.', 1)[0] + '.255'
  
    try:
      self.controller.socket.sendto(msg.encode(), (broadcast_addr, self.controller.port))
      self.controller.lsnp_logger.info(f"PING BROADCAST: Sent to {broadcast_addr}:{self.controller.port}")    
      if self.controller.verbose:
        self.controller.lsnp_logger_v.info(f"[PING] Sent to {broadcast_addr}")
    except Exception as e:
      self.controller.lsnp_logger.error(f"PING BROADCAST FAILED: To {broadcast_addr} - {e}")
      
  def broadcast_profile(self):	
    msg = make_profile_message(self.controller.display_name, self.controller.user_id, self.controller.ip)
    broadcast_count = 0
  
    for peer in self.controller.peer_map.values():
      try:
        self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
        broadcast_count += 1
        self.controller.lsnp_logger.info(f"[BROADCAST] Sent to {peer.ip}:{peer.port}")
      except Exception as e:
        self.controller.lsnp_logger.error("[BROADCAST] FAILED: To {peer.ip} - {e}")
        
    self.controller.lsnp_logger.info(f"PROFILE BROADCAST: Sent to {broadcast_count} peers")
  
    if self.controller.verbose:
      self.controller.lsnp_logger_v.info("[BROADCAST] Profile message sent.")

  def _periodic_profile_broadcast(self):
    while True:
      time.sleep(LSNP_BROADCAST_PERIOD_SECONDS)  # 5 minutes
      if self.controller.peer_map:  # Only broadcast if we have peers
        if self.controller.verbose:
          self.controller.lsnp_logger_v.info("Periodic Broadcast - Starting scheduled profile broadcast.")
        self.broadcast_profile()