import json
from typing import Tuple
from src.protocol import Peer
from src.protocol.protocol_parser import parse_lsnp_messages, format_lsnp_message
from src.utils import validate_token, format_kv_message
from src.protocol.types.messages.message_formats import Group
from src.protocol.types.messages.peer_format import Peer
from src.manager.lsnp_controller import LSNPController
from src.ui.logging import LoggerInstance
from src.protocol.types.messages.message_formats import make_ack_message, make_profile_message, make_dm_message, make_ping_message, make_follow_message, make_post_message, make_like_message, make_group_remove_message, make_group_message, make_group_add_message

class ProtocolManager:
    def __init__(self, controller: "LSNPController", logger: "LoggerInstance"):
        self.controller = controller
        self.logger = logger

        
    def _failed_security_check(self, from_id: str, sender_ip: str) -> bool:
        if from_id and "@" in from_id:
            from_ip = from_id.split("@")[-1]
            if from_ip != sender_ip:
                self.controller.lsnp_logger.warning(f"[SECURITY] FROM field IP {from_ip} does not match sender IP {sender_ip}. Dropping message.")
                return True
            return False
        return True

    def _handle_kv_message(self, kv: dict, addr: Tuple[str, int]):
        msg_type = kv.get("TYPE")
        sender_ip, sender_port = addr

        if msg_type == "PROFILE":
            from_id = kv.get("USER_ID", "")
            display_name = kv.get("DISPLAY_NAME", "")
            avatar_data = kv.get("AVATAR_DATA")
            avatar_type = kv.get("AVATAR_TYPE")

            ip = addr[0]
            port = addr[1]

            self.controller.ip_tracker.log_new_ip(sender_ip, from_id, "profile_message")
            if from_id not in self.controller.peer_map:
                peer = Peer(from_id, display_name, ip, port)
                peer.avatar_data = avatar_data
                peer.avatar_type = avatar_type
                self.controller.peer_map[from_id] = peer
            else:
                # Update existing peer
                self.controller.peer_map[from_id].display_name = display_name
                self.controller.peer_map[from_id].avatar_data = avatar_data
                self.controller.peer_map[from_id].avatar_type = avatar_type

            if self.controller.verbose:
                self.controller.lsnp_logger.info(f"[PROFILE] {display_name} ({from_id}) joined from {ip}")
                
        elif msg_type == "DM":
            from_id = kv.get("FROM", "")
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            to_id = kv.get("TO", "")
            token = kv.get("TOKEN", "")

            # Verify this message is for us
            if self.controller.verbose:
                self.controller.lsnp_logger.info(f"[DM] Received from ${from_id} to ${to_id}")
            if to_id != self.controller.full_user_id:
                if self.controller.verbose:
                    self.controller.lsnp_logger.info(f"[DM IGNORED] Not for us: {to_id}")
                return
                
            if not validate_token(token, "chat"):
                if self.controller.verbose:
                    self.controller.lsnp_logger.info(f"[DM REJECTED] Invalid token from {from_id}")
                return
            content = kv.get("CONTENT", "")
            message_id = kv.get("MESSAGE_ID", "")
            timestamp = kv.get("TIMESTAMP", "")
            
            # Get display name for prettier output
            display_name = from_id.split('@')[0]  # Default to username part
            if self.controller.verbose:
                self.controller.lsnp_logger.info(f"{display_name}: {content}")
            # Check if it's from ourselves
            if from_id == self.controller.full_user_id:
                display_name = self.controller.display_name
            else:
                # Look up in peer_map for other peers
                for peer in self.controller.peer_map.values():
                    if peer.user_id == from_id:
                        display_name = peer.display_name
                        break
            
            self.controller.lsnp_logger.info(f"{display_name}: {content}")
            self.controller.inbox.append(f"[{timestamp}] {display_name}: {content}")
            self.controller.lsnp_logger.debug(f"Send Ack")
            self._send_ack(message_id, addr)
  
        elif msg_type == "FOLLOW":
            from_id = kv.get("FROM", "")
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            to_id = kv.get("TO", "")
            message_id = kv.get("MESSAGE_ID", "")
            display_name = from_id.split('@')[0]
            
            if to_id == self.controller.full_user_id:
                self.controller.lsnp_logger.info(f"[NOTIFY] {display_name} ({from_id}) is now following you.")
                self.controller.inbox.append(f"User {display_name} started following you.")
                self._send_ack(message_id, addr)
                self.controller.followers.append(from_id)

        elif msg_type == "UNFOLLOW":
            from_id = kv.get("FROM", "")
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            message_id = kv.get("MESSAGE_ID", "")
            display_name = from_id.split('@')[0]
            self.controller.lsnp_logger.info(f"[NOTIFY] {display_name} ({from_id}) has unfollowed you.")
            self.controller.inbox.append(f"User {display_name} unfollowed you.")
            self._send_ack(message_id, addr)
            self.controller.followers.remove(from_id)
        
        elif msg_type == "POST":
            from_id = kv.get("USER_ID", "")
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            token = kv.get("TOKEN", "")
            message_id = kv.get("MESSAGE_ID", "")
            if not validate_token(token, "post"):
                    self.controller.lsnp_logger.warning(f"[POST REJECTED] Invalid token from {from_id}")
                    return
            content = kv.get("CONTENT", "")
            timestamp = kv.get("TIMESTAMP", "")
            display_name = None
            for peer in self.controller.peer_map.values():
                    if peer.user_id == from_id:
                            display_name = peer.display_name
                            break
            if not display_name:
              display_name = from_id.split('@')[0]
            self.controller.lsnp_logger.info(f"[POST] {display_name}: {content}")
            self.controller.inbox.append(f"[{timestamp}] {display_name} (POST): {content}")
            self._send_ack(message_id, addr)

        # File transfer message handlers
        elif msg_type == "FILE_OFFER":
            from_id = kv.get("FROM", "")
            if self._failed_security_check(from_id, sender_ip):
                return
            
            self.controller.file_manager._handle_file_offer(kv, addr)
            
        elif msg_type == "FILE_CHUNK":
            from_id = kv.get("FROM", "")
            if self._failed_security_check(from_id, sender_ip):
                return
            
            self.controller.file_manager._handle_file_chunk(kv, addr)
            
        elif msg_type == "FILE_RECEIVED":
            from_id = kv.get("FROM", "")
            if self._failed_security_check(from_id, sender_ip):
                return
            
            self.controller.file_manager._handle_file_received(kv, addr)

        elif msg_type == "ACK":
            
            
            message_id = kv.get("MESSAGE_ID", "")
            if message_id in self.controller.ack_events:
                self.controller.ack_events[message_id].set()
                if self.controller.verbose:
                    self.controller.lsnp_logger.info(f"[ACK] Received for message {message_id}")
        
        elif msg_type == "PING":
            
            
            user_id = kv.get("USER_ID", "")
            if self.controller.verbose:
                self.controller.lsnp_logger.info(f"[PING] From {user_id}")

        elif msg_type == "FILE_ACCEPT":
            from_id = kv.get("FROM", "")
            if self._failed_security_check(from_id, sender_ip):
                return
            
            to_id = kv.get("TO", "")
            file_id = kv.get("FILEID", "")
            token = kv.get("TOKEN", "")
            
            if to_id != self.controller.full_user_id:
                return
            
            if not validate_token(token, "file"):
                del self.controller.pending_offers[file_id] 
                if self.controller.verbose:
                    self.controller.lsnp_logger.info(f"[FILE_ACCEPT REJECTED] Invalid token from {from_id}")
                
                return
            
            # Signal that file was accepted
            if file_id in self.controller.file_response_events:
                self.controller.file_responses[file_id] = "ACCEPTED"
                self.controller.file_response_events[file_id].set()
                if self.controller.verbose:
                    self.controller.lsnp_logger.info(f"[FILE_ACCEPT] Received for {file_id}")

        elif msg_type == "FILE_REJECT":
            from_id = kv.get("FROM", "")
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            to_id = kv.get("TO", "")
            file_id = kv.get("FILEID", "")
            token = kv.get("TOKEN", "")
            
            if to_id != self.controller.full_user_id:
                return
            
            if not validate_token(token, "file"):
                del self.controller.pending_offers[file_id] 
                if self.controller.verbose:
                    self.controller.lsnp_logger.info(f"[FILE_REJECT REJECTED] Invalid token from {from_id}")
                    
                return
            
            # Signal that file was rejected
            if file_id in self.controller.file_response_events:
                self.controller.file_responses[file_id] = "REJECTED"
                self.controller.file_response_events[file_id].set()
                if self.controller.verbose:
                    self.controller.lsnp_logger.info(f"[FILE_REJECT] Received for {file_id}")
        elif msg_type == "LIKE":
            from_id = kv.get("FROM", "");
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            to_id = kv.get("TO", "")
            post_timestamp = kv.get("POST_TIMESTAMP", "")
            action = kv.get("ACTION", "")
            timestamp = kv.get("TIMESTAMP", "")
            token = kv.get("TOKEN", "")
            
            
          
        elif msg_type == "TICTACTOE_INVITE":
            from_id = str(kv.get("FROM"))
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            gameid = str(kv.get("GAMEID"))
            symbol = str(kv.get("SYMBOL"))
            
            self.controller.lsnp_logger.info(f"{from_id.split('@')[0]} is inviting you to play tic-tac-toe.")
            
            self.controller.tictactoe_games[gameid] = {
                "board": [" "] * 9,
                "my_symbol": "O" if symbol == "X" else "X",
                "opponent": from_id,
                "turn": 0,
                "active": True
            }
            self.controller.gamemanager._print_ttt_board(self.controller.tictactoe_games[gameid]["board"])

        elif msg_type == "TICTACTOE_MOVE":
            from_id = str(kv.get("FROM"))
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            gameid = str(kv.get("GAMEID"))
            pos = int(str(kv.get("POSITION")))
            sym = kv.get("SYMBOL")
            game = self.controller.tictactoe_games.get(gameid)
            if game:
                game["board"][pos] = sym
                game["turn"] = int(str(kv.get("TURN")))
                self.controller.gamemanager._print_ttt_board(game["board"])
                winner, line = self.controller.gamemanager._check_ttt_winner(game["board"])
                if winner:
                    self.controller.gamemanager.send_tictactoe_result(gameid, winner, line)

        elif msg_type == "TICTACTOE_RESULT":
            from_id = str(kv.get("FROM"))
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            gameid = kv.get("GAMEID")
            result = kv.get("RESULT")
            line = kv.get("WINNING_LINE", "")
            self.controller.lsnp_logger.info(f"Game {gameid} result: {result}")
            self.controller.lsnp_logger.info(f"Winning line: {line}")
            self.controller.gamemanager._print_ttt_board(self.controller.tictactoe_games[gameid]["board"])
            
            self.controller.tictactoe_games[gameid]["active"] = False
            del self.controller.tictactoe_games[gameid]

        elif msg_type == "GROUP_CREATE":
            from_id: str = kv.get("FROM", "")
            
            from_id = str(kv.get("FROM"))
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            group_id: str = kv.get("GROUP_ID", "")
            group_name: str = kv.get("GROUP_NAME", "")
            members: str = kv.get("MEMBERS", "")
            token: str = kv.get("TOKEN", "")

            parts = members.split(",")

            if self.controller.full_user_id not in parts:
                return
            
            if not validate_token(token, "group"):
                if self.controller.verbose:
                    self.controller.lsnp_logger.info(f"[GROUP_CREATE REJECTED] Invalid token from {from_id}")
                return
            
            group = Group(group_id, group_name, from_id, parts)
            self.controller.groups.append(group)

            self.controller.lsnp_logger.info(f"[GROUP_CREATE] You've been added to \"{group_name}\"")
            if self.controller.verbose:
                self.controller.lsnp_logger.info(f"[GROUP_CREATE] Owner: {from_id}")
                self.controller.lsnp_logger.info(f"[GROUP_CREATE] Members: {members}")

        elif msg_type == "GROUP_ADD":
            from_id: str = kv.get("FROM", "")
            from_id = str(kv.get("FROM"))
            
            if self._failed_security_check(from_id, sender_ip):
                return
            group_id: str = kv.get("GROUP_ID", "")
            group_name: str = kv.get("GROUP_NAME", "")
            add: str = kv.get("ADD", "")
            members: str = kv.get("MEMBERS", "")
            token: str = kv.get("TOKEN", "")

            add_parts = add.split(",")
            member_parts = members.split(",")

            if self.controller.full_user_id not in member_parts:
                return
                            
            if not validate_token(token, "group"):
                if self.controller.verbose:
                    self.controller.lsnp_logger.info(f"[GROUP_ADD REJECTED] Invalid token from {from_id}")
                return

            if self.controller.full_user_id in add_parts:
                group = Group(group_id, group_name, from_id, member_parts)
                self.controller.groups.append(group)
                self.controller.lsnp_logger.info(f"[GROUP_ADD] You've been added to \"{group_name}\"")
            else:
                group_index = -1
                for index, group in enumerate(self.controller.groups):
                    if group.group_id == group_id:
                        group_index = index
                        break
                self.controller.groups[group_index].members = member_parts
                self.controller.lsnp_logger.info(f"[GROUP_ADD] The group \"{self.controller.groups[group_index].group_name}\" member list was updated.")
            if self.controller.verbose:
                self.controller.lsnp_logger.info(f"[GROUP_ADD] Owner: {from_id}")
                self.controller.lsnp_logger.info(f"[GROUP_ADD] Members: {members}")

        elif msg_type == "GROUP_REMOVE":
            from_id: str = kv.get("FROM", "")
            from_id = str(kv.get("FROM"))
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            group_id: str = kv.get("GROUP_ID", "")
            remove: str = kv.get("REMOVE", "")
            token: str = kv.get("TOKEN", "")

            remove_parts = remove.split(",")

            group_index = -1
            for index, group in enumerate(self.controller.groups):
                if group.group_id == group_id:
                    group_index = index
                    break

            if group_index == -1:
                return

            if self.controller.full_user_id not in self.controller.groups[group_index].members:
                return
            
            if not validate_token(token, "group"):
                if self.controller.verbose:
                    self.controller.lsnp_logger.info(f"[GROUP_REMOVE REJECTED] Invalid token from {from_id}")
                return
            
            if self.controller.full_user_id in remove_parts:
                self.controller.lsnp_logger.info(f"[GROUP_REMOVE] You've been removed from \"{self.controller.groups[group_index].group_name}\"")
                self.controller.groups.pop(group_index)
            else:
                for member in remove_parts:
                    self.controller.groups[group_index].members.remove(member)
                self.controller.lsnp_logger.info(f"[GROUP_REMOVE] The group \"{self.controller.groups[group_index].group_name}\" member list was updated.")
            
            if self.controller.verbose:
                members_str = ""
                for member in self.controller.groups[group_index].members:
                    members_str = members_str + ","
                members_str = members_str[:-1]
                self.controller.lsnp_logger.info(f"[GROUP_REMOVE] Owner: {from_id}")
                self.controller.lsnp_logger.info(f"[GROUP_REMOVE] Members: {members_str}")

        elif msg_type == "GROUP_MESSAGE":
            from_id = kv.get("FROM", "")
            
            from_id = str(kv.get("FROM"))
            
            if self._failed_security_check(from_id, sender_ip):
                return
            
            group_id: str = kv.get("GROUP_ID", "")
            content = kv.get("CONTENT", "")
            message_id = kv.get("MESSAGE_ID", "")
            token = kv.get("TOKEN", "")

            group_index = -1
            for index, group in enumerate(self.controller.groups):
                if group.group_id == group_id:
                    group_index = index
                    break
            
            if group_index == -1:
                return
            
            if not validate_token(token, "group"):
                if self.controller.verbose:
                    self.controller.lsnp_logger.info(f"[GROUP MESSAGE REJECTED] Invalid token from {from_id}")
                return
            
            self.controller.lsnp_logger.info(f"[\"{self.controller.groups[group_index].group_name}\"] {from_id}: {content}")
            self._send_ack(message_id, addr)
        elif msg_type == "REVOKE":
            token = kv.get("TOKEN", "")
            if token:
                self.controller.revoked_tokens.add(token)
                if self.controller.verbose:
                    self.controller.lsnp_logger.info(f"[REVOKE] Token revoked: {token}")     
    def _handle_json_message(self, msg: dict, addr):
        # Legacy handler for any remaining JSON messages
        msg_type = msg.get("type")
        sender_id = msg.get("user_id")

        if msg_type == "DM":
            token = msg.get("token", "")
            if not validate_token(token):
                self.controller.lsnp_logger.warning(f"[DM REJECTED] Invalid token from {sender_id}")
                return
            content = msg.get("content")
            message_id = msg.get("message_id")
            timestamp = msg.get("timestamp")
            self.controller.lsnp_logger.info(f"{sender_id}: {content}")
            self.controller.inbox.append(f"[{timestamp}] {sender_id}: {content}")
            self._send_ack_json(sender_id, addr, message_id)

        elif msg_type == "ACK":
            message_id = msg.get("message_id")
            if message_id in self.controller.ack_events:
                self.controller.ack_events[message_id].set()

    def _send_ack(self, message_id: str, addr):
        ack_msg = make_ack_message(message_id)
        self.controller.socket.sendto(ack_msg.encode(), addr)
        
        if self.controller.verbose:
            self.controller.lsnp_logger.info(f"[ACK SENT] For message {message_id} to {addr}")

    def _send_ack_json(self, sender_id, addr, message_id):
        # Legacy JSON ACK for compatibility
        ack = {
            "type": "ACK",
            "user_id": self.controller.user_id,
            "message_id": message_id
        }
        self.controller.socket.sendto(json.dumps(ack).encode(), addr)
