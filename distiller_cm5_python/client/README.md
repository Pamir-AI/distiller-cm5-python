# MCP Client

This directory contains the client-side application for interacting with an MCP (Multi-modal Conversation Protocol) server.

## Overview

The client application provides a command-line interface (CLI) to interact with an LLM backend, optionally managed via an MCP server process. It supports features like configuration management, optional local LLM server management (for llama.cpp), tool usage facilitated by the MCP server, streaming responses, and conversation history.

The primary entry point is `main.py` in the project root, which handles initial setup (like starting a local `llama.cpp` server if configured) and then delegates execution to `client/cli.py`.

## Execution Flow (`main.py` -> `client/cli.py`)

1.  **Entry Point (`main.py`):**
    *   Located in the project root, not within this `client` directory.
    *   Reads initial configuration (`utils/config.py`).
    *   **Optional Llama.cpp Management:** If `PROVIDER_TYPE` is `llama-cpp`, it checks if a local server is running (`client/llm_infra/llama_manager.py`). If not, it attempts to start one.
    *   Delegates core CLI logic to `client.cli.main()`.
    *   Handles final cleanup, including stopping the managed `llama.cpp` server if it was started.

2.  **Command-Line Interface (`client/cli.py`):**
    *   Parses command-line arguments (e.g., `--stream`, `--llm-url`, `--server-script`), potentially overriding configuration defaults.
    *   Instantiates the core `MCPClient` (`client/mid_layer/mcp_client.py`) with the specified configuration.
    *   Connects the `MCPClient` to the separate MCP server process (specified by `--server-script`).
    *   Initiates the interactive `chat_loop`, handling user input and displaying assistant responses.
    *   Manages client-side errors and cleanup.

3.  **Mid-Layer Interaction (`client/mid_layer/`):**
    *   The `chat_loop` in `cli.py` calls `MCPClient.process_query()`.
    *   `MCPClient` coordinates communication with the MCP server process.
    *   The MCP server process (running separately) uses its own components (including an `LLMClient` instance within the server, configured via the client's initial connection) to interact with the actual LLM backend.
    *   Results (potentially including tool calls) are streamed back through the MCP server to the `MCPClient` and then to the `cli.py` for display.

## Key Components

*   **`cli.py`**:
    *   Provides the user-facing command-line interface using `argparse`.
    *   Handles argument parsing, initializes `MCPClient`, manages the connection to the MCP server process, and runs the interactive chat loop.
*   **`mid_layer/`**: Contains the core client logic for interacting with the MCP server.
    *   **`mcp_client.py`**: Defines the `MCPClient` class. Orchestrates the connection to the *MCP server process*, sends user queries, receives results, and manages the overall client state. It does **not** directly talk to the LLM but relies on the connected MCP server.
    *   **`llm_client.py`**: Defines `LLMClient` (or similar base class). *Instances of this are primarily used within the separate MCP server process* to communicate directly with the configured LLM backend (e.g., llama.cpp HTTP server, OpenAI API). The client-side `MCPClient` configures how the *server* should use its `LLMClient`.
    *   **`processors.py`**: Defines processors (e.g., `MessageProcessor`, `ToolProcessor`) used *within the MCP server process* to manage conversation history, tool definitions/execution, and prompts based on communication from the `MCPClient`.
*   **`llm_infra/`**: Utilities specifically for managing local LLM infrastructure.
    *   **`llama_manager.py`**: (Used by `main.py`) Contains `LlamaCppServerManager` to check status, start, and stop a local `llama-cpp` server process if configured.
    *   **`parsing_utils.py`**: Helper functions potentially used by `llama_manager.py`.

## Functionality Provided by the Client Application

*   **CLI:** Interactive chat via `cli.py`.
*   **Configuration:** Manage LLM provider details, server paths, streaming via args and `utils/config.py`.
*   **Local Server Management:** Optionally start/stop a local `llama.cpp` server via `main.py` and `LlamaCppServerManager`.
*   **Connection:** `MCPClient` connects to a *separate MCP server process* using the path provided.
*   **Query Processing:** `cli.py` takes input, `MCPClient` sends it to the MCP server, which handles LLM interaction and tool calls before returning the response.
*   **Streaming Support:** Handles streaming responses received *from the MCP server*.

## Usage

The client application is typically run via the main entry point:

```bash
python main.py [OPTIONS]
```

Refer to `python main.py --help` or `client/cli.py` for available command-line options (`--stream`, `--llm-url`, `--provider`, `--model`, `--server-script`, etc.) which configure how the client and the connected MCP server behave. 