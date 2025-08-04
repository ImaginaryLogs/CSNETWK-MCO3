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

LOG_PRINT_DAYS = False
LOG_PRINT_DATETIME = False

# Buffer configuration
BUFFER_MAX_MESSAGES = 50
BUFFER_TIME_LIMIT_MINUTES = 5

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
    datestr = "%Y-%m-%d " if LOG_PRINT_DAYS else ""
    datetimestr = self.timestamp.strftime(f'{datestr}%H:%M:%S.%f')[:-3] if LOG_PRINT_DATETIME else "" # Add: 
    timeStr = f"[black][{datetimestr}][/] " if LOG_PRINT_DATETIME else ""
    
    return f"{timeStr}{self.prefix} {self.level.value} {self.message}";
  
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

@dataclass
class BufferedLogEntry:
  """
  A buffered log entry that includes console output information
  """
  entry: LogEntry
  console_enabled: bool
  end: str = "\n"

create_logger_entry: Callable[[LogLevel, str], 'LogEntry'] = lambda level, msg: LogEntry(datetime.now(), level, LOGGER_PREFIX, msg)

create_logger_info_entry:  Callable[[str], 'LogEntry'] = lambda msg : create_logger_entry(LogLevel.INFO, msg)

create_logger_error_entry: Callable[[str], 'LogEntry'] = lambda msg : create_logger_entry(LogLevel.ERROR, msg)

create_logger_debug_entry: Callable[[str], 'LogEntry'] = lambda msg : create_logger_entry(LogLevel.DEBUG, msg)