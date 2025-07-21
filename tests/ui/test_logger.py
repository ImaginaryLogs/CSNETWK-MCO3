try: 
  from src.ui.logging import LogLevel, LogEntry, Logger, LoggerInstance
except ImportError as e:
  print(f"Failed to import. Error: {e}")

def test_singleton():
  logger1 = Logger()
  logger2 = Logger()
  assert logger1 is logger2, "Logger does not work as a singleton"
  print("[Test][Logger] Test Singleton complete") # Have to use regular print statements

def test_general_usage():
  logger = Logger()


  # Create different logger instances for different parts of your application
  server_logger = logger.get_logger("[SERVER]", console_enabled=True)
  client_logger = logger.get_logger("[CLIENT]", console_enabled=True)
  debug_logger = logger.get_logger("[DEBUG]", console_enabled=False)

  # Use the loggers
  server_logger.info("Server starting up")
  server_logger.warning("Low memory warning")

  client_logger.info("Client connected")
  client_logger.error("Connection failed")

  debug_logger.debug("This won't print to console")
  debug_logger.info("But it's still stored")

  # Retrieve logs
  print("\n--- All logs ---")
  all_logs = logger.get_all_logs()
  for log in all_logs:
      print(log)


  # Filter logs by prefix
  print("\n--- Server logs only ---")
  server_logs = logger.get_logs(prefix="[SERVER]")
  for log in server_logs:
      print(log)

  # Filter logs by level
  print("\n--- Error logs only ---")
  error_logs = logger.get_logs(level=LogLevel.ERROR)
  for log in error_logs:
      print(log)

  # Modify instance settings
  server_logger.set_console_enabled(False)
  server_logger.info("This won't print to console")

  # But you can still retrieve it
  print("\n--- Latest server log (stored but not printed) ---")
  latest_server_logs = logger.get_logs(prefix="[SERVER]")
  print(latest_server_logs[-1])