import argparse
from src.ui.logging import LogEntry, Logger, LoggerInstance, LogLevel
from src.network.peer_listener import *
from src.manager import *

logger = Logger()

STARTER_CODENAME='STARTER'

server_logger = logger.get_logger(f'[{STARTER_CODENAME}]')
verbose_logger = logger.get_logger(f'[{STARTER_CODENAME}] |:', False)

def main():
  server_logger.info("Hello World!")
  parser = argparse.ArgumentParser()
  parser.add_argument("user_id", help="Your username (without @ip)")
  parser.add_argument("-n", "--name", default="Anonymous", help="Display name")
  parser.add_argument("-p", "--port", type=int, default=LSNP_PORT, help="UDP port")
  parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose mode")
  args = parser.parse_args()
  server_logger.info("Starting LSNP Controller...")
  peer = LSNPController(args.user_id, args.name, args.port, args.verbose)
  peer.run()
  pass

if __name__ == "__main__":
  
  main()