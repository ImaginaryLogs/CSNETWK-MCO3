from src.protocol.protocol_parser import parse_lsnp_messages, format_lsnp_message
from src.manager.state import known_peers, posts, dms

def test_general():
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

    correct_output = [
        "TYPE: PROFILE\nUSER_ID: alice@192.168.1.2\nDISPLAY_NAME: Alice\nSTATUS: Ready\nAVATAR_TYPE: image/png\nAVATAR_ENCODING: base64\nAVATAR_DATA: iVBORw0KGgoAAAANSUhEUgAAAAUA...\n\n",
        "TYPE: POST\nUSER_ID: alice@192.168.1.2\nCONTENT: Hello from LSNP!\nTTL: 3600\nMESSAGE_ID: f83d2b1c\nTOKEN: alice@192.168.1.2|1728941991|broadcast\n\n",
        "TYPE: DM\nFROM: alice@192.168.1.2\nTO: bob@192.168.1.3\nCONTENT: Hi Bob!\nTIMESTAMP: 1728938500\nMESSAGE_ID: f83d2b1d\nTOKEN: alice@192.168.1.2|1728942100|chat\n\n"
    ]
    
    print("=== LSNP PARSER TESTS ===\n")
    
    for i, raw in enumerate(samples, 1):
        print(f"\n--- Test #{i} ---")
        msg = parse_lsnp_messages(raw, verbose)
        formatted_msg = format_lsnp_message(msg, verbose)
        assert formatted_msg == correct_output[i - 1]
        print(formatted_msg)
        
if __name__ == "__main__":
    test_general()
