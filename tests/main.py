import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, "src")
sys.path.insert(0, src_path)

from protocol.protocol_parser import parse_lsnp_messages, format_lsnp_message
from manager.state import known_peers, posts, dms

def run_tests():
    verbose = True  # Set to False for cleaner output

    samples = [
        # PROFILE message
        """TYPE: PROFILE
USER_ID: alice@192.168.1.2
DISPLAY_NAME: Alice
STATUS: Ready
AVATAR_TYPE: image/png
AVATAR_ENCODING: base64
AVATAR_DATA: iVBORw0KGgoAAAANSUhEUgAAAAUA...
""",

        # POST message
        """TYPE: POST
USER_ID: alice@192.168.1.2
CONTENT: Hello from LSNP!
TTL: 3600
MESSAGE_ID: f83d2b1c
TOKEN: alice@192.168.1.2|1728941991|broadcast
""",

        # DM message
        """TYPE: DM
FROM: alice@192.168.1.2
TO: bob@192.168.1.3
CONTENT: Hi Bob!
TIMESTAMP: 1728938500
MESSAGE_ID: f83d2b1d
TOKEN: alice@192.168.1.2|1728942100|chat
"""
    ]

    print("=== LSNP PARSER TESTS ===\n")
    for i, raw in enumerate(samples, 1):
        print(f"\n--- Test #{i} ---")
        msg = parse_lsnp_messages(raw)
        formatted_msg = format_lsnp_message(msg)
        print(formatted_msg)
        
if __name__ == "__main__":
    run_tests()
