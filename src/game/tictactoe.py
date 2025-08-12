from src.ui.logging import LoggerInstance
from src.manager.lsnp_controller import LSNPController
import time
import uuid
from src.utils.tokens import generate_token
from src.protocol.types.messages.message_formats import (
    make_tictactoe_result_message,
    make_tictaceto_invite_message,
    make_tictactoe_move_message
)
class GameManager:
  def __init__(self, controller: "LSNPController", logger: "LoggerInstance"):
      self.logger = logger
      self.controller = controller
      
  def _print_ttt_board(self, board):
    self.logger.info("\n")
    for i in range(0, 9, 3):
      self.logger.info(f" {board[i]} | {board[i+1]} | {board[i+2]} ")
      if i < 6:
        self.logger.info("---+---+---")
    self.logger.info("\n")

  def _check_ttt_winner(self, board):
      wins = [
          (0,1,2), (3,4,5), (6,7,8),  # rows
          (0,3,6), (1,4,7), (2,5,8),  # cols
          (0,4,8), (2,4,6)            # diagonals
      ]
      for a,b,c in wins:
          if board[a] != " " and board[a] == board[b] == board[c]:
              return board[a], (a,b,c)
      if " " not in board:
          return "DRAW", None
      return None, None
    
  def send_tictactoe_invite(self, recipient_id: str, symbol: str):
    symbol = symbol.upper()
    if symbol not in ("X", "O"):
        self.logger.error("Symbol must be X or O.")
        return

    if "@" not in recipient_id:
        for uid in self.controller.peer_map:
            if uid.startswith(f"{recipient_id}@"):
                recipient_id = uid
                break
    if recipient_id not in self.controller.peer_map:
        self.logger.error(f"[ERROR] Unknown peer: {recipient_id}")
        return
    
    gameid = f"g{len(self.controller.tictactoe_games) % 256}"
    message_id = str(uuid.uuid4())[:8]
    token = generate_token(self.controller.full_user_id, "game")
    timestamp = int(time.time())

    self.controller.tictactoe_games[gameid] = {
        "board": [" "] * 9,
        "my_symbol": symbol,
        "opponent": recipient_id,
        "turn": 0,
        "active": True
    }

    msg = make_tictaceto_invite_message(
        from_user_id=self.controller.full_user_id,
        to_user_id=recipient_id,
        game_id=gameid,
        msg_id=message_id,
        symbol=symbol,
        timestamp=timestamp,
        token=token
    )

    peer = self.controller.peer_map[recipient_id]
    self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
    self.logger.info(f"Sent Tic Tac Toe invite to {recipient_id.split('@')[0]} as {symbol}")

  def send_tictactoe_move(self, gameid: str, position: int):
    game = self.controller.tictactoe_games.get(gameid)
    if not game or not game.get("active"):
        self.logger.error(f"No active game: {gameid}")
        return
    if position < 0 or position > 8 or game["board"][position] != " ":
        self.logger.error("Invalid move")
        return

    game["board"][position] = game["my_symbol"]
    game["turn"] += 1

    winner, line = self._check_ttt_winner(game["board"])
    peer_id = game["opponent"]
    message_id = str(uuid.uuid4())[:8]
    token = generate_token(self.controller.full_user_id, "game")

    move_msg = make_tictactoe_move_message(
          from_user_id=self.controller.full_user_id,
          to_user_id=peer_id,
          gameid=gameid,
          message_id=message_id,
          position=position,
          symbol=game["my_symbol"],
          turn=game["turn"],
          token=token
    )
  
    peer = self.controller.peer_map[peer_id]
    self.controller.socket.sendto(move_msg.encode(), (peer.ip, peer.port))
    self.controller.gamemanager._print_ttt_board(game["board"])

    if winner:
        self.send_tictactoe_result(gameid, winner, line)

  def send_tictactoe_result(self, gameid: str, winner, line):
    game = self.controller.tictactoe_games.get(gameid)
    if not game:
        return
    peer_id = game["opponent"]
    result = "DRAW" if winner == "DRAW" else ( "LOSS" if winner == "LOSS" else ("WIN" if winner == game["my_symbol"] else "LOSS"))

    message_id = str(uuid.uuid4())[:8]
    timestamp = int(time.time())
    win_line_str = ",".join(map(str, line)) if line else ""

    msg = make_tictactoe_result_message(
        from_id=self.controller.full_user_id,
        to_id=peer_id,
        gameid=gameid,
        result=result,
        symbol=game["my_symbol"],
        win_line_str=win_line_str,
        message_id=message_id,
        timestamp=timestamp,
        token=generate_token(self.controller.full_user_id, "game")
    )
    
    
    peer = self.controller.peer_map[peer_id]
    self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
    self.controller.lsnp_logger.info(f"Game {gameid} ended: {result}")
    game["active"] = False

  def send_forfeit_tictactoe(self, gameid: str):
    self.send_tictactoe_result(gameid, "LOSS", None)
    
  def play_tictactoe(self, recipient_id: str):
    # Accept both formats: "user" or "user@ip"
    if "@" not in recipient_id:
        # Find the full user_id in peer_map
        full_recipient_id = None
        for user_id in self.controller.peer_map:
            if user_id.startswith(f"{recipient_id}@"):
                full_recipient_id = user_id
                break
        if not full_recipient_id:
            self.logger.error(f"[ERROR] Unknown peer: {recipient_id}")
            return
        recipient_id = full_recipient_id

    if recipient_id not in self.controller.peer_map:
        self.logger.error(f"[ERROR] Unknown peer: {recipient_id}")
        return

