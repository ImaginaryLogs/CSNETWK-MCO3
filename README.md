# CSNETWK-MCO3

![Static Badge](https://img.shields.io/badge/AY2425--T3-CSNETWK-red)

Link to the [Kanban Board](https://github.com/users/ImaginaryLogs/projects/2)

> [!IMPORTANT]
>
> Structure of the code:
>
>```txt
>docs/
> ├── CSNETWK MP Rubric.pdf
> │
> ├── CSNETWK MP RFC.pdf
> │
> └── TaskToDo.md
>src/
> ├── __init__.py
> │
> ├── config/                 <--: Configs
> │   └── ...
> ├── game/                   <--: Game state, player assets
> │   └── ...
> ├── manager/                <--: Core/Controller/Managers
> │   └── ...
> ├── protocol/               <--: Protocol and Type Definitions
> │   ├── ... 
> │   │
> │   └── types/   
> │       ├── games
> │       │
> │       └── messages
> ├── ui                      <--: UI/Terminal/View
> │   └── ...
> └── utils/                  <--: Helper files
>     └── ...
> tests/
> ├── __init__.py
> │
> ├── manager
> │   └── ...
> ├── network
> │   └── ...
> └── protocol
>     └── ...
> pyproject.toml
> __init__.py
> README.md
>```
>

## Installation

`pip install -r requirements.txt`

`pip install -e .`

`pip install poetry`

`poetry install`

Reselect your python interpreter to the local instance.

`poetry add <your-library-to-add>`

Run the server `poetry run python src/manager/main.py`.

## Testing

`poetry install pytest`

`poetry run pytest`

## Documentation

### Milestone 1

The Logger system consists of three main components:

- `Logger` - Singleton class that manages log storage and instance creation
- `LoggerInstance` - Individual logger instances with specific configurations
- `LogEntry` - Data structure for storing log information
- `LogLevel` - Enumeration defining different log levels with rich formatting

#### Classes

##### LogLevel (Enum)

Defines different log levels with rich console formatting colors:

- `INPUT` - Blue `[<<<<]` for user input logging.
- `DEBUG` - Blue `[DEBG]` for debug information.
- `INFO` - Green `[INFO]` for general information.
- `WARNING` - Yellow `[WARN]` for warnings that can include special cases or handled unexpected behavior
- `ERROR` - Orange `[EROR]` for errors. These are for features that have failed in someway.
- `CRITICAL` - Red `[CRIT]` for critical issue that affect the entire system,

#### LogEntry (Dataclass)

Stores individual log entries with the following fields:

- `timestamp: datetime` - When the log was created
- `level: LogLevel` - The log level
- `prefix: str` - Custom prefix for the log source
- `message: str` - The actual log message

String Format: `[YYYY-MM-DD HH:MM:SS.mmm]` prefix `[LEVEL]` message

#### Logger (Singleton)

The main logging class that manages all log storage and instance creation.

##### Key Features

- Thread-safe singleton pattern using double-checked locking
- Centralized log storage with thread-safe operations
- Instance management for different logger configurations
- Log filtering and retrieval capabilities

##### Methods for Logger

1) > `get_logger(prefix: str, console_enabled: bool = True) -> LoggerInstance`
   > Creates or retrieves a logger instance with specific configuration.
   >
   > **Parameters**
   >
   > - `prefix` - Custom prefix for all messages from this instance
   > - `console_enabled` - Whether to print logs to console (default: True)
   >
   > **Returns**: LoggerInstance object

2) > `get_logs(level=None, prefix=None, start_time=None, end_time=None) -> List[LogEntry]`
   > Retrieves stored logs with optional filtering.
   >
   > **Parameters**
   >
   > - `level: Optional[LogLevel]` - Filter by specific log level
   > - `prefix: Optional[str]` - Filter by prefix
   > - `start_time: Optional[datetime]` - Filter logs after this time
   > - `end_time: Optional[datetime]` - Filter logs before this time
   >
   > **Returns**: List of LogEntry objects matching criteria

3) > `get_all_logs() -> List[LogEntry]`
   >
   > **Returns**: all stored log entries.

4) > `clear_logs() -> None`
   >
   > Clears all stored log entries.

5) > `get_logs_as_strings(**kwargs) -> List[str]`
   >
   > **Returns** logs as formatted strings using the same filtering options as get_logs().

#### LoggerInstance

Individual logger instances with specific configurations.

##### Methods for Logger Instance

###### Logging Methods

1) > `input(message: str, end: str = "\n") -> str`
   > Logs input and prompts for user input
2) > `debug(message: str, end: str = "\n") -> None`
   > Logs debug messages
3) > `info(message: str, end: str = "\n") -> None`
   > Logs informational messages
4) > `warning(message: str, end: str = "\n") -> None`
   > Logs warnings
5) > `error(message: str, end: str = "\n") -> None`
   > Logs errors
6) > `critical(message: str, end: str = "\n") -> None`
   > Logs critical messages

##### Configuration Methods

1) `set_console_enabled(enabled: bool) -> None` - Enable/disable console output
2) `set_prefix(prefix: str) -> None` - Change the instance prefix
