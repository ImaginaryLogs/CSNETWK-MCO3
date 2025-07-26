import argparse
from src.ui.logging import LogEntry, Logger, LoggerInstance, LogLevel
from src.network.peer_listener import *
from src.manager import *

logger = Logger()

server_logger = logger.get_logger('[Server]')
verbose_logger = logger.get_logger('[Server] >>', False)

def main():
  server_logger.info("Hello World!")
  verbose_logger.info("The Message above me is printed with Logger.")
  parser = argparse.ArgumentParser()
  parser.add_argument("user_id", help="Your username (without @ip)")
  parser.add_argument("-n", "--name", default="Anonymous", help="Display name")
  parser.add_argument("-p", "--port", type=int, default=LSNP_PORT, help="UDP port")
  parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose mode")
  args = parser.parse_args()

  peer = LSNPController(args.user_id, args.name, args.port, args.verbose)
  peer.run()
  pass

if __name__ == "__main__":
  
  main()