# LLM Server

This directory contains a FastAPI-based server that provides an interface to interact with local Large Language Models (LLMs) using the `llama-cpp-python` library.

## Overview

The server loads GGUF-format LLM files and exposes HTTP endpoints for:
- Listing available models.
- Setting the currently active model.
- Generating chat completions, supporting OpenAI-compatible API requests including tool use and streaming responses.
- Managing a prompt cache for faster subsequent requests with the same prefix.

## Features

- **Model Management**: Dynamically load and switch between different GGUF models located in the `models/` directory.
- **Chat Completion**: Provides an endpoint (`/chat/completions`) compatible with the OpenAI chat completion API format.
    - Supports multiple messages in the conversation history.
    - Supports passing available tools to the model.
    - Supports streaming responses (`text/event-stream`).
- **Prompt Caching**: Utilizes `llama-cpp-python`'s disk caching (`LlamaDiskCache`) to speed up processing for requests with repeated prompt structures. The cache is stored in the `cache/` directory.
- **Configuration**: Configurable host, port, default model, and logging level via command-line arguments.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    Ensure you have the necessary build tools for `llama-cpp-python` (like C++ compilers). Refer to the `llama-cpp-python` documentation for details.

2.  **Place Models**: Download your desired LLM models in GGUF format and place them inside the `models/` directory.

## Running the Server

You can run the server directly using Python:

```bash
python server.py [OPTIONS]
```

Available options:
- `--host`: Host to bind the server to (default: `127.0.0.1`).
- `--port`: Port to bind the server to (default: `8000`).
- `--model_name`: Default GGUF model file to load from the `models/` directory (default: `qwen2.5-3b-instruct-q4_k_m.gguf`).
- `--log-level`: Logging level (`debug`, `info`, `warning`, `error`) (default: `info`).

Alternatively, you can use `uvicorn`:

```bash
uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```
*(Note: Running with `uvicorn` directly won't process the command-line arguments defined in `server.py` for model loading etc. unless the logic is adapted)*

## API Endpoints

- **`GET /`**: Returns the server status.
- **`GET /models`**: Lists the GGUF model files found in the `models/` directory.
- **`POST /setModel`**: Sets the active LLM. Requires a JSON body like `{"modelName": "your_model.gguf"}`.
- **`POST /chat/completions`**: Generates chat completions. Accepts OpenAI-compatible request bodies. The `model` field in the request body can be used to specify or change the model for the request.
- **`POST /restore_cache`**: Pre-warms the model's cache based on a provided message history and tools.

## Dependencies

- `fastapi`: Web framework.
- `uvicorn`: ASGI server.
- `llama-cpp-python`: Python bindings for `llama.cpp`.
- `Jinja2`: Used for formatting prompts based on model templates. 