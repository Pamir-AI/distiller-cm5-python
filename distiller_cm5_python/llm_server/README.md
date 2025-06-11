# LLM Server

This directory contains a FastAPI-based server that provides an interface to interact with local Large Language Models (LLMs) using the `llama-cpp-python` library.

## Overview

The server loads GGUF-format LLM files and exposes HTTP endpoints for:
- Checking server health and status
- Listing available models from the models directory
- Dynamically loading and switching between models with custom configurations
- Generating chat completions with OpenAI-compatible API
- Supporting advanced features like tool calling, streaming responses, and inference parameter customization
- Automatic disk-based prompt caching for improved performance

## Features

### Model Management
- **Dynamic Loading**: Load and switch between different GGUF models from the `models/` directory
- **Custom Configuration**: Specify model parameters (e.g., `n_ctx`, context window size) during loading
- **Auto-Discovery**: Automatically detect available GGUF files in the models directory
- **Memory Management**: Efficient model loading and unloading

### Chat Completion API
- **OpenAI Compatibility**: Full compatibility with OpenAI's chat completions API format
- **Chat Templates**: Automatic template application based on model metadata using Jinja2
- **Conversation History**: Support for multi-turn conversations with message history
- **Tool Integration**: Native support for function/tool calling capabilities
- **Streaming Responses**: Real-time response streaming with `text/event-stream`
- **Parameter Customization**: Per-request inference parameters (temperature, top_p, max_tokens, etc.)

### Performance Optimization
- **Prompt Caching**: Automatic disk-based caching using `LlamaDiskCache` for faster repeated requests
- **Cache Pre-warming**: Endpoint to pre-populate cache with common prompt patterns
- **Efficient Processing**: Optimized request handling and response generation

### Configuration & Monitoring
- **Health Checks**: Comprehensive server and model status monitoring
- **Logging**: Configurable logging levels with structured output
- **Command-line Interface**: Full CLI support for server configuration

## Setup

### 1. Install Dependencies

Ensure you have the necessary dependencies installed:

```bash
# Navigate to the project root
cd /path/to/distiller-cm5-python

# Install using uv (recommended)
uv sync

# Or install specific dependencies
pip install fastapi uvicorn "llama-cpp-python[server]" jinja2 pydantic
```

**Note**: `llama-cpp-python` requires C++ build tools. Refer to the [llama-cpp-python documentation](https://github.com/abetlen/llama-cpp-python) for platform-specific installation instructions.

### 2. Prepare Models

Download your desired LLM models in GGUF format and place them in the `llm_server/models/` directory:

```bash
# Create models directory if it doesn't exist
mkdir -p distiller_cm5_python/llm_server/models/

# Place your GGUF models here
# Example: qwen2.5-3b-instruct-q4_k_m.gguf, llama-3.2-1b-instruct-q4_k_m.gguf, etc.
```

## Running the Server

### Method 1: Direct Python Execution (Recommended)

```bash
# Navigate to the project root
python -m distiller_cm5_python.llm_server.server [OPTIONS]
```

### Method 2: From Server Directory

```bash
# Navigate to the llm_server directory
cd distiller_cm5_python/llm_server/
python server.py [OPTIONS]
```

### Method 3: Using uvicorn (Development)

```bash
# Navigate to the project root
uvicorn distiller_cm5_python.llm_server.server:app --host 127.0.0.1 --port 8000 --reload
```

**Note**: Using uvicorn directly bypasses command-line arguments like `--model-name` and `--log-level`.

### Command-Line Options

- `--host`: Server host address (default: `127.0.0.1`)
- `--port`: Server port (default: `8000`)
- `--model-name`: Default GGUF model to load on startup (e.g., `qwen2.5-3b-instruct-q4_k_m.gguf`)
- `--log-level`: Logging verbosity (`debug`, `info`, `warning`, `error`) (default: `info`)

### Example Usage

```bash
# Start server with specific model and debug logging
python -m distiller_cm5_python.llm_server.server \
    --host 0.0.0.0 \
    --port 8001 \
    --model-name llama-3.2-1b-instruct-q4_k_m.gguf \
    --log-level debug
```

## API Reference

### Health & Status Endpoints

#### `GET /`
**Description**: Returns basic server status  
**Response**: `{"message": "LLM Server is running"}`

#### `GET /health`
**Description**: Comprehensive health check including model status  
**Response**: 
```json
{
  "status": "ok",
  "message": "Server is healthy and model is loaded",
  "model_loaded": true,
  "current_model": "qwen2.5-3b-instruct-q4_k_m.gguf"
}
```

### Model Management Endpoints

#### `GET /models`
**Description**: List all available GGUF models in the models directory  
**Response**:
```json
{
  "models": [
    "qwen2.5-3b-instruct-q4_k_m.gguf",
    "llama-3.2-1b-instruct-q4_k_m.gguf"
  ]
}
```

#### `POST /setModel`
**Description**: Load a specific model with optional configuration  
**Request Body**:
```json
{
  "model_name": "qwen2.5-3b-instruct-q4_k_m.gguf",
  "load_model_configs": {
    "n_ctx": 4096,
    "n_gpu_layers": -1,
    "verbose": false
  }
}
```
**Response**: `{"message": "Model loaded successfully", "model": "..."}`

### Chat Completion Endpoint

#### `POST /chat/completions`
**Description**: Generate chat completions with OpenAI-compatible API  

**Request Body Parameters**:
- `model` (optional): Model name for this request (triggers loading if different from current)
- `messages`: Array of message objects with `role` and `content`
- `tools` (optional): Array of available tools in OpenAI format
- `stream` (optional): Boolean for streaming responses (default: false)
- `inference_configs` (optional): Override inference parameters
- `load_model_configs` (optional): Model loading parameters if switching models

**Example Request**:
```json
{
  "model": "qwen2.5-3b-instruct-q4_k_m.gguf",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user", 
      "content": "What is the capital of France?"
    }
  ],
  "stream": false,
  "inference_configs": {
    "temperature": 0.7,
    "max_tokens": 1024,
    "top_p": 0.9
  }
}
```

**Response Format** (Non-streaming):
```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "qwen2.5-3b-instruct-q4_k_m.gguf",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "The capital of France is Paris."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 8,
    "total_tokens": 33
  }
}
```

### Cache Management

#### `POST /restore_cache`
**Description**: Pre-warm the model's prompt cache for faster subsequent requests  
**Request Body**:
```json
{
  "messages": [...],
  "tools": [...],
  "inference_configs": {...}
}
```

## Integration with Distiller Framework

The LLM server integrates seamlessly with the Distiller framework:

### Automatic Management
- **Main Script Integration**: `main.py` can automatically start/stop the server when using `llama-cpp` provider
- **Configuration Integration**: Server settings pulled from the multi-provider configuration system
- **Health Monitoring**: Client components can check server health before making requests

### Configuration
Configure the server through the framework's configuration system:

```json
{
  "llm_providers": {
    "llama-cpp": {
      "server_url": "http://127.0.0.1:8000",
      "model_name": "qwen2.5-3b-instruct-q4_k_m.gguf",
      "timeout": 150,
      "temperature": 0.7,
      "max_tokens": 4096
    }
  },
  "active_llm_provider": "llama-cpp"
}
```

## Performance Considerations

### Model Selection
- **Size vs Speed**: Smaller quantized models (Q4_K_M) offer good balance of quality and speed
- **Context Window**: Configure `n_ctx` based on your use case (longer contexts require more memory)
- **GPU Acceleration**: Set `n_gpu_layers: -1` to use all available GPU layers for faster inference

### Caching
- **Disk Cache**: Automatically stores processed prompts in `cache/` directory
- **Cache Warm-up**: Use `/restore_cache` endpoint to pre-populate common patterns
- **Cache Management**: Cache persists between server restarts for consistent performance

### Resource Usage
- **Memory**: Models require significant RAM/VRAM depending on size and quantization
- **CPU/GPU**: Configure GPU layers based on available hardware
- **Concurrent Requests**: Server handles requests sequentially by design

## Troubleshooting

### Common Issues

1. **Model Loading Failures**
   - Verify GGUF file is valid and not corrupted
   - Check available system memory
   - Ensure model file permissions are correct

2. **Slow Performance** 
   - Enable GPU acceleration with `n_gpu_layers`
   - Use smaller/more quantized models
   - Pre-warm cache for common requests

3. **Memory Issues**
   - Reduce `n_ctx` context window size
   - Use more aggressively quantized models (Q4_0, Q3_K_M)
   - Monitor system memory usage

4. **Connection Issues**
   - Verify server is running with `/health` endpoint
   - Check firewall settings if accessing remotely
   - Ensure correct host/port configuration

### Logging
Enable debug logging for detailed troubleshooting:
```bash
python -m distiller_cm5_python.llm_server.server --log-level debug
```

## Dependencies

- **`fastapi`**: Modern web framework for building APIs
- **`uvicorn`**: ASGI server for running FastAPI applications  
- **`llama-cpp-python`**: Python bindings for llama.cpp with GGUF support
- **`jinja2`**: Template engine for chat format processing
- **`pydantic`**: Data validation and serialization 