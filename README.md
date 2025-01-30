# System Monitoring and Control with Python Sockets

This project implements a system for monitoring and controlling endpoint agents from a central manager. It uses Python's `socket` library for TCP and UDP communication, along with libraries like `psutil` for system information and `json` for data serialization.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Code Explanation](#code-explanation)
    - [CentralManager.py](#centralmanagerpy)
    - [Client.py](#clientpy)
- [Running the Application](#running-the-application)
- [Contributing](#contributing)
- [License](#license)

## Overview

This system allows a central manager to collect system statistics (CPU usage, memory usage, running process count) and issue commands (like system restart) to multiple endpoint agents.  Communication is done over TCP for command and response, and UDP for asynchronous alerts (e.g., high CPU usage alerts).

## Features

* **Centralized Management:**  A single manager can monitor and control multiple agents.
* **System Statistics Collection:** Agents provide CPU and memory usage, and running process counts.
* **Command Execution:** The manager can send commands to agents, including system restart.
* **Asynchronous Alerts:** Agents send UDP alerts to the manager for critical events (e.g., high CPU usage).
* **Robust Connection Management:** Handles client disconnections and retries connections.
* **Threaded Architecture:** Uses threads for concurrent handling of multiple clients and background tasks.
* **Port Management:** Attempts to close existing processes using specified ports before binding.

## Architecture

The system consists of two main components:

* **CentralManager.py:** The central server that manages connections to agents, collects statistics, and issues commands.
* **Client.py:** The client program running on each machine to be monitored. It collects system information and executes commands from the manager.

The communication flow is as follows:

1.  Clients connect to the manager via TCP.
2.  The manager requests statistics from the clients via TCP.
3.  Clients respond with system information (CPU, memory, processes) via TCP.
4.  Clients send asynchronous alerts (e.g., high CPU) to the manager via UDP.

## Installation

1.  **Clone the repository:** (If you have a repository, replace with the actual URL)
    ```bash
    git clone <repository_url>
    cd system-monitoring
    ```

2.  **Install dependencies:**
    ```bash
    pip install psutil
    ```

## Usage

1.  **Start the CentralManager:**
    ```bash
    python CentralManager.py
    ```

2.  **Start the Clients:**
    ```bash
    python Client.py --mode client --manager_host <manager_ip_address>
    ```
    (Replace `<manager_ip_address>` with the IP address of the machine running the CentralManager.)  You can also run the client in server mode if you want to test it independently:
    ```bash
    python Client.py --mode server
    ```

## Code Explanation

### CentralManager.py

The `CentralManager` class handles:

*   TCP and UDP socket setup.
*   Client connection management (accepting new connections, removing disconnected clients).
*   Command distribution to clients.
*   Receiving and processing client responses (system stats).
*   Handling UDP alerts from clients.
*   Command interface for the user to interact with the system.

Key methods:

*   `start()`: Initializes and starts all threads (TCP listener, UDP listener, connection retry, command interface, connection monitor).
*   `handle_client()`: Handles communication with a single client (receiving commands, sending responses).
*   `handle_udp_messages()`: Handles incoming UDP alerts.
*   `command_interface()`: Provides a command-line interface for the user.
*   `monitor_connections()`: Periodically checks client connections and removes disconnected ones.

### Client.py

The `EndpointAgent` class handles:

*   Connecting to the CentralManager (TCP).
*   Sending system statistics to the manager.
*   Receiving and executing commands from the manager.
*   Sending UDP alerts for high CPU usage.
*   System monitoring.

Key methods:

*   `start()`: Starts the agent, either in server mode (waiting for a manager) or client mode (connecting to a manager).
*   `handle_connection()`: Handles communication with the manager.
*   `monitor_system()`: Monitors system resources (CPU) and sends UDP alerts.
*   `get_process_count()`: Gets the number of running processes.

## Running the Application

1.  Run the `CentralManager.py` script.
2.  Run the `Client.py` script in client mode, specifying the manager's IP address.
3.  Interact with the CentralManager through its command-line interface.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
