from typing import List, Dict, Optional, Any, Callable
from datetime import datetime
import threading
from dataclasses import dataclass
from enum import Enum
from rich.console import Console
from rich.text import Text
from datetime import timedelta
import json
import os

LOG_TIMECHECK_MINUTES = 5
LOG_DEBUG = False
LOGGER_CODENAME = 'LOGGER '
LOGGER_PREFIX = f"[blue][{LOGGER_CODENAME}][/]"
LOG_FILENAME = "logger.log"

console = Console()

class LogLevel(Enum):
  """
  Enum for different log levels.
  """
  INPUT =      "[blue][<<<<<][/]"
  DEBUG =      "[blue][     ][/]"
  INFO =      "[green][  -  ][/]"
  WARNING =  "[yellow][ /!\\ ][/]"
  ERROR =    "[red][ !!! ][/]"
  CRITICAL =    "[magenta][!!!!!][/]"
  
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
    return f"[black][{strTime}][/] {self.prefix} {self.level.value} {self.message}";
  
  def to_dict(self) -> dict:
    """_summary_

    Args:
        str (_type_): _description_

    Raises:
        RuntimeError: _description_

    Returns:
        dict: _description_
    """
    return {
      'timestamp': self.timestamp.isoformat(),
      'level': self.level.name,
      'prefix': self.prefix,
      'message': self.message
    }
    
  @classmethod
  def from_dict(cls, data: dict) -> 'LogEntry':
    """Create LogEntry from dictionary.

    Args:
        data (dict): dictionary containing valid LogEntry Values

    Returns:
        LogEntry: LogEntry class created from the dict
    """
    return cls(
      timestamp=datetime.fromisoformat(data['timestamp']),
      level=LogLevel[data['level']],
      prefix=data['prefix'],
      message=data['message']
    )
    
create_logger_entry: Callable[[LogLevel, str], 'LogEntry'] = lambda level, msg: LogEntry(datetime.now(), level, LOGGER_PREFIX, msg)

create_logger_info_entry:  Callable[[str], 'LogEntry'] = lambda msg : create_logger_entry(LogLevel.INFO, msg)

create_logger_error_entry: Callable[[str], 'LogEntry'] = lambda msg : create_logger_entry(LogLevel.ERROR, msg)

create_logger_debug_entry: Callable[[str], 'LogEntry'] = lambda msg : create_logger_entry(LogLevel.DEBUG, msg)

def _debug_logger(msg: str):
  if LOG_DEBUG: console.print(f'{create_logger_debug_entry(msg)}')

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
  
  def __init__(self, max_logs: int = 50, archive_after_minutes: int = 1, log_file: str = LOG_FILENAME) -> None:
    """
    Locally creates the Logger file within the code space.
    
    """
    if hasattr(self, '_initialized'):
      return
    
    self._logs: List[LogEntry] = []
    self._instances: Dict[str, LoggerInstance] = {} 
    self._logs_lock = threading.Lock()                    # Only the Logger Class can create logs, locked
    self._instances_lock = threading.Lock()               # Only the Logger Class can create more local instances, locked
    
    self._max_logs = max_logs
    self._archive_after_minutes = archive_after_minutes
    
    self._logs_dir = "logs"
    os.makedirs(self._logs_dir, exist_ok=True)
    self._log_file = os.path.join(self._logs_dir, log_file)
    
    self._last_archive_check = datetime.now()
    
    self._initialized = True
    return
  
  def _store_log(self, entry: LogEntry) -> None:
    """Store Logs, then locks the storage.

    Args:
        entry (LogEntry): LogEntry to store in the Logger.
    """
    with self._logs_lock:                                 #  While Logs Lock is open
      self._logs.append(entry)                            #  Append the log
      self._check_and_archive()
  
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
  
  def _check_and_archive(self) -> None:
    """Check if archiving is needed based on log count or time limits."""
    now = datetime.now()
    # Check if we have too many logs
    if len(self._logs) >= self._max_logs:
      self._archive_old_logs(reason="max_logs_reached")
      return
    
    # Check if enough time has passed since last archive check
    time_since_last_check = now - self._last_archive_check
  
    _debug_logger(f'Time since last check {time_since_last_check}')
    
    if time_since_last_check >= timedelta(minutes=LOG_TIMECHECK_MINUTES):  # Check every minute
      self._last_archive_check = now
      
      # Archive logs older than the specified time limit
      cutoff_time = now - timedelta(minutes=self._archive_after_minutes)
      old_logs = [log for log in self._logs if log.timestamp <= cutoff_time]
      
      _debug_logger(f'Old Logs Length {old_logs.__len__()}')
      
      if old_logs:
        
        _debug_logger("Time Limit Reached.")
        
        self._archive_old_logs(reason="time_limit_reached", cutoff_time=cutoff_time)
  
  def _archive_old_logs(self, reason: str = "manual", cutoff_time: Optional[datetime] = None) -> None:
    """Archive old logs to file and remove them from memory.
    
    Args:
        reason (str): Reason for archiving (for logging purposes)
        cutoff_time (datetime, optional): If provided, only archive logs older than this time
    """
    if not self._logs:
      return
    
    try:
      # Determine which logs to archive
      if cutoff_time:
        logs_to_archive = [log for log in self._logs if log.timestamp <= cutoff_time]
        logs_to_keep = [log for log in self._logs if log.timestamp > cutoff_time]
      else:
        # Archive all but the most recent 10 logs
        logs_to_archive = self._logs[:-10] if len(self._logs) > 10 else self._logs[:-1]
        logs_to_keep = self._logs[-10:] if len(self._logs) > 10 else self._logs[-1:]
      
      if not logs_to_archive: return
      
      # Prepare archive data
      archive_entry = {
        'archived_at': datetime.now().isoformat(),
        'reason': reason,
        'log_count': len(logs_to_archive),
        'logs': [log.to_dict() for log in logs_to_archive]
      }
      
      # Write to archive file
      file_exists = os.path.exists(self._log_file)
      
      with open(self._log_file, 'a', encoding='utf-8') as f:
        if file_exists:
          f.write('\n')  # Add newline separator between archive entries
        f.write(json.dumps(archive_entry, indent=2))
      
      # Update in-memory logs
      self._logs = logs_to_keep
      
      # Log the archiving action (but don't trigger another archive check)
      archive_log = create_logger_info_entry(f"Archived {len(logs_to_archive)} logs to {self._log_file} (reason: {reason})")
      
      # Directly append without triggering archive check
      self._logs.append(archive_log)
      
      if console:
        console.print(str(archive_log))
        
    except Exception as e:
      error_log = create_logger_error_entry(f"Failed to archive logs: {str(e)}")
      
      # Directly append without triggering archive check
      self._logs.append(error_log)
      
      if console:
        console.print(str(error_log))
  
  def manual_archive(self) -> None:
    """Manually trigger log archiving."""
    with self._logs_lock:
      self._archive_old_logs(reason="manual_trigger")
      
  def get_archive_stats(self) -> Dict[str, Any]:
    """Get statistics about archived logs."""
    if not os.path.exists(self._log_file):
      return {
        'archive_file_exists': False,
        'logs_directory': self._logs_dir,
        'file_size_bytes': 0,
        'current_memory_logs': len(self._logs)
      }
    
    file_size = os.path.getsize(self._log_file)
    
    return {
      'archive_file_exists': True,
      'archive_file': self._log_file,
      'logs_directory': self._logs_dir,
      'file_size_bytes': file_size,
      'file_size_mb': round(file_size / (1024 * 1024), 2),
      'current_memory_logs': len(self._logs),
      'max_logs_threshold': self._max_logs,
      'archive_after_minutes': self._archive_after_minutes
    }

  

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
  
  def _store(self, level: LogLevel, message: str, end: str = '\n') -> 'LogEntry':
    if self._parent_logger is None:
        raise RuntimeError("Logger instance not properly initialized")
    
    entry = LogEntry(
        timestamp=datetime.now(),
        level=level,
        prefix=self.prefix,
        message=message
    )
    
    self._parent_logger._store_log(entry)
    return entry
  
  def _log(self, level: LogLevel, message: str, end: str = "\n") -> None:
    """Internal method to handle logging."""
    entry = self._store(level, message, end)
    
    if self.console_enabled: 
      console.print(str(entry), end=end)
  
  def input(self, message: str, end: str = "\n") -> str:
      """Logs an Input"""
      
      if self.console_enabled: 
        print_entry = LogEntry(datetime.now(), LogLevel.INPUT, self.prefix, message)
        console.print(str(print_entry), end=end)
      
      received_input = input(message)
      
      self._store(LogLevel.INPUT, ' '.join([message, received_input]))
      
      return received_input
  
  def debug(self, message: str, end: str = "\n") -> None:
      """Log debug message."""
      self._log(LogLevel.DEBUG, message, end)
  
  def info(self, message: str, end: str = "\n") -> None:
      """Log info message."""
      self._log(LogLevel.INFO, message, end)
  
  def warning(self, message: str, end: str = "\n") -> None:
      """Log warning message."""
      self._log(LogLevel.WARNING, message, end)
  
  def error(self, message: str, end: str = "\n") -> None:
      """Log error message."""
      self._log(LogLevel.ERROR, message, end)
  
  def critical(self, message: str, end: str = "\n") -> None:
      """Log critical message."""
      self._log(LogLevel.CRITICAL, message, end)
  
  def set_console_enabled(self, enabled: bool) -> None:
      """Enable or disable console output for this instance."""
      self.console_enabled = enabled
  
  def set_prefix(self, prefix: str) -> None:
      """Change the prefix for this instance."""
      self.prefix = prefix
  
  
  
  