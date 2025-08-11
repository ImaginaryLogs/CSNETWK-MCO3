from src.ui.logging import LoggerInstance

class GameManager:
  def __init__(self, logger: "LoggerInstance"):
      self.logger = logger
      
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
