import socket
from zeroconf import ServiceInfo, Zeroconf
from .lsnp_controller import LSNPController
from src.ui.logging import LoggerInstance
from src.config import MDNS_SERVICE_TYPE

class PeerManager():
  def __init__(self, controller: "LSNPController", logger: "LoggerInstance"):
      self.controller = controller
      self.logger = logger

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
    if self.controller.verbose:
      self.logger.info(f"[mDNS] Registered: {info.name}")
