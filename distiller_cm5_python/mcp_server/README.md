# MCP Server Implementations

This directory contains various example implementations of servers adhering to the Multi-modal Conversation Protocol (MCP). Each server typically exposes a specific set of tools or resources related to a particular domain or device.

These servers are designed to be launched independently and communicated with by an MCP client (like the one in the `../client` directory), often via standard input/output (stdio).

## Included Servers

- **`speaker_server.py`**: An MCP server offering tools to manage a speaker (e.g., set volume, play/pause).
- **`wifi_server.py`**: An MCP server for interacting with WiFi networks (e.g., list networks, connect/disconnect). *Note: Functionality might vary based on the OS.*
- **`wifi_mac_server.py`**: A variant of the WiFi server, potentially tailored for macOS specific commands or behaviors.

## Usage

Each server script can typically be run directly using Python:

```bash
python <server_script_name>.py
```

An MCP client can then connect to the launched server process using the stdio transport mechanism provided by the `mcp` library.

## Dependencies

- `mcp` library (likely installed from the parent project or a central location).
- Specific system utilities or libraries depending on the server's functionality (e.g., network utilities for WiFi servers). 