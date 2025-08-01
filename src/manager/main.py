import argparse
import os
from src.ui.logging import LogEntry, Logger, LoggerInstance, LogLevel
from src.network.peer_listener import *
from src.manager import *

logger = Logger()

STARTER_CODENAME='STARTER'

server_logger = logger.get_logger(f'[{STARTER_CODENAME}]')
verbose_logger = logger.get_logger(f'[{STARTER_CODENAME}] |:', False)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # -> src/manager
DEFAULT_IMAGE_DIR = os.path.join(CURRENT_DIR, "..", "utils", "images")

def main():
  server_logger.info("Hello World!")
  parser = argparse.ArgumentParser()
  parser.add_argument("user_id", help="Your username (without @ip)")
  parser.add_argument("-n", "--name", default="Anonymous", help="Display name")
  parser.add_argument("-p", "--port", type=int, default=LSNP_PORT, help="UDP port")
  parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose mode")
  parser.add_argument("--avatar", help="Path to your profile picture")
  args = parser.parse_args()
  avatar_path = None
  if args.avatar:
    # If user gave just a filename, join it with default directory
    if not os.path.isabs(args.avatar) and not os.path.dirname(args.avatar):
        avatar_path = os.path.join(DEFAULT_IMAGE_DIR, args.avatar)
    else:
        avatar_path = args.avatar

    # Validate if the file exists
    if not os.path.isfile(avatar_path):
        server_logger.error(f"Avatar file not found: {avatar_path}")
        return
  else:
    avatar_path = None  
  server_logger.info("Starting LSNP Controller...")
  peer = LSNPController(args.user_id, args.name, args.port, args.verbose, avatar_path=avatar_path)
  peer.run()
  pass

if __name__ == "__main__":
  
  main()