# MCP Server Implementations

This directory contains various example implementations of servers adhering to the Model Context Protocol (MCP). Each server typically exposes a specific set of tools or resources related to a particular domain or device.

These servers are designed to be launched independently and communicated with by an MCP client (like the one in the `../client` directory), often via standard input/output (stdio).

## Dependencies Management

All dependencies are managed through the project's `pyproject.toml` using **uv**:

```bash
# Navigate to project root first
cd distiller-cm5-python

# Install all dependencies
uv sync
```


## Included Example Servers

- **`led-control_server.py`**: An MCP server for controlling RGB LED on the Distiller CM5 device. Provides tools for setting colors, blinking patterns, and clearing the LED.
- **`medical_assistant_server.py`**: A FastMCP server that provides system prompts for medical assistants. Includes prompts for clinical documentation, patient education, medical research, and diagnostic support.
- **`talk_server.py`**: An MCP server offering a tool (`speak_text`) to perform Text-to-Speech using the `piper` library. Allows the assistant to speak provided text aloud.
- **`wifi_server.py`**: An MCP server for interacting with WiFi networks on **Linux systems** using `nmcli`. Provides tools for listing networks, checking status, connecting to a network, and showing SSH instructions. *Note: Requires `nmcli` and appropriate permissions (e.g., `sudo`) for some operations.*

## Usage

Each server script can be run using **uv** which handles all dependencies automatically:

```bash
# Navigate to project root first
cd distiller-cm5-python

# Example for LED control server
uv run python distiller_cm5_python/mcp_server/Badge_AI_server.py

# Example for medical assistant server
uv run python distiller_cm5_python/mcp_server/medical_assistant_server.py

```

An MCP client (like the one started via `main.py --server-script /path/to/server.py`) can then connect to the launched server process using the stdio transport mechanism provided by the `mcp` library.

### Medical Assistant Server

The medical assistant server provides system prompts for different medical assistant scenarios:

**Prompts:**
- `general_medical_assistant`: General medical assistant system prompt
- `clinical_documentation_general`: System prompt for general clinical documentation
- `clinical_documentation_cardiology`: System prompt for cardiology clinical documentation
- `clinical_documentation_emergency`: System prompt for emergency clinical documentation
- `patient_education_general`: System prompt for general patient education
- `patient_education_diabetes`: System prompt for diabetes patient education
- `patient_education_hypertension`: System prompt for hypertension patient education
- `medical_research_general`: System prompt for general medical research
- `diagnostic_support_general`: System prompt for general diagnostic support
- `medication_guidance_general`: System prompt for general medication guidance

Each prompt provides a comprehensive system prompt that can be used to configure AI assistants for specific medical use cases. The prompts are parameter-less to ensure compatibility with different MCP client implementations.


## Dependencies

All dependencies are automatically managed through `pyproject.toml` and installed with **uv**:

- `mcp`: Core MCP library for protocol implementation
- `fastmcp`: Enhanced MCP server framework (for `medical_assistant_server.py`) 
- `distiller_cm5_sdk`: Hardware control SDK (`piper` for TTS, LED control)
- `nest_asyncio`: Async event loop utilities
- Plus additional dependencies as specified in the project's `pyproject.toml`

### System Requirements
- `nmcli`: Required for `wifi_server.py` on Linux systems  
- Appropriate permissions (e.g., `sudo`) for network operations

To add or modify dependencies, edit the project's `pyproject.toml` and run `uv sync`.
