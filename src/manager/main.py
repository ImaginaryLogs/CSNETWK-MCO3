from src.ui.logging import LogEntry, Logger, LoggerInstance, LogLevel

logger = Logger()

server_logger = logger.get_logger('[Server]')
verbose_logger = logger.get_logger('[Server] >>', False)

def main():
  server_logger.info("Hello World!")
  verbose_logger.info("The Message above me is printed with Logger.")
  pass

if __name__ == "__main__":
  
  main()