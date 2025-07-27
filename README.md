# CSNETWK-MCO3

![Static Badge](https://img.shields.io/badge/AY2425--T3-CSNETWK-red) ![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)

> Need a Local Social Peer Network? We've got you connected and covered!

This machine project is in fulfillment for the Introduction to Computer Networks Class of De La Salle Univerity of AY2024-2025 Term 3.

| Profile | Author| Aspect |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|--------|
|[<img src="https://github.com/ClarenceAng.png" width="60px;"/><br /><sub><a href="https://github.com/ClarenceAng"></a></sub>](https://github.com/ClarenceAng/)             | Ang, Clarence <br /> (@ClarenceAng)            | Jarvis |
|[<img src="https://github.com/ImaginaryLogs.png" width="60px;"/><br /><sub><a href="https://github.com/ImaginaryLogs}"></a></sub>](https://github.com/ImaginaryLogs/)      | Campo, Roan Cedric V. <br /> (@ImaginaryLogs)  | Logs   |
|[<img src="https://github.com/InsomniacCoffee.png" width="60px;"/><br /><sub><a href="https://github.com/InsomniacCoffee}"></a></sub>](https://github.com/InsomniacCoffee/)| Go, Kenneth D. <br /> (@InsomniacCoffee)       | Coffee |
|[<img src="https://github.com/nathan1elA.png" width="60px;"/><br /><sub><a href="https://github.com/nathan1elA}"></a></sub>](https://github.com/nathan1elA/)               | Nathaniel <br /> (@nathan1elA)                 | Napalm |



## Project Overview

The structure of our code is separated to three major components: documentations `docs/`, source code `src/`, tests / quality assurance `tests/`.

The source code is partially based on the Model-View-Control MVC Format. The project architecture is specialized to fit its own needs, and that is:

- `config` - model-type, store configurations for the application.
- `game` - has controller-type files handling game logic like tic-tac-toe.
- `managers/` - has controller-type files handling the necessary \'business\' logic to handle any applications.
- `networks/` - has controller-type and model-type files handling networking logic.
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

| Task Role                               | [<img src="https://github.com/ClarenceAng.png" width="60px;"/><br /><sub><a href="https://github.com/ClarenceAng"></a></sub>](https://github.com/ClarenceAng/) @ClarenceAng (Clarence Ang) | [<img src="https://github.com/ImaginaryLogs.png" width="60px;"/><br /><sub><a href="https://github.com/ImaginaryLogs}"></a></sub>](https://github.com/ImaginaryLogs/) @ImaginaryLogs (Roan Cedric V. Campo) | [<img src="https://github.com/InsomniacCoffee.png" width="60px;"/><br /><sub><a href="https://github.com/InsomniacCoffee}"></a></sub>](https://github.com/InsomniacCoffee/) @InsomniacCoffee (Kenneth D. Go) | [<img src="https://github.com/nathan1elA.png" width="60px;"/><br /><sub><a href="https://github.com/nathan1elA}"></a></sub>](https://github.com/nathan1elA/) @nathan1elA (Nathaniel) |
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

> [!WARNING]
>
> ![ChatGPT](https://img.shields.io/badge/ChatGPT-74aa9c?logo=openai&logoColor=white) ![Claude](https://img.shields.io/badge/Claude-D97757?logo=claude&logoColor=fff)
> 
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

Simply install and run the pytest program to execute test files located in the `/tests/` directory.

```zsh
# Install pytest to your local python env
poetry install pytest

# Run pytest
poetry run pytest
```

## Documentation
### Table of Contents

#### [Milestone 1](#milestone-1)
- [Logging](#logging)  
  - [LogLevel (Enum)](#loglevel-enum)  
  - [LogEntry (Dataclass)](#logentry-dataclass)  
  - [Logger (Singleton)](#logger-singleton)  
  - [LoggerInstance](#loggerinstance)  
- [IPAddressTracker](#ipaddresstracker)  
  - [Core Tracking Methods](#core-tracking-methods)  
  - [Analysis and Statistics Methods](#analysis-and-statistics-methods)  
#### Milestone 2
#### Milestone 3

---

### Milestone 1
#### Logging
The Logger system consists of three main components:

- `Logger` - Singleton class that manages log storage and instance creation
- `LoggerInstance` - Individual logger instances with specific configurations
- `LogEntry` - Data structure for storing log information
- `LogLevel` - Enumeration defining different log levels with rich formatting

##### Classes

###### LogLevel (Enum)

Defines different log levels with rich console formatting colors:

- `INPUT` - Blue `[<<<<<]` for user input logging.
- `DEBUG` - Blue `[     ]` for debug information.
- `INFO` - Green `[  -  ]` for general information.
- `WARNING` - Yellow `[ /!\ ]` for warnings that can include special cases or handled unexpected behavior
- `ERROR` - Red `[ !!! ]` for errors. These are for features that have failed in someway.
- `CRITICAL` - Magenta `[!!!!!]` for critical issue that affect the entire system,

##### LogEntry (Dataclass)

Stores individual log entries with the following fields:

- `timestamp: datetime` - When the log was created
- `level: LogLevel` - The log level
- `prefix: str` - Custom prefix for the log source
- `message: str` - The actual log message

String Format: `[YYYY-MM-DD HH:MM:SS.mmm]` prefix `[LEVEL]` message

##### Logger (Singleton)

The main logging class that manages all log storage and instance creation.

###### Key Features

- Thread-safe singleton pattern using double-checked locking.
- Centralized log storage with thread-safe operations.
- Instance management for different logger configurations.
- Log filtering and retrieval capabilities.
- Stores Logs in a file once the length or time threshold has been reached.

###### Methods for Logger

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

##### LoggerInstance

Individual logger instances with specific configurations.

###### Methods for Logger Instance

**Logging Methods**

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

**Configuration Methods**

1) `set_console_enabled(enabled: bool) -> None` - Enable/disable console output
2) `set_prefix(prefix: str) -> None` - Change the instance prefix

#### IPAddressTracker

The IPAddressTracker is a specialized component designed to monitor, track, and analyze IP address-related network activities within the logging system. It provides comprehensive IP address management, connection monitoring, and suspicious activity detection.


##### Key Features

- **IP Discovery Tracking** - Monitors and logs when new IP addresses are first encountered
- **User-to-IP Mapping** - Maintains associations between IP addresses and user identifiers
- **Connection Attempt Monitoring** - Tracks both successful and failed connection attempts per IP
- **Suspicious Activity Detection** - Automatically flags IPs with excessive failed connection attempts
- **Traffic Flow Analysis** - Monitors message flow and data transfer between IP addresses
- **Statistical Analysis** - Provides comprehensive statistics about network activity patterns

##### Data Structures

- `known_ips: Set[str]` - Set of all discovered IP addresses
- `ip_to_user: Dict[str, str]` - Mapping of IP addresses to user identifiers
- `connection_attempts: Dict[str, int]` - Counter of connection attempts per IP
- `blocked_ips: Set[str]` - Set of IP addresses that have been flagged or blocked

##### Methods

###### Core Tracking Methods

1) > `__init__(main_logger_instance) -> None`
   > 
   > Initializes the IPAddressTracker with a reference to the main logger instance.
   > 
   > **Parameters:**
   > - `main_logger_instance` - Reference to the main Logger singleton instance for logging activities

2) > `log_new_ip(ip: str, user_id: str = None, context: str = "discovery") -> None`
   > 
   > Logs when a new IP address is encountered for the first time.
   > 
   > **Parameters:**
   > - `ip` - The IP address that was discovered
   > - `user_id` - Optional user identifier associated with this IP
   > - `context` - Context of discovery (e.g., "mdns_discovery", "profile_message", "connection")
   > **Behavior:** Adds IP to known_ips set and creates user mapping if provided. Logs discovery event with context.

3) > `log_connection_attempt(ip: str, port: int, success: bool = True) -> None`
   > 
   > Records connection attempts from specific IP addresses and monitors for suspicious patterns.
   > 
   > **Parameters:**
   > - `ip` - Source IP address of the connection attempt
   > - `port` - Target port number
   > - `success` - Whether the connection attempt was successful
   > 
   > **Behavior:** Increments connection counter, logs attempt status, and triggers suspicious activity warnings for excessive failed attempts (>10).

4) > `log_message_flow(from_ip: str, to_ip: str, msg_type: str, size: int) -> None`
   >
   > Tracks message traffic and data flow between IP addresses.
   >
   > **Parameters:**
   > - `from_ip` - Source IP address sending the message
   > - `to_ip` - Destination IP address receiving the message
   > - `msg_type` - Type of message being sent (e.g., "DM", "PROFILE", "ACK")
   > - `size` - Size of the message in bytes
   > 
   > **Behavior:** Logs detailed message flow information for traffic analysis and debugging.
   > 

###### Analysis and Statistics Methods

5) > `get_ip_stats() -> Dict[str, Any]`
   > 
   > Generates comprehensive statistics about IP address activity and network patterns.
   > 
   > **Returns:** Dictionary containing:
   > - `total_known_ips: int` - Total number of unique IP addresses encountered
   > - `mapped_users: int` - Number of IP addresses with associated user identifiers
   > - `total_connection_attempts: int` - Sum of all connection attempts across all IPs
   > - `blocked_ips: int` - Number of IP addresses flagged as suspicious or blocked
   > - `top_active_ips: List[Tuple[str, int]]` - Top 5 most active IP addresses with attempt counts

