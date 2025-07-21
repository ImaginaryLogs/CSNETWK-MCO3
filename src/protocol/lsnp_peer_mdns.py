import socket
import threading
import time
import json
import logging
from typing import Dict, List
from dataclasses import dataclass
from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser
import uuid

# Constants
LSNP_PORT = 50999
BUFFER_SIZE = 4096
MDNS_SERVICE_TYPE = "_lsnp._udp.local."
RETRY_COUNT = 3
RETRY_INTERVAL = 2.0  # seconds

@dataclass
class Peer:
    user_id: str
    display_name: str
    ip: str
    port: int

class PeerListener:
    def __init__(self, peer_map: Dict[str, Peer], on_discover):
        self.peer_map = peer_map
        self.on_discover = on_discover

    def remove_service(self, zeroconf, type, name):
        pass

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if info:
            props = info.properties
            user_id = props.get(b'user_id', b'').decode()
            display_name = props.get(b'display_name', b'').decode()
            ip = socket.inet_ntoa(info.addresses[0])
            port = info.port
            if user_id not in self.peer_map:
                peer = Peer(user_id=user_id, display_name=display_name, ip=ip, port=port)
                self.peer_map[user_id] = peer
                self.on_discover(peer)

    def update_service(self, zeroconf, type, name):
        pass

class LSNPPeer:
    def __init__(self, user_id: str, display_name: str, port: int = LSNP_PORT, verbose: bool = False):
        self.user_id = user_id
        self.display_name = display_name
        self.port = port
        self.verbose = verbose
        self.peer_map: Dict[str, Peer] = {}
        self.inbox: List[str] = []
        self.ack_events: Dict[str, threading.Event] = {}

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("", self.port))

        self.zeroconf = Zeroconf()
        self._register_mdns()
        self._start_listeners()

        if self.verbose:
            print(f"LSNP Peer initialized: {self.user_id}@{self._get_own_ip()} on port {self.port}")

    def _register_mdns(self):
        ip = self._get_own_ip()
        properties = {
            "user_id": self.user_id,
            "display_name": self.display_name,
        }
        info = ServiceInfo(
            MDNS_SERVICE_TYPE,
            f"{self.user_id}_at_{ip.replace('.', '_')}.{MDNS_SERVICE_TYPE}",
            addresses=[socket.inet_aton(ip)],
            port=self.port,
            properties=properties,
        )
        self.zeroconf.register_service(info)
        if self.verbose:
            print(f"[mDNS] Service registered: {info.name}")

    def _start_listeners(self):
        threading.Thread(target=self._listen, daemon=True).start()
        listener = PeerListener(self.peer_map, self._on_peer_discovered)
        self.browser = ServiceBrowser(self.zeroconf, MDNS_SERVICE_TYPE, listener)
        if self.verbose:
            print("[mDNS] Discovery started")

    def _get_own_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def _listen(self):
        while True:
            data, addr = self.socket.recvfrom(BUFFER_SIZE)
            try:
                msg = json.loads(data.decode())
                self._handle_message(msg, addr)
            except Exception as e:
                print(f"[ERROR] Failed to parse message from {addr}: {e}")

    def _handle_message(self, msg, addr):
        msg_type = msg.get("type")
        sender_id = msg.get("user_id")

        if msg_type == "DM":
            content = msg.get("content")
            message_id = msg.get("message_id")
            timestamp = msg.get("timestamp")
            print(f"{sender_id}: {content}")
            self._send_ack(sender_id, addr, message_id)
            self.inbox.append(f"[{timestamp}] {sender_id}: {content}")

        elif msg_type == "ACK":
            message_id = msg.get("message_id")
            if message_id in self.ack_events:
                self.ack_events[message_id].set()

    def _send_ack(self, sender_id, addr, message_id):
        ack = {
            "type": "ACK",
            "user_id": self.user_id,
            "message_id": message_id
        }
        self.socket.sendto(json.dumps(ack).encode(), addr)

    def _on_peer_discovered(self, peer: Peer):
        print(f"Added peer: {peer.user_id} ({peer.display_name}) at {peer.ip}:{peer.port}")
        print(f"[mDNS] Discovered peer: {peer.user_id}@{peer.ip}")

    def send_dm(self, recipient_id: str, content: str):
        if recipient_id not in self.peer_map:
            print(f"Unknown recipient: {recipient_id}")
            return

        peer = self.peer_map[recipient_id]
        message_id = str(uuid.uuid4())
        msg = {
            "type": "DM",
            "user_id": self.user_id,
            "content": content,
            "message_id": message_id,
            "timestamp": time.strftime("%H:%M:%S")
        }

        ack_event = threading.Event()
        self.ack_events[message_id] = ack_event

        for attempt in range(RETRY_COUNT):
            self.socket.sendto(json.dumps(msg).encode(), (peer.ip, peer.port))
            if self.verbose:
                print(f"[SEND] Attempt {attempt+1}: DM to {recipient_id}")
            if ack_event.wait(RETRY_INTERVAL):
                print(f"DM sent to {recipient_id}")
                del self.ack_events[message_id]
                return

        print(f"[ERROR] DM to {recipient_id} failed: No ACK received after {RETRY_COUNT} attempts")
        del self.ack_events[message_id]

    def list_peers(self):
        for peer in self.peer_map.values():
            print(f"- {peer.display_name} ({peer.user_id}@{peer.ip})")

    def show_inbox(self):
        print("Direct Messages:")
        for msg in self.inbox:
            print(msg)

    def run(self):
        print("LSNP Peer started. Type 'help' for commands.")
        while True:
            try:
                cmd = input("> ").strip()
                if cmd == "quit":
                    break
                elif cmd == "help":
                    print("Commands: peers, dms, dm <user_id> <msg>, verbose, quit")
                elif cmd == "peers":
                    self.list_peers()
                elif cmd == "dms":
                    self.show_inbox()
                elif cmd.startswith("dm "):
                    parts = cmd.split(" ", 2)
                    if len(parts) < 3:
                        print("Usage: dm <user_id> <msg>")
                        continue
                    _, recipient_id, msg = parts
                    self.send_dm(recipient_id, msg)
                elif cmd == "verbose":
                    self.verbose = not self.verbose
                    print(f"Verbose mode {'enabled' if self.verbose else 'disabled'}")
            except KeyboardInterrupt:
                break

        self.zeroconf.close()
        print("LSNP Peer stopped")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("user_id")
    parser.add_argument("-n", "--name", default="Anonymous")
    parser.add_argument("-p", "--port", type=int, default=LSNP_PORT)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    peer = LSNPPeer(args.user_id, args.name, args.port, args.verbose)
    peer.run()
