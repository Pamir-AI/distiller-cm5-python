# MCP Client

This directory contains the client-side components responsible for interacting with an MCP server. The client can be launched via the main project entry point (`main.py` in the project root), which supports both a Graphical User Interface (GUI) and a Command-Line Interface (CLI).

## Quick Start

All dependencies are managed through `pyproject.toml`. Install and run using **uv**:

```bash
# From project root
cd distiller-cm5-python

# Install dependencies
uv sync

# Run GUI mode
uv run python main.py --gui

# Run CLI mode  
uv run python main.py
```

Refer to the main project `README.md` for complete installation instructions.

## Interfaces

The client offers two primary ways to interact with the MCP server:

1.  **Graphical User Interface (`ui/`)**
    *   Provides a rich, visual interface built with PyQt6 and QML.
    *   The main application logic resides in `App.py`, which initializes the Qt application, loads the QML interface defined in `main.qml`, and manages various components.
    *   Features include:
        *   Visual chat display.
        *   Integration with `Whisper` for voice input (STT).
        *   Support for E-Ink displays via `EInkRenderer` and `EInkRendererBridge`.
        *   Potential hardware button interaction using `evdev` (if available).
    *   The UI communicates with the MCP server through the `mid_layer` via the `ui/bridge/MCPClientBridge.py`.

2.  **Command-Line Interface (`cli.py`)**
    *   Provides a text-based, interactive chat loop for environments where a GUI is not needed or desired.
    *   Handles command-line argument parsing specific to the client (though initial parsing and GUI/CLI selection happens in the root `main.py`).
    *   Directly utilizes the `mid_layer/mcp_client.py` to connect and communicate with the MCP server.

## Key Components

*   **`ui/`**: Contains all code related to the Qt/QML Graphical User Interface.
    *   `App.py`: Core application class managing the UI lifecycle, event loop, and integration of other components (Whisper, E-Ink, Bridge).
    *   `main.qml`: Defines the structure and appearance of the user interface.
    *   `bridge/MCPClientBridge.py`: Acts as an intermediary, exposing the functionality of the `mid_layer`'s `MCPClient` to the QML frontend in a Qt-friendly way.
    *   `bridge/EInkRenderer.py` & `bridge/EInkRendererBridge.py`: Handle screen capture and rendering to E-Ink displays (if configured).
    *   Other subdirectories contain QML components, images, fonts, utility functions, etc.
*   **`cli.py`**: Implements the command-line interface, parsing arguments and running the interactive chat session.
*   **`mid_layer/`**: Contains the core client logic for interacting with the MCP server, shared by both the UI and CLI.
    *   `mcp_client.py`: Defines the `MCPClient` class. This is the central component orchestrating the connection to the *MCP server process*, sending user queries, receiving results (including streaming and tool calls), and managing the client-side communication state.
    *   `llm_client.py`: Defines the `LLMClient` base class and its implementations (e.g., for OpenAI, Llama.cpp). *Instances of these are primarily used within the separate MCP server process*, configured by the client via the `MCPClient`.
    *   `processors.py`: Defines processors (e.g., `MessageProcessor`, `ToolProcessor`) used *within the MCP server process* to manage conversation history, tool execution, and prompt formatting based on instructions from the `MCPClient`.
*   **`llm_infra/`**: Utilities specifically for managing local LLM infrastructure.
    *   `llama_manager.py`: Contains `LlamaCppServerManager` to check status, start, and stop a local `llama-cpp` server process. This is primarily invoked by the root `main.py` during startup/shutdown, not during active client operation.
    *   `parsing_utils.py`: Helper functions, potentially used by `llama_manager.py`.

## Functionality Provided by the Client Module

*   **User Interfaces:** Offers both a GUI (`ui/`) and a CLI (`cli.py`).
*   **MCP Communication:** Connects to and interacts with the MCP server process via `mid_layer/mcp_client.py`.
*   **UI Features:** Visual chat, voice input processing (via Whisper), E-Ink display rendering, hardware button handling (optional).
*   **Configuration Handling:** While core configuration is loaded via `utils/config.py` (project root), client-specific arguments modify behavior.
*   **Streaming Support:** Handles streaming responses received *from the MCP server* for display in either the UI or CLI.

## Usage

To run the client (either GUI or CLI), use **uv** with the main entry point:

```bash
# Navigate to the project root directory first
cd distiller-cm5-python

# Install dependencies first (if not done already)
uv sync

# To run the GUI
uv run python main.py --gui [OTHER_OPTIONS]

# To run the CLI
uv run python main.py [OPTIONS_WITHOUT_--gui]

# Get help
uv run python main.py --help
```

All dependencies are automatically managed through `pyproject.toml` when using **uv**. 