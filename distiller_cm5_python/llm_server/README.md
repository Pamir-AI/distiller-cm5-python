# LLM Server

This directory contains a FastAPI-based server that provides an interface to interact with local Large Language Models (LLMs) using the `llama-cpp-python` library.

## Overview

The server loads GGUF-format LLM files and exposes HTTP endpoints for:
- Checking server health.
- Listing available models.
- Setting the currently active model, including specific loading configurations.
- Generating chat completions, supporting OpenAI-compatible API requests including tool use, inference parameter customization, and streaming responses.
- Utilizing automatic disk-based prompt caching and providing an endpoint to pre-warm the cache.

## Features

- **Model Management**: Dynamically load and switch between different GGUF models located in the `models/` directory. Allows specifying model configuration (e.g., `n_ctx`) during loading via the API.
- **Chat Completion**: Provides an endpoint (`/chat/completions`) compatible with the OpenAI chat completion API format.
    - Applies the appropriate chat template based on model metadata using Jinja2.
    - Supports multiple messages in the conversation history.
    *   Supports passing available tools (`tools`) to the model.
    *   Supports customizing inference parameters per request (`inference_configs`) like `temperature`, `max_tokens`, `top_k`, `top_p`, `repeat_penalty`, `stop`.
    *   Supports specifying model load configurations (`load_model_configs`) per request if switching models.
    - Supports streaming responses (`text/event-stream`).
- **Prompt Caching**: Automatically utilizes `llama-cpp-python`'s disk caching (`LlamaDiskCache`) to speed up processing for requests with repeated prompt structures. The cache is stored in the `cache/` directory. An endpoint is provided to pre-warm this cache.
- **Configuration**: Configurable host, port, default model, and logging level via command-line arguments when run directly.

## Setup

1.  **Install Dependencies using uv**:
    ```bash
    # Navigate to the project root first
    cd distiller-cm5-python
    
    # Install all dependencies from pyproject.toml
    uv sync
    ```
    All required dependencies including FastAPI, uvicorn, llama-cpp-python, Jinja2, and pydantic are automatically managed through `pyproject.toml`. Ensure you have the necessary build tools for `llama-cpp-python` (like C++ compilers). Refer to the `llama-cpp-python` documentation for details.

2.  **Place Models**: Download your desired LLM models in GGUF format and place them inside the `llm_server/models/` directory relative to the project root.

## Running the Server

The recommended way to run the server is using **uv**, which handles all dependencies automatically:

```bash
# Navigate to the project root directory
cd distiller-cm5-python

# Run with uv
uv run python -m distiller_cm5_python.llm_server.server [OPTIONS]
```
Or if running from within the `llm_server` directory:
```bash
uv run python server.py [OPTIONS]
```

Available options:
- `--host`: Host to bind the server to (default: `127.0.0.1`).
- `--port`: Port to bind the server to (default: `8000`).
- `--model-name`: Default GGUF model file to load from the `models/` directory (e.g., `qwen2.5-3b-instruct-q4_k_m.gguf`). Defaults might be specified in the script.
- `--log-level`: Logging level (`debug`, `info`, `warning`, `error`) (default: `info`).

Alternatively, you can use `uvicorn` with **uv** for development (note: this bypasses the `--model-name` and `--log-level` arguments from `server.py`):

```bash
# Navigate to the project root directory
cd distiller-cm5-python

# Run uvicorn with uv
uv run uvicorn distiller_cm5_python.llm_server.server:app --host 127.0.0.1 --port 8000 --reload
```

## API Endpoints

- **`GET /`**: Returns the server status.
- **`GET /health`**: Checks if the server is running and the LLM model is loaded. Returns `{"status": "ok", "message": "..."}` on success.
- **`GET /models`**: Lists the GGUF model files found in the `models/` directory. Returns `{"models": ["model1.gguf", ...]}`.
- **`POST /setModel`**: Sets the active LLM. Requires a JSON body like `{"model_name": "your_model.gguf", "load_model_configs": {"n_ctx": 4096}}`.
- **`POST /chat/completions`**: Generates chat completions. Accepts OpenAI-compatible request bodies.
    - `model` (optional): Specify a model name from the `models/` directory for this request. If different from the current model, it will be loaded using `load_model_configs`.
    - `messages`: List of message objects (`role`, `content`).
    - `tools` (optional): List of available tools in OpenAI format.
    - `stream` (optional): Boolean, set to `true` for streaming response.
    - `inference_configs` (optional): Dictionary with inference parameters (`temperature`, `max_tokens`, `top_k`, `top_p`, `repeat_penalty`, `stop`).
    - `load_model_configs` (optional): Dictionary with model loading parameters (`n_ctx`, etc.) used if the `model` field specifies a model different from the currently loaded one.
- **`POST /restore_cache`**: Pre-warms the model's prompt cache based on a provided message history and tools, potentially speeding up subsequent related requests. Accepts `messages`, `tools`, and optional `inference_configs`.

## Dependencies

- `fastapi`: Web framework.
- `uvicorn`: ASGI server.
- `llama-cpp-python`: Python bindings for `llama.cpp`.
- `Jinja2`: Used for formatting prompts based on model chat templates.
- `pydantic`: Data validation (used by FastAPI). 

to update llama-cpp-python under uv env, try : 
```bash
uv pip install llama-cpp-python==0.3.14

# or if show no version match try
uv pip install llama-cpp-python==0.3.14 --index-strategy unsafe-best-match
```
