# CSNETWK-MCO3

![Static Badge](https://img.shields.io/badge/AY2425--T3-CSNETWK-red) ![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)

> Need a Local Social Peer Network? We got you connected and covered!

This machine project is in fulfillment for the Introduction to Computer Networks Class of De La Salle Univerity of AY2024-2025 Term 3.

## Project Overview

The structure of our code is separated to three major components: documentations `docs/`, source code `src/`, tests / quality assurance `tests/`.

The source code is partially based on the Model-View-Control MVC Format. The project architecture is specialized to fit its own needs, and that is:

- `config` - model-type, store configurations for the application.
- `game` - has controller-type files handling game logic like tic-tac-toe.
- `managers/` - has controller-type files handling the necessary \'business\' logic to handle any applications.
- `networks/` - has controller-type files handling networking logic.
- `protocol/` - has model-type files handling token parsing, protocol parsing, and any files dealing with non-logging data handling and storage.
- `ui/` - has view-type files handling logging, cli output and formatting. Logging data is handled here.

> [!NOTE]
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
> │
> ├── game/                   <--: Game state, player assets
> │   └── ...
> │
> ├── manager/                <--: Core/Controller/Managers
> │   └── ...
> │
> ├── protocol/               <--: Protocol and Type Definitions
> │   ├── ... 
> │   │
> │   └── types/   
> │       ├── games           <--: Key-Value Dict Type definitions for Tic, Tac, Toe
> │       │
> │       └── messages        <--: Key-Value Dict Type definitions for Profiles, DMs, Ack and Ping
> │
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
> __init__.py
> makefile
> pyproject.toml
> poetry.lock
> pyproject.toml
> README.md
> requirements.txt
> ...
>```
>

When performing Milestone Tracking and Deliverables, it is being done in the [Kanban Board](https://github.com/users/ImaginaryLogs/projects/2)

| Task Role                               | @ImaginaryLogs (Roan Cedric V. Campo) | @InsomniacCoffee (Kenneth D. Go) | @ClarenceAng (Clarence Ang) | @nathan1elA (Nathaniel) |
|-----------------------------------------|---------------------------------------|----------------------------------|-----------------------------|-------------------------|
| **Network Communication**               |                                       |                                  |                             |                         |
| UDP Socket Setup                        |                                       |                                  |                             |                         |
| mDNS Discovery Integration              |                                       |                                  |                             |                         |
| IP Address Logging                      |                                       |                                  |                             |                         |
| **Core Feature Implementation**         |                                       |                                  |                             |                         |
| Core Messaging (POST, DM, LIKE, FOLLOW) |                                       |                                  |                             |                         |
| File Transfer (Offer, Chunk, ACK)       |                                       |                                  |                             |                         |
| Tic Tac Toe Game (with recovery)        |                                       |                                  |                             |                         |
| Group Creation / Messaging              |                                       |                                  |                             |                         |
| Induced Packet Loss (Game & File)       |                                       |                                  |                             |                         |
| Acknowledgement / Retry                 |                                       |                                  |                             |                         |
| **UI & Logging**                        |                                       |                                  |                             |                         |
| Verbose Mode Support                    |                                       |                                  |                             |                         |
| Terminal Grid Display                   |                                       |                                  |                             |                         |
| Message Parsing & Debug Output          |                                       |                                  |                             |                         |
| **Testing and Validation**              |                                       |                                  |                             |                         |
| Inter-group Testing                     |                                       |                                  |                             |                         |
| Correct Parsing Validation              |                                       |                                  |                             |                         |
| Token Expiry & IP Match                 |                                       |                                  |                             |                         |
| **Documentation & Coordination**        |                                       |                                  |                             |                         |
| RFC & Project Report                    |                                       |                                  |                             |                         |
| Milestone Tracking & Deliverables       |                                       |                                  |                             |                         |

## Disclaimer

> ![WARNING]
>
> ![ChatGPT](https://img.shields.io/badge/ChatGPT-74aa9c?logo=openai&logoColor=white) ![Claude](https://img.shields.io/badge/Claude-D97757?logo=claude&logoColor=fff)
> Parts of the code documentation in this project were generated or assisted by AI tools, including OpenAI's [ChatGPT](https://chatgpt.com/) and Anthropic's [Claude](https://www.anthropic.com/claude). While care has been taken to review and verify the content, automated outputs may contain errors or omissions. Please review critically and contribute improvements where necessary when reading documentation.

## Installation

Some dependencies are required to install for this project to work. As such to handle many dependencies, the [poetry](https://python-poetry.org/) python dependencies manager is used to manage such dependencies.

```zsh
pip install -r requirements.txt

pip install -e .

poetry install
```

Then, reselect your python interpreter to the local instance.

```zsh
# Adds a library 
poetry add 'your-library-to-add'

# Removes a library
poetry remove 'your-library-to-remove'
```

Run the server `poetry run python src/manager/main.py`.

## Testing

Performing quality assurance is done via pytest for automatic test generation and qualification.

Simply install and run the pytest program to execute test files located in `/tests/`.

```zsh
# Install pytest to your local python env
poetry install pytest

# Run pytest
poetry run pytest
```

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

- Thread-safe singleton pattern using double-checked locking.
- Centralized log storage with thread-safe operations.
- Instance management for different logger configurations.
- Log filtering and retrieval capabilities.
- Stores Logs in a file once the length or time threshold has been reached.

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
