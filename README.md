# CSNETWK-MCO3

![Static Badge](https://img.shields.io/badge/AY2425--T3-CSNETWK-red) ![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)

> Need a Local Social Peer Network? We've got you connected and covered!

This machine project is in fulfillment for the Introduction to Computer Networks Class of De La Salle Univerity of AY2024-2025 Term 3.

| Profile                                                                                                                                                                     | Author                                        | Aspect |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- | ------ |
| [<img src="https://github.com/ClarenceAng.png" width="60px;"/><br /><sub><a href="https://github.com/ClarenceAng"></a></sub>](https://github.com/ClarenceAng/)              | Ang, Clarence <br /> (@ClarenceAng)           | Jarvis |
| [<img src="https://github.com/ImaginaryLogs.png" width="60px;"/><br /><sub><a href="https://github.com/ImaginaryLogs}"></a></sub>](https://github.com/ImaginaryLogs/)       | Campo, Roan Cedric V. <br /> (@ImaginaryLogs) | Logs   |
| [<img src="https://github.com/InsomniacCoffee.png" width="60px;"/><br /><sub><a href="https://github.com/InsomniacCoffee}"></a></sub>](https://github.com/InsomniacCoffee/) | Go, Kenneth D. <br /> (@InsomniacCoffee)      | Coffee |
| [<img src="https://github.com/nathan1elA.png" width="60px;"/><br /><sub><a href="https://github.com/nathan1elA}"></a></sub>](https://github.com/nathan1elA/)                | Nathaniel <br /> (@nathan1elA)                | Napalm |

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
> ```txt
> docs/
> ├── CSNETWK MP Rubric.pdf
> │
> ├── CSNETWK MP RFC.pdf
> │
> └── TaskToDo.md
> src/
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
> ```

When performing Milestone Tracking and Deliverables, it is being done in the [Kanban Board](https://github.com/users/ImaginaryLogs/projects/2)

| Task Role                               | [<img src="https://github.com/ClarenceAng.png" width="60px;"/><br /><sub><a href="https://github.com/ClarenceAng"></a></sub>](https://github.com/ClarenceAng/) @ClarenceAng (Clarence Ang) | [<img src="https://github.com/ImaginaryLogs.png" width="60px;"/><br /><sub><a href="https://github.com/ImaginaryLogs}"></a></sub>](https://github.com/ImaginaryLogs/) @ImaginaryLogs (Roan Cedric V. Campo) | [<img src="https://github.com/InsomniacCoffee.png" width="60px;"/><br /><sub><a href="https://github.com/InsomniacCoffee}"></a></sub>](https://github.com/InsomniacCoffee/) @InsomniacCoffee (Kenneth D. Go) | [<img src="https://github.com/nathan1elA.png" width="60px;"/><br /><sub><a href="https://github.com/nathan1elA}"></a></sub>](https://github.com/nathan1elA/) @nathan1elA (Nathaniel) |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Network Communication**               |                       |                             |                       |                    |
| UDP Socket Setup                        | P                     | S                           | R                     |                    |
| mDNS Discovery Integration              | S                     | P                           |                       | R                  |
| IP Address Logging                      | R                     | P                           | S                     |                    |
| **Core Feature Implementation**         |                       |                             |                       |                    |
| Core Messaging (POST, DM, LIKE, FOLLOW) | P                     | R                           | S                     |                    |
| File Transfer (Offer, Chunk, ACK)       | S                     |                             | P                     | R                  |
| Tic Tac Toe Game (with recovery)        | R                     | S                           | P                     |                    |
| Group Creation / Messaging              | S                     | R                           |                       | P                  |
| Induced Packet Loss (Game & File)       | P                     |                             | R                     | S                  |
| Acknowledgement / Retry                 |                       | P                           | S                     | R                  |
| **UI & Logging**                        |                       |                             |                       |                    |
| Verbose Mode Support                    | S                     | P                           | R                     |                     |
| Terminal Grid Display                   | R                     | S                           | P                     |                     |
| Message Parsing & Debug Output          | P                     | R                           | S                     |                     |
| **Testing and Validation**              |                       |                             |                       |                    |
| Inter-group Testing                     | S                     | P                           |                       | R                  |
| Correct Parsing Validation              | R                     | S                           |                       | P                  |
| Token Expiry & IP Match                 |                       | R                           | S                     | P                  |
| **Documentation & Coordination**        |                       |                             |                       |                    |
| RFC & Project Report                    | P                     | S                           | R                     |                     |
| Milestone Tracking & Deliverables       | S                     | R                           |                       | P                  |

| Name      | Primary | Secondary | Reviewer |
|-----------|---------|-----------|----------|
| Clarence  |   5     |    5      |    5     |
| Roan      |   5     |    5      |    5     |
| Kenneth   |   5     |    5      |    5     |
| Nathaniel |   5     |    5      |    5     |

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

- [CSNETWK-MCO3](#csnetwk-mco3)
  - [Project Overview](#project-overview)
  - [Disclaimer](#disclaimer)
  - [Installation](#installation)
  - [Testing](#testing)
  - [Documentation](#documentation)
    - [Table of Contents](#table-of-contents)
    - [Milestone 1](#milestone-1)
      - [Logging](#logging)
        - [Classes](#classes)
          - [LogLevel (Enum)](#loglevel-enum)
        - [LogEntry (Dataclass)](#logentry-dataclass)
        - [Logger (Singleton)](#logger-singleton)
          - [Key Features](#key-features)
          - [Methods for Logger](#methods-for-logger)
        - [LoggerInstance](#loggerinstance)
          - [Methods for Logger Instance](#methods-for-logger-instance)
          - [Logging Methods](#logging-methods)
          - [Configuration Methods](#configuration-methods)
      - [IP Address Tracker](#ip-address-tracker)
        - [Key Features for IP Address Tracker](#key-features-for-ip-address-tracker)
        - [Data Structures](#data-structures)
        - [Methods](#methods)
          - [Core Tracking Methods](#core-tracking-methods)
          - [Analysis and Statistics Methods](#analysis-and-statistics-methods)
      - [Network Discovery](#network-discovery)
        - [PeerListener (ServiceListener)](#peerlistener-servicelistener)
          - [Key Features for PeerListener](#key-features-for-peerlistener)
          - [Data Structures](#data-structures-1)
          - [Methods for PeerListener](#methods-for-peerlistener)
        - [Peer Class](#peer-class)
          - [Key Features for Peer](#key-features-for-peer)
          - [Data Structure](#data-structure)
        - [mDNS Service Registration](#mdns-service-registration)
          - [Service Registration Process](#service-registration-process)
          - [Integration with LSNPController](#integration-with-lsnpcontroller)
      - [LSNP Protocol Parser](#lsnp-protocol-parser)
        - [Core Parsing Methods](#core-parsing-methods)
      - [LSNPController](#lsnpcontroller)
        - [Key Features for LSNPController](#key-features-for-lsnpcontroller)
        - [Data Structures](#data-structures-2)
        - [Core Methods](#core-methods)
        - [Message Handling](#message-handling)
          - [Key-Value Message Processing](#key-value-message-processing)
          - [Legacy JSON Support](#legacy-json-support)
        - [Network Integration](#network-integration)
          - [UDP Socket Configuration](#udp-socket-configuration)
          - [Threading Architecture](#threading-architecture)
        - [Command Interface](#command-interface)
        - [Error Handling and Reliability](#error-handling-and-reliability)
- [File Transfer System](#file-transfer-system)
  - [Key Features for File Transfer](#key-features-for-file-transfer)
  - [Core Classes](#core-classes)
    - [FileTransfer](#filetransfer)
      - [Data Structure](#data-structure-1)
      - [Key Methods](#key-methods)
  - [File Transfer Protocol Messages](#file-transfer-protocol-messages)
    - [FILE\_OFFER Message](#file_offer-message)
    - [FILE\_ACCEPT/FILE\_REJECT Messages](#file_acceptfile_reject-messages)
    - [FILE\_CHUNK Message](#file_chunk-message)
    - [FILE\_RECEIVED Message](#file_received-message)
  - [LSNPController File Transfer Methods](#lsnpcontroller-file-transfer-methods)
    - [Sending Files](#sending-files)
    - [Receiving Files](#receiving-files)
    - [File Storage and Organization](#file-storage-and-organization)
      - [Directory Structure](#directory-structure)
      - [File Path Resolution for Sending](#file-path-resolution-for-sending)
  - [Message Handling Implementation](#message-handling-implementation)
    - [File Offer Processing](#file-offer-processing)
    - [Chunk Reception](#chunk-reception)
    - [Transfer Completion](#transfer-completion)
    - [Response Handling](#response-handling)
  - [Configuration Constants](#configuration-constants)
  - [Command Line Interface](#command-line-interface)
    - [File Transfer Commands](#file-transfer-commands)
    - [Usage Examples](#usage-examples)
  - [Error Handling and Recovery](#error-handling-and-recovery)
    - [Network Resilience](#network-resilience)
    - [User Experience](#user-experience)
    - [Security Features](#security-features)

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

1. > `get_logger(prefix: str, console_enabled: bool = True) -> LoggerInstance`
   > Creates or retrieves a logger instance with specific configuration.
   >
   > **Parameters**
   >
   > - `prefix` - Custom prefix for all messages from this instance
   > - `console_enabled` - Whether to print logs to console (default: True)
   >
   > **Returns**: LoggerInstance object

2. > `get_logs(level=None, prefix=None, start_time=None, end_time=None) -> List[LogEntry]`
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

3. > `get_all_logs() -> List[LogEntry]`
   >
   > **Returns**: all stored log entries.

4. > `clear_logs() -> None`
   >
   > Clears all stored log entries.

5. > `get_logs_as_strings(**kwargs) -> List[str]`
   >
   > **Returns** logs as formatted strings using the same filtering options as get_logs().

##### LoggerInstance

Individual logger instances with specific configurations.

###### Methods for Logger Instance

###### Logging Methods

1. > `input(message: str, end: str = "\n") -> str`
   > Logs input and prompts for user input
2. > `debug(message: str, end: str = "\n") -> None`
   > Logs debug messages
3. > `info(message: str, end: str = "\n") -> None`
   > Logs informational messages
4. > `warning(message: str, end: str = "\n") -> None`
   > Logs warnings
5. > `error(message: str, end: str = "\n") -> None`
   > Logs errors
6. > `critical(message: str, end: str = "\n") -> None`
   > Logs critical messages

###### Configuration Methods

1. `set_console_enabled(enabled: bool) -> None` - Enable/disable console output
2. `set_prefix(prefix: str) -> None` - Change the instance prefix

#### IP Address Tracker

The IP Address Tracker is a specialized component designed to monitor, track, and analyze IP address-related network activities within the logging system. It provides comprehensive IP address management, connection monitoring, and suspicious activity detection.

##### Key Features for IP Address Tracker

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

1. > `__init__(main_logger_instance) -> None`
   >
   > Initializes the IPAddressTracker with a reference to the main logger instance.
   >
   > **Parameters:**
   >
   > - `main_logger_instance` - Reference to the main Logger singleton instance for logging activities

2. > `log_new_ip(ip: str, user_id: str = None, context: str = "discovery") -> None`
   >
   > Logs when a new IP address is encountered for the first time.
   >
   > **Parameters:**
   >
   > - `ip` - The IP address that was discovered
   > - `user_id` - Optional user identifier associated with this IP
   > - `context` - Context of discovery (e.g., "mdns_discovery", "profile_message", "connection")
   >   **Behavior:** Adds IP to known_ips set and creates user mapping if provided. Logs discovery event with context.

3. > `log_connection_attempt(ip: str, port: int, success: bool = True) -> None`
   >
   > Records connection attempts from specific IP addresses and monitors for suspicious patterns.
   >
   > **Parameters:**
   >
   > - `ip` - Source IP address of the connection attempt
   > - `port` - Target port number
   > - `success` - Whether the connection attempt was successful
   >
   > **Behavior:** Increments connection counter, logs attempt status, and triggers suspicious activity warnings for excessive failed attempts (>10).

4. > `log_message_flow(from_ip: str, to_ip: str, msg_type: str, size: int) -> None`
   >
   > Tracks message traffic and data flow between IP addresses.
   >
   > **Parameters:**
   >
   > - `from_ip` - Source IP address sending the message
   > - `to_ip` - Destination IP address receiving the message
   > - `msg_type` - Type of message being sent (e.g., "DM", "PROFILE", "ACK")
   > - `size` - Size of the message in bytes
   >
   > **Behavior:** Logs detailed message flow information for traffic analysis and debugging.

###### Analysis and Statistics Methods

5. > `get_ip_stats() -> Dict[str, Any]`
   >
   > Generates comprehensive statistics about IP address activity and network patterns.
   >
   > **Returns:** Dictionary containing:
   >
   > - `total_known_ips: int` - Total number of unique IP addresses encountered
   > - `mapped_users: int` - Number of IP addresses with associated user identifiers
   > - `total_connection_attempts: int` - Sum of all connection attempts across all IPs
   > - `blocked_ips: int` - Number of IP addresses flagged as suspicious or blocked
   > - `top_active_ips: List[Tuple[str, int]]` - Top 5 most active IP addresses with attempt counts

#### Network Discovery

The Network Discovery system implements mDNS (Multicast DNS) service discovery to automatically find and connect with peers on the local network. It consists of peer management, service registration, and discovery components.

##### PeerListener (ServiceListener)

A specialized service listener that handles mDNS service discovery events for peer-to-peer networking.

###### Key Features for PeerListener

- **Automatic Peer Discovery** - Monitors mDNS broadcasts to discover new peers joining the network
- **Peer Registration** - Automatically registers discovered peers in the peer mapping system
- **Service Event Handling** - Responds to service addition, removal, and update events
- **IP Address Resolution** - Resolves peer IP addresses from mDNS service information
- **User Identification** - Extracts user identifiers and display names from service properties

###### Data Structures

- `peer_map: Dict[str, Peer]` - Dictionary mapping full user IDs to Peer objects
- `on_discover: Callable[[Peer], None]` - Callback function executed when new peers are discovered

###### Methods for PeerListener

1. > `__init__(peer_map: Dict[str, Peer], on_discover: Callable[[Peer], None]) -> None`
   >
   > Initializes the PeerListener with peer management and discovery callback.
   >
   > **Parameters:**
   >
   > - `peer_map` - Reference to the main peer dictionary for storing discovered peers
   > - `on_discover` - Callback function to execute when a new peer is discovered

2. > `add_service(zeroconf: Zeroconf, type: str, name: str) -> None`
   >
   > Handles new mDNS service discovery events and registers discovered peers.
   >
   > **Parameters:**
   >
   > - `zeroconf` - Zeroconf instance for service information retrieval
   > - `type` - Service type identifier
   > - `name` - Service name identifier
   >
   > **Behavior:**
   >
   > - Retrieves service information from mDNS broadcast
   > - Extracts user_id, display_name, IP address, and port from service properties
   > - Creates full_user_id in format "user_id@ip_address"
   > - Prevents duplicate peer registration
   > - Creates new Peer object and adds to peer_map
   > - Triggers on_discover callback for newly discovered peers

3. > `remove_service(*args) -> None`
   >
   > Handles mDNS service removal events (currently no-op implementation).

4. > `update_service(*args) -> None`
   >
   > Handles mDNS service update events (currently no-op implementation).

##### Peer Class

Represents a discovered network peer with connection information.

###### Key Features for Peer

- **User Identification** - Stores unique user ID and display name
- **Network Information** - Maintains IP address and port for communication
- **Connection State** - Tracks peer availability and connection status

###### Data Structure

```python
class Peer:
    user_id: str        # Full user ID in format "username@ip_address"
    display_name: str   # Human-readable display name
    ip: str            # IP address for network communication
    port: int          # Port number for UDP communication
```

##### mDNS Service Registration

The system automatically registers each peer as an mDNS service for network-wide discovery.

###### Service Registration Process

1. **Service Type** - Uses predefined `MDNS_SERVICE_TYPE` for service identification
2. **Service Name** - Formats as `{user_id}_at_{ip_with_underscores}.{service_type}`
3. **Service Properties** - Includes:
   - `user_id` - Unique identifier for the user
   - `display_name` - Human-readable name for display purposes
4. **Network Information** - Binds to peer's IP address and communication port
5. **Automatic Broadcasting** - Continuously broadcasts service availability on the network

###### Integration with LSNPController

The mDNS system integrates seamlessly with the main `LSNPController`:

- **Service Browser** - Automatically starts mDNS service discovery on initialization
- **Peer Callback** - Registers discovered peers and logs discovery events
- **IP Tracking** - Integrates with IP Address Tracker for network monitoring
- **Connection Management** - Maintains peer connection state and availability

#### LSNP Protocol Parser

The LSNP protocol uses a key-value pair structure with messages separated by newline characters. Each message is expected to follow this format:

```
Key1: Value1
Key2: Value2
Key3: Value3
```

Where each key-value pair is separated by a newline, and messages are separated by an additional newline.

##### Core Parsing Methods

1. > `parse_lsnp_messages(raw_message: str, verbose: bool) -> dict`
   >
   > Parses raw LSNP message strings into structured key-value dictionaries.
   >
   > **Parameters:**
   >
   > - `raw_message (str)` - The raw LSNP message string to parse
   > - `verbose (bool)` - If True, print debug information during parsing
   >
   > **Returns:** Dictionary of key-value pairs extracted from the message
   >
   > **Behavior:** Splits message by newlines, processes each key-value pair, handles malformed entries gracefully

2. > `format_lsnp_message(msg_data: dict, verbose: bool) -> str`
   >
   > Formats dictionary data into LSNP protocol message format.
   >
   > **Parameters:**
   >
   > - `msg_dict (dict)` - Dictionary of key-value pairs to format
   > - `verbose (bool)` - If True, print debug information during formatting
   >
   > **Returns:** LSNP-formatted message string ending with `\n\n`
   >
   > **Behavior:** Converts dictionary to key-value format, ensures proper message termination

#### LSNPController

The main controller class that manages peer-to-peer networking, message handling, and service discovery for the Local Social Network Protocol.

##### Key Features for LSNPController

- **UDP Socket Management** - Handles UDP socket creation, binding, and broadcasting
- **mDNS Integration** - Automatic peer discovery and service registration
- **Message Processing** - Handles both key-value and legacy JSON message formats
- **Direct Messaging** - Reliable message delivery with acknowledgment and retry mechanisms
- **Ping and Profile Broadcasting** - Periodic and manual profile announcements to peers
- **IP Address Tracking** - Comprehensive network monitoring and statistics
- **Peer Management** - Maintains active peer connections and availability

##### Data Structures

- `user_id: str` - Unique identifier for this peer
- `display_name: str` - Human-readable name for display
- `ip: str` - Own IP address for network communication
- `port: int` - UDP port for message reception
- `full_user_id: str` - Complete identifier in format "user_id@ip_address"
- `peer_map: Dict[str, Peer]` - Active peer connections
- `inbox: List[str]` - Received message storage
- `ack_events: Dict[str, threading.Event]` - Acknowledgment tracking for sent messages

##### Core Methods

1. > `__init__(user_id: str, display_name: str, port: int = LSNP_PORT, verbose: bool = True, avatar_path: str = None) -> None`
   >
   > Initializes the LSNP controller with user information and network configuration.
   >
   > **Parameters:**
   >
   > - `user_id` - Unique identifier for this peer
   > - `display_name` - Human-readable display name
   > - `port` - UDP port for communication (default: LSNP_PORT)
   > - `verbose` - Enable detailed logging and debug output
   > - `avatar_path` - Optional path to user avatar image for profile broadcasting
   >
   > **Behavior:** Sets up UDP socket, registers mDNS service, starts background threads, initializes IP tracker

2. > `send_dm(recipient_id: str, content: str) -> None`
   >
   > Sends direct messages to specified peers with acknowledgment and retry logic.
   >
   > **Parameters:**
   >
   > - `recipient_id` - Target peer identifier (accepts "user" or "user@ip" format)
   > - `content` - Message content to send
   >
   > **Behavior:** Validates recipient, generates message token, implements retry mechanism with exponential backoff, tracks acknowledgments

3. > `broadcast_profile() -> None`
   >
   > Broadcasts profile information to all known peers in the network.
   >
   > **Behavior:** Sends profile message to all peers in peer_map, logs successful and failed transmissions

4. > `list_peers() -> None`
   >
   > Displays information about all discovered and active peers.
   >
   > **Output:** Shows peer count, display names, user IDs, and network addresses

5. > `show_inbox() -> None`
   >
   > Displays all received messages in chronological order.
   >
   > **Output:** Formatted message list with timestamps and sender information

6. > `show_ip_stats() -> None`
   >
   > Displays comprehensive IP address and network activity statistics.
   >
   > **Output:** Total IPs, mapped users, connection attempts, blocked IPs, and most active addresses

7. > `follow(user_id: str) -> None`
   >
   > Adds a peer to the following list and sends a FOLLOW message with acknowledgment and retry logic.
   >
   > Parameters:
   > user_id – Identifier of the target peer (accepts short form "user" or full "user@ip").
   >
   > Behavior:
   > Resolves short user_id to full format using peer_map.
   > Validates that the peer exists and is not self.
   > Adds peer to following set.
   > Builds and sends a FOLLOW message to the peer with retry mechanism and acknowledgment handling.

8. > `unfollow(user_id: str) -> None`
   >
   > Removes a peer from the following list and sends an UNFOLLOW message with acknowledgment and retry logic.
   >
   > Parameters:
   > user_id – Identifier of the target peer (accepts short form "user" or full "user@ip").
   >
   > Behavior:
   > Resolves short user_id to full format using peer_map.
   > Validates that the peer exists, is not self, and is currently followed.
   > Removes peer from following set.
   > Builds and sends an UNFOLLOW message to the peer with retry mechanism and acknowledgment handling.

9. > `send_post(content: str) -> None`
   >
   > Sends a post message to all followers with retry and acknowledgment tracking.
   >
   > Parameters:
   > content – Text content of the post.
   >
   > Behavior:
   > Checks if there are followers; exits if none.
   > Creates a POST message for each follower with unique message_id and security token.
   > Sends messages in batch, tracks acknowledgment events.
   > Implements retry logic for unacknowledged peers with exponential backoff.
   > Logs delivery status and cleans up acknowledgment data.

   10.> toggle_like(post_timestamp_id: str, owner_name: str) -> None

   > Toggles like status on a post (LIKE if not liked, UNLIKE if already liked) and sends an update to the post owner.
   >
   > Parameters:
   > post_timestamp_id – Unique identifier of the post (timestamp-based).
   > owner_name – Display name or short user ID of the post owner.
   >
   > Behavior:
   > Resolves owner name to full user ID via peer_map.
   > Determines current like state and selects action (LIKE or UNLIKE).
   > Builds and sends a LIKE message to the owner with acknowledgment and retry logic.
   > Updates local like state upon confirmation.

##### Message Handling

###### Key-Value Message Processing

The controller handles LSNP protocol messages in key-value format:

- **PROFILE Messages** - Peer discovery and registration
- **DM Messages** - Direct message delivery with token validation
- **ACK Messages** - Message acknowledgment handling
- **PING Messages** - Network connectivity testing

###### Legacy JSON Support

Maintains backward compatibility with JSON message format for transition period.

##### Network Integration

###### UDP Socket Configuration

- **Broadcasting Enabled** - Supports network-wide message distribution
- **Non-blocking Reception** - Continuous message listening without blocking main thread
- **Error Handling** - Graceful handling of malformed messages and network errors

###### Threading Architecture

- **Message Listener** - Dedicated thread for incoming message processing
- **mDNS Browser** - Background service discovery monitoring
- **Periodic Broadcasting** - Scheduled profile and ping announcements every 5 minutes

##### Command Interface

The controller provides an interactive command-line interface:

- `help` - Display available commands
- `peers` - List discovered peers
- `dms` - Show message inbox
- `dm <user> <message>` - Send direct message
- `post <content>` - Post for your followers
- `like <post_timestamp> <user_id>` - Like a user's post
- `ttl <number>` - Set the TTL
- `follow <user>` - Follow a user
- `unfollow <user>` - Unfollow a user
- `broadcast` - Manual profile broadcast
- `ping` - Send network ping
- `verbose` - Toggle debug output
- `ipstats` - Display IP statistics
- `quit` - Exit application

##### Error Handling and Reliability

- **Token Validation** - Ensures message authenticity and prevents replay attacks
- **Retry Mechanism** - Automatic retransmission for failed message delivery
- **Connection Monitoring** - Tracks failed connection attempts and suspicious activity
- **Graceful Degradation** - Continues operation despite individual peer failures

# File Transfer System

The LSNP file transfer system provides reliable peer-to-peer file sharing capabilities with chunked transmission, acknowledgment handling, and progress tracking. The system handles files of any size by breaking them into manageable chunks and reassembling them on the recipient side.

## Key Features for File Transfer

- **Chunked File Transmission** - Large files are automatically split into manageable chunks (1KB default)
- **Offer-Accept Model** - Recipients must explicitly accept file transfers before transmission begins
- **Progress Tracking** - Real-time monitoring of file transfer progress for both sender and receiver
- **Automatic Reassembly** - Received chunks are automatically reassembled into complete files
- **Token Validation** - All file transfer messages use cryptographic tokens for security
- **File Metadata** - Includes filename, size, type, and optional description
- **Error Recovery** - Handles missing chunks and network interruptions gracefully
- **Local Storage** - Downloaded files are saved in user-specific directories

## Core Classes

### FileTransfer

Manages individual file transfer sessions with complete state tracking.

#### Data Structure

```python
class FileTransfer:
    file_id: str              # Unique identifier for this transfer
    filename: str             # Original filename
    filesize: int             # Total file size in bytes
    filetype: str             # MIME type of the file
    total_chunks: int         # Number of chunks needed for complete file
    sender_id: str            # Full user ID of the sender
    description: str          # Optional file description
    chunks: Dict[int, bytes]  # Received chunk data indexed by chunk number
    received_chunks: int      # Count of successfully received chunks
    accepted: bool            # Whether recipient has accepted the transfer
    completed: bool           # Whether all chunks have been received
    timestamp: int            # Transfer initiation timestamp
```

#### Key Methods

1. > `__init__(file_id: str, filename: str, filesize: int, filetype: str, total_chunks: int, sender_id: str, description: str = "") -> None`
   >
   > Initializes a new file transfer session with metadata.
   >
   > **Parameters:**
   >
   > - `file_id` - Unique UUID for this transfer session
   > - `filename` - Name of the file being transferred
   > - `filesize` - Total size of the file in bytes
   > - `filetype` - MIME type (e.g., "text/plain", "image/jpeg")
   > - `total_chunks` - Number of chunks needed for complete transmission
   > - `sender_id` - Full user ID of the sender (format: "user@ip")
   > - `description` - Optional description of the file contents

2. > `add_chunk(chunk_index: int, data: bytes) -> bool`
   >
   > Adds a received chunk to the transfer session.
   >
   > **Parameters:**
   >
   > - `chunk_index` - Sequential index of the chunk (0-based)
   > - `data` - Raw bytes of the chunk data
   >
   > **Returns:** True if chunk was successfully added, False if transfer not accepted
   >
   > **Behavior:** Validates acceptance status, prevents duplicate chunks, tracks completion status

3. > `get_assembled_data() -> Optional[bytes]`
   >
   > Assembles all received chunks into complete file data.
   >
   > **Returns:** Complete file data as bytes, or None if transfer incomplete
   >
   > **Behavior:** Validates all chunks present, assembles in correct order, returns complete file

## File Transfer Protocol Messages

### FILE_OFFER Message

Initiates a file transfer by offering a file to a recipient.

**Format:**

```
TYPE: FILE_OFFER
FROM: sender_user_id@ip
TO: recipient_user_id@ip
FILENAME: example.txt
FILESIZE: 1024
FILETYPE: text/plain
FILEID: uuid-string
DESCRIPTION: Optional description
TIMESTAMP: unix_timestamp
TOKEN: cryptographic_token
```

### FILE_ACCEPT/FILE_REJECT Messages

Recipient's response to a file offer.

**Format:**

```
TYPE: FILE_ACCEPT  # or FILE_REJECT
FROM: recipient_user_id@ip
TO: sender_user_id@ip
FILEID: uuid-string
TOKEN: cryptographic_token
TIMESTAMP: unix_timestamp
```

### FILE_CHUNK Message

Contains individual file chunks during transmission.

**Format:**

```
TYPE: FILE_CHUNK
FROM: sender_user_id@ip
TO: recipient_user_id@ip
FILEID: uuid-string
CHUNK_INDEX: 0
TOTAL_CHUNKS: 10
CHUNK_SIZE: 1024
TOKEN: cryptographic_token
DATA: base64_encoded_chunk_data
```

### FILE_RECEIVED Message

Confirmation that file transfer has completed successfully.

**Format:**

```
TYPE: FILE_RECEIVED
FROM: recipient_user_id@ip
TO: sender_user_id@ip
FILEID: uuid-string
STATUS: COMPLETE
TIMESTAMP: unix_timestamp
```

## LSNPController File Transfer Methods

### Sending Files

1. > `send_file(recipient_id: str, file_path: str, description: str = "") -> None`
   >
   > Initiates file transfer to a specified peer.
   >
   > **Parameters:**
   >
   > - `recipient_id` - Target peer (accepts "user" or "user@ip" format)
   > - `file_path` - Path to file (absolute or relative to project root)
   > - `description` - Optional description of the file
   >
   > **File Path Resolution:**
   >
   > - Absolute paths used directly
   > - Relative paths first checked in `/files/` directory
   > - Falls back to project root if not found in `/files/`
   >
   > **Process Flow:**
   >
   > 1. Validates recipient exists in peer map
   > 2. Resolves and validates file path
   > 3. Generates unique file ID and metadata
   > 4. Sends FILE_OFFER message with file details
   > 5. Waits for recipient acceptance (60-second timeout)
   > 6. If accepted, transmits file in chunks with small delays
   > 7. Logs completion status and cleans up resources

2. > `_get_file_type(filename: str) -> str`
   >
   > Determines MIME type based on file extension.
   >
   > **Supported Types:**
   >
   > - `.txt` → `text/plain`
   > - `.jpg/.jpeg` → `image/jpeg`
   > - `.png` → `image/png`
   > - `.gif` → `image/gif`
   > - `.pdf` → `application/pdf`
   > - `.mp3` → `audio/mpeg`
   > - `.mp4` → `video/mp4`
   > - `.zip` → `application/zip`
   > - Default → `application/octet-stream`

### Receiving Files

1. > `accept_file(file_id: str) -> None`
   >
   > Accepts a pending file offer and begins receiving chunks.
   >
   > **Parameters:**
   >
   > - `file_id` - Unique identifier of the file offer to accept
   >
   > **Behavior:**
   >
   > - Validates file offer exists in pending offers
   > - Moves transfer from pending to active transfers
   > - Sends FILE_ACCEPT message to sender
   > - Prepares to receive file chunks

2. > `reject_file(file_id: str) -> None`
   >
   > Rejects a pending file offer.
   >
   > **Parameters:**
   >
   > - `file_id` - Unique identifier of the file offer to reject
   >
   > **Behavior:**
   >
   > - Validates file offer exists
   > - Sends FILE_REJECT message to sender
   > - Removes offer from pending list

3. > `list_pending_files() -> None`
   >
   > Displays all pending file offers awaiting user response.
   >
   > **Output:** Shows filename, size, sender, file ID, and description for each pending offer

4. > `list_active_transfers() -> None`
   >
   > Displays progress of ongoing file transfers.
   >
   > **Output:** Shows filename, sender, and chunk progress (received/total) for active transfers

### File Storage and Organization

#### Directory Structure

Files are automatically organized in user-specific directories:

```
project_root/
└── lsnp_data/
    └── user_id@ip_address/
        └── downloads/
            ├── received_file1.txt
            ├── received_file2.jpg
            └── ...
```

#### File Path Resolution for Sending

1. **Absolute Paths** - Used directly if file exists
2. **Files Directory** - Checks `project_root/files/filename` first
3. **Project Root** - Falls back to `project_root/filename`
4. **Error Handling** - Provides helpful hints about file placement

## Message Handling Implementation

### File Offer Processing

1. > `_handle_file_offer(kv: dict, addr: Tuple[str, int]) -> None`
   >
   > Processes incoming FILE_OFFER messages.
   >
   > **Validation Steps:**
   >
   > - Verifies message is addressed to this peer
   > - Validates cryptographic token
   > - Extracts file metadata (name, size, type, ID, description)
   >
   > **Behavior:**
   >
   > - Calculates required chunk count
   > - Creates FileTransfer object in pending offers
   > - Displays offer notification to user
   > - Waits for user acceptance/rejection

### Chunk Reception

2. > `_handle_file_chunk(kv: dict, addr: Tuple[str, int]) -> None`
   >
   > Processes incoming FILE_CHUNK messages during active transfers.
   >
   > **Validation:**
   >
   > - Verifies message addressing and token
   > - Confirms active transfer exists for file ID
   >
   > **Process:**
   >
   > - Decodes base64 chunk data
   > - Adds chunk to transfer object
   > - Updates progress tracking
   > - Triggers completion when all chunks received

### Transfer Completion

3. > `_complete_file_transfer(transfer: FileTransfer, sender_addr: Tuple[str, int]) -> None`
   >
   > Handles completion of file transfers and saves files to disk.
   >
   > **Process:**
   >
   > - Assembles all chunks into complete file data
   > - Creates user-specific download directory
   > - Saves file with original filename
   > - Sends FILE_RECEIVED confirmation
   > - Cleans up transfer resources
   > - Logs completion and file location

### Response Handling

4. > `_send_file_response(recipient_id: str, file_id: str, response_type: str) -> None`
   >
   > Sends FILE_ACCEPT or FILE_REJECT responses to file offers.
   >
   > **Security:** Generates fresh token for response message
   > **Reliability:** Includes error handling for network failures

## Configuration Constants

- `MAX_CHUNK_SIZE = 1024` - Maximum size of individual file chunks in bytes
- File transfer timeout: 60 seconds for recipient response
- Chunk transmission delay: 0.1 seconds between chunks to prevent network congestion

## Command Line Interface

### File Transfer Commands

- `sendfile <user> <filepath> [description]` - Initiate file transfer
- `acceptfile <fileid>` - Accept pending file offer
- `rejectfile <fileid>` - Reject pending file offer
- `pendingfiles` - List files awaiting acceptance
- `transfers` - Show active transfer progress

### Usage Examples

```bash
# Send a file from the files directory
sendfile alice document.pdf "Project report for review"

# Send with absolute path
sendfile bob /home/user/photo.jpg "Vacation photos"

# List pending offers and accept one
pendingfiles
acceptfile a1b2c3d4-e5f6-7890-abcd-ef1234567890

# Check transfer progress
transfers
```

## Error Handling and Recovery

### Network Resilience

- **Token Validation** - Prevents unauthorized file access and replay attacks
- **Chunk Verification** - Validates chunk integrity and prevents duplicates
- **Timeout Handling** - Graceful handling of unresponsive peers
- **Resource Cleanup** - Automatic cleanup of failed or completed transfers

### User Experience

- **Progress Feedback** - Real-time updates on transfer status
- **Clear Error Messages** - Helpful error reporting with suggestions
- **File Location Hints** - Guidance on where to place files for sending
- **Completion Notifications** - Clear indication of successful transfers

### Security Features

- **Cryptographic Tokens** - All file transfer messages include security tokens
- **User Consent** - Recipients must explicitly accept before receiving files
- **Path Validation** - Prevents directory traversal attacks
- **Size Limits** - Configurable limits on file and chunk sizes
