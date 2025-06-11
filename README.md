# Distiller CM5 Python Framework

This repository contains the Python implementation for the Distiller CM5 project, featuring a client-server architecture based on the Model Context Protocol (MCP) for interacting with Large Language Models (LLMs).

> **Note**: MCP (Model Context Protocol) integration is currently under active development. The current implementation provides direct LLM provider integration while MCP features are being developed and refined.

## Overview

The framework consists of several key components:

*   **Client (`distiller_cm5_python/client/`)**: Provides a command-line interface (CLI) to interact with LLM backends through various providers. Includes features like optional local LLM server management and streaming responses. MCP integration for advanced tool usage is under development. (See `client/README.md` for details)
*   **LLM Server (`distiller_cm5_python/llm_server/`)**: A FastAPI server that wraps local LLMs (using `llama-cpp-python`) and exposes an OpenAI-compatible API endpoint for chat completions, model management, and caching. (See `llm_server/README.md` for details)
*   **Utilities (`distiller_cm5_python/utils/`)**: Shared modules for configuration management (`config.py`), logging (`logger.py`), and custom exceptions (`distiller_exception.py`). Features a new multi-provider configuration system that supports multiple LLM backends. (See `utils/README.md` for details)
*   **SDK (`distiller_cm5_sdk`)**: An external, installable package containing reusable components like Whisper (ASR) and Piper (TTS) wrappers. See [Pamir-AI/distiller-cm5-sdk](https://github.com/Pamir-AI/distiller-cm5-sdk/tree/main) for details.

The primary user entry point is `main.py` in the project root.

## Installation and Setup

### Prerequisites

- Python 3.12 or higher
- `uv` package manager (recommended)

### 1. Install `uv` (Recommended Package Manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env # Or add uv to your PATH manually
```

### 2. Create and Activate Virtual Environment

```bash
# Navigate to the project root directory
cd /path/to/distiller-cm5-python
uv venv # Creates a .venv directory
source .venv/bin/activate # Or `.\.venv\Scripts\activate` on Windows
```

### 3. Install Dependencies

```bash
# Install project dependencies using uv
uv sync

# Or manually install if needed:
# uv pip install -e .
# uv pip install distiller-cm5-sdk   # External SDK package
```

*Note: Installing `llama-cpp-python` might require C++ build tools. Refer to its documentation.*
*Note: `distiller-cm5-sdk` might have its own dependencies (like `portaudio` for `PyAudio`) - refer to its [README](https://github.com/Pamir-AI/distiller-cm5-sdk/tree/main).*

### 4. Download LLM Models (for Local LLM Server)

Place your desired GGUF-format models into the `distiller_cm5_python/llm_server/models/` directory.

### 5. Configuration

The framework now uses a **multi-provider configuration system** that supports multiple LLM backends with an active provider selection.

#### Configuration Priority (highest to lowest):
1. Environment variables (e.g., `LLM_SERVER_URL`, `LLM_MODEL_NAME`)
2. User configuration file (`mcp_config.json` in project root)
3. Default configuration (`distiller_cm5_python/utils/default_config.json`)

#### Setup Configuration:

**Option A: Create User Configuration File**
```bash
# Copy default config and customize
cp distiller_cm5_python/utils/default_config.json mcp_config.json
# Edit mcp_config.json to customize settings
```

**Option B: Use Environment Variables**
```bash
export LLM_SERVER_URL="http://127.0.0.1:8000"
export LLM_MODEL_NAME="your_model.gguf"
export LOG_LEVEL="INFO"
```

#### Provider Configuration:

The system supports multiple LLM providers:

- **`llama-cpp`**: Local llama.cpp server (default)
- **`openrouter`**: OpenRouter API for access to various models
- Additional providers can be configured in the `llm_providers` section

The `active_llm_provider` setting determines which provider configuration is used.

## Running the Application

### 1. LLM Backend

Choose one of the following LLM backend options:

#### Option A: Local LLM Server (llama-cpp)

```bash
# Run the local LLM server
python -m distiller_cm5_python.llm_server.server --model-name your_model.gguf

# Or let main.py manage it automatically (if active_llm_provider is "llama-cpp")
```

#### Option B: OpenRouter API

Set up OpenRouter configuration:
```bash
# In mcp_config.json, set:
# "active_llm_provider": "openrouter"

# Set API key:
export LLM_API_KEY="sk-or-v1-your-api-key"
```

### 2. Client (CLI)

The main entry point handles launching the client and automatically manages the LLM backend if needed.

#### CLI Client:
```bash
python main.py
```
- Text-based interactive chat
- Streaming response support
- Tool integration (under development)

### 3. Additional Options

```bash
# View all available options
python main.py --help

# Run with specific server script for MCP tools (under development)
python main.py --server-script /path/to/mcp_server_script.py

# Custom configuration file
export MCP_CONFIG_FILE="/path/to/custom_config.json"
python main.py
```

## Configuration Reference

### Key Configuration Settings

- **`active_llm_provider`**: Which LLM provider to use ("llama-cpp", "openrouter", etc.)
- **Provider-specific settings** under `llm_providers.{provider_name}`:
  - `server_url`: API endpoint URL
  - `model_name`: Model identifier
  - `api_key`: Authentication key (if required)
  - `timeout`: Request timeout in seconds
  - `temperature`, `top_p`, `top_k`: Generation parameters
  - `max_tokens`: Maximum tokens to generate
  - `streaming`: Enable streaming responses

### Environment Variable Overrides

Environment variables override the active provider's settings:
- `LLM_SERVER_URL`: Override server URL
- `LLM_MODEL_NAME`: Override model name
- `LLM_API_KEY`: Override API key
- `LLM_TEMPERATURE`: Override temperature
- `LOG_LEVEL`: Override logging level
- `MCP_CONFIG_FILE`: Custom config file path

## Project Structure

```
distiller-cm5-python/
├── main.py                          # Main entry point
├── pyproject.toml                   # Project configuration
├── uv.lock                         # Dependency lock file
├── mcp_config.json                 # User configuration (create from default)
└── distiller_cm5_python/
    ├── client/                     # Client interface (CLI)
    │   ├── cli.py                 # Command-line interface
    │   ├── mid_layer/             # Core client logic
    │   └── llm_infra/             # LLM infrastructure management
    ├── llm_server/                # Local LLM server
    │   ├── server.py              # FastAPI server
    │   ├── models/                # GGUF model files
    │   └── cache/                 # Prompt cache storage
    └── utils/                     # Shared utilities
        ├── config.py              # Multi-provider configuration
        ├── logger.py              # Logging setup
        ├── default_config.json    # Default configuration
        └── distiller_exception.py # Custom exceptions
```

## Development

The project uses modern Python tooling:
- **uv**: Fast package manager and virtual environment
- **Ruff**: Code formatting and linting
- **pyproject.toml**: Modern Python project configuration

For development, ensure you have Python 3.12+ and follow the installation steps above.

