from typing import List, Dict, Optional, Any
from datetime import datetime
import threading
from dataclasses import dataclass
from enum import Enum
from rich.console import Console
from rich.text import Text

console = Console()

class LogLevel(Enum):
  """
  Enum for different log levels.
  """
  DEBUG = "[blue][DEBUG][/]"
  INFO = "[green][INFO][/]"
  WARNING = "[yellow][WARNING][/]"
  ERROR = "[orange][ERROR][/]"
  CRITICAL = "[red]]CRITICAL][/]"
  



@dataclass
class LogEntry:
  """
  A data class that stores related useful logging data
  """ 
  timestamp: datetime;
  level: LogLevel;
  prefix: str;
  message: str;
  
  def __str__(self) -> str:
    """Generates a string from data

    Returns:
        str: formatted string
    """
    strTime = self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3];
    return f"[black][{strTime}][/] {self.level.value} {self.prefix} {self.message}";
  
class Logger:
  """
  Records information and stores it somewhere in the server.
  """
  _instance: Optional['Logger'] = None;    # Boolean whether an instance of a Logging class was created
  _lock: threading.Lock = threading.Lock() # One way to create a singleton class within a project
  
  
  def __new__(cls) -> 'Logger':
    """
    Statically creates the Logger file in the Python Env, ensures that singleton pattern is defined properly here.
    
    Refer to https://docs.python.org/3/reference/datamodel.html
    Returns:
        Logger: _description_
    """
    if cls._instance is None:
      with cls._lock:                                     # While this class is thread locked
        if cls._instance is None:
          cls._instance = super(Logger, cls).__new__(cls) # Point the parent, cls, to a new instance to of the Logger class
          
    return cls._instance
  
  def __init__(self) -> None:
    """
    Locally creates the Logger file within the code space.
    
    """
    if hasattr(self, '_initialized'):
      return
    
    self._logs: List[LogEntry] = []
    self._instances: Dict[str, LoggerInstance] = {} 
    self._logs_lock = threading.Lock()                    # Only the Logger Class can create logs, locked
    self._instances_lock = threading.Lock()               # Only the Logger Class can create more local instances, locked
    self._initialized = True
    return
  
  def _store_log(self, entry: LogEntry) -> None:
    with self._logs_lock:                                 #  While Logs Lock is open
      self._logs.append(entry)                            #  Append the log
  
  def get_logger(self, prefix: str, console_enabled: bool = True):
    """
    Get a logger instance with specific configuration.

    Args:
        prefix (str): Prefix to be added to each message.
        console_enabled (bool, optional): Prints to console or not. Defaults to True.
    """
    instance_key = f"{prefix}"
    with self._instances_lock: 
      if instance_key not in self._instances:
        instance = LoggerInstance(prefix, console_enabled)
        instance._set_parent(self)
        self._instances[instance_key] = instance
      
      return self._instances[instance_key]
    pass  

  def get_logs(self, level: Optional[LogLevel] = None, prefix: Optional[str] = None, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> List[LogEntry]:
    """
    Retrieve stored logs with optional filtering.
    
    Args:
        level: Filter by log level
        prefix: Filter by prefix
        start_time: Filter logs after this time
        end_time: Filter logs before this time
        
    Returns:
        List of LogEntry objects matching the criteria
    """
    with self._logs_lock:
        filtered_logs = self._logs.copy()
    
    # For each filter you need, apply
    if level is not None:
        filtered_logs = [log for log in filtered_logs if log.level == level]
    
    if prefix is not None:
        filtered_logs = [log for log in filtered_logs if log.prefix == prefix]
    
    if start_time is not None:
        filtered_logs = [log for log in filtered_logs if log.timestamp >= start_time]
    
    if end_time is not None:
        filtered_logs = [log for log in filtered_logs if log.timestamp <= end_time]
    
    return filtered_logs
  
  def get_all_logs(self) -> List[LogEntry]:
    """Get all stored log entries."""
    with self._logs_lock:
      return self._logs.copy()
  
  def clear_logs(self) -> None:
    """Clear all stored log entries."""
    with self._logs_lock:
      self._logs.clear()
  
  def get_logs_as_strings(self, **kwargs) -> List[str]:
    """Get logs as formatted strings."""
    logs = self.get_logs(**kwargs)
    return [str(log) for log in logs]

  

class LoggerInstance:
  """ 
  Local logger instance with a specific configuration to that codespace.
  """
  def __init__(self, prefix: str, console_enabled: bool = True):
    self.prefix = prefix
    self.console_enabled = console_enabled
    self._parent_logger = None

  def _set_parent(self, parent_logger: 'Logger') -> None:
    """Set reference to parent singleton logger."""
    self._parent_logger = parent_logger
    
  def _log(self, level: LogLevel, message: str) -> None:
    """Internal method to handle logging."""
    if self._parent_logger is None:
        raise RuntimeError("Logger instance not properly initialized")
    
    entry = LogEntry(
        timestamp=datetime.now(),
        level=level,
        prefix=self.prefix,
        message=message
    )
    
    self._parent_logger._store_log(entry)
    
    if self.console_enabled: 
      console.print(str(entry))
  
  def debug(self, message: str) -> None:
      """Log debug message."""
      self._log(LogLevel.DEBUG, message)
  
  def info(self, message: str) -> None:
      """Log info message."""
      self._log(LogLevel.INFO, message)
  
  def warning(self, message: str) -> None:
      """Log warning message."""
      self._log(LogLevel.WARNING, message)
  
  def error(self, message: str) -> None:
      """Log error message."""
      self._log(LogLevel.ERROR, message)
  
  def critical(self, message: str) -> None:
      """Log critical message."""
      self._log(LogLevel.CRITICAL, message)
  
  def set_console_enabled(self, enabled: bool) -> None:
      """Enable or disable console output for this instance."""
      self.console_enabled = enabled
  
  def set_prefix(self, prefix: str) -> None:
      """Change the prefix for this instance."""
      self.prefix = prefix
  
  
  
  