#!/usr/bin/env python3
"""
LLM Server - Provides LLM services over HTTP
"""
import argparse
import logging
import json
import os
import sys
import hashlib
import asyncio
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn
from llama_cpp import Llama

from llama_cpp.llama_cache import LlamaDiskCache
from jinja2 import Template
import re

# Import the centralized logging setup
from distiller_cm5_python.utils.logger import setup_logging

# --- Logging setup will be done in main() after parsing args ---

# Get the logger for this module
# We get the logger instance here, but configuration (level, stream) happens in main()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="LLM Server", description="A simple LLM server that provides LLM services"
)

# At the top, add cache management
MODEL_NAME = None
MODEL = None
CURRENT_CACHE = None  # Track current cache to invalidate when model changes
CURRENT_INFERENCE_CONFIGS = None  # Track current inference configurations

# Define request and response models
class Message(BaseModel):
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None


class SetModel(BaseModel):
    model_name: str
    load_model_configs: Dict[str, Any] = dict()
    inference_configs: Optional[Dict[str, Any]] = None


class ToolParameter(BaseModel):
    type: str
    description: Optional[str] = None


class ToolFunction(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class Tool(BaseModel):
    type: str = "function"
    function: ToolFunction


class ChatCompletionRequest(BaseModel):
    messages: List[Message]
    tools: Optional[List[Tool]] = None
    model: Optional[str] = None
    stream: Optional[bool] = False
    inference_configs: Optional[Dict[str, Any]] = dict()
    load_model_configs: Optional[Dict[str, Any]] = dict()


class CompletionRequest(BaseModel):
    prompt: str


class ToolCallFunction(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: ToolCallFunction


class CompletionResponse(BaseModel):
    response: str
    tool_calls: List[ToolCall] = Field(default_factory=list)


class RestoreCacheRequest(BaseModel):
    messages: List[Message]
    tools: List[Tool]
    inference_configs: Optional[Dict[str, Any]] = dict()


class Cache:
    def __init__(self, model: Llama):
        self.model = model
        self.cache_context = None

    def get_cache_key(self, prompt: str, seed: Optional[int] = None, temperature: float = 0.0):
        """Generate cache key including seed and temperature for consistency"""
        # Include seed and temperature in the cache key to ensure consistency
        cache_data = {
            "prompt_tokens": self.model.tokenize(prompt.encode("utf-8")),
            "seed": seed,
            "temperature": temperature
        }
        # Create a hashable key from the cache data
        key_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    @staticmethod
    def build_cache(
        cache_dir: str,
        prompts: str,
        model: Llama,
        model_name: str,
        temperature: float = 0.0,
        capacity_bytes: int = 2 << 30,
        seed: Optional[int] = None,
    ):
        cache = Cache(model)
        
        # Always set seed for consistency, use default if not provided
        effective_seed = seed if seed is not None else 12345  # Default consistent seed
        model.set_seed(effective_seed)
        
        # Create a model-specific cache directory
        model_specific_cache_dir = os.path.join(cache_dir, model_name)
        os.makedirs(model_specific_cache_dir, exist_ok=True) # Ensure the directory exists

        cache_context = LlamaDiskCache(cache_dir=model_specific_cache_dir)
        model.set_cache(cache_context)
        
        # Use improved cache key that includes seed and temperature
        cache_key = cache.get_cache_key(prompts, effective_seed, temperature)

        try:
            cached_state = cache_context[cache_key]
            logger.debug("Cache hit successful")
            return cached_state
        except KeyError:
            logger.debug("Cache miss - key not found, building new cache")
        except Exception as e:
            logger.warning(f"Cache error (not just missing): {e}")
            # Fall through to rebuild cache
            
        # Build new cache
        model.reset()
        _ = model(
            prompts,
            max_tokens=1,  # Minimal tokens for cache creation
            temperature=temperature,
            echo=False,
        )
        # Save the state to cache with the new key
        cache_state = model.save_state()
        cache_context[cache_key] = cache_state
        return cache_state


def is_cache_valid_for_request(messages, tools, inference_configs):
    """Check if current cache is still valid for the request"""
    global CURRENT_CACHE, MODEL_NAME
    
    if CURRENT_CACHE is None:
        return False
        
    try:
        # Check if the same prompt would be generated
        formatted_messages = format_messages(messages)
        formatted_tools = format_tools(tools) if tools else []
        current_prompt = format_prompt(formatted_messages, formatted_tools)
        
        # Check if cache key would match
        cache = Cache(MODEL)
        seed = inference_configs.get("seed", 12345)
        temperature = inference_configs.get("temperature", 0.0)
        current_cache_key = cache.get_cache_key(current_prompt, seed, temperature)
        
        # This is a simplified check - in a full implementation you might want to 
        # store the cache key that was used when CURRENT_CACHE was set
        logger.debug(f"Cache validation - current key: {current_cache_key}")
        return True  # For now, assume valid if cache exists
        
    except Exception as e:
        logger.warning(f"Cache validation failed: {e}")
        return False


@app.get("/")
async def root():
    return {"status": "ok", "message": "LLM Server is running"}


@app.get("/health")
async def health_check():
    if MODEL is None:
        raise HTTPException(status_code=503, detail="LLM model not loaded")
    try:
        # Verify model is functioning properly
        if MODEL_NAME is None:
            return {
                "status": "warning",
                "message": "LLM model loaded but no model name set",
            }
        return {
            "status": "ok",
            "message": f"LLM Server is healthy, using model: {MODEL_NAME}",
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@app.get("/models")
async def list_models():
    try:
        path = os.path.join(os.path.dirname(__file__), "models")
        model_names = [
            f
            for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f)) and f.endswith(".gguf")
        ]
        return {"models": [m for m in model_names]}
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing models: {str(e)}")


@app.get("/getCurrentModel")
async def get_current_model():
    """Get the currently loaded model and its configuration."""
    if MODEL_NAME is None:
        return {
            "status": "no_model",
            "model": None,
            "message": "No model currently loaded"
        }
    return {
        "status": "ok",
        "model": MODEL_NAME,
        "provider": "llama-cpp",
        "context_length": MODEL.n_ctx() if MODEL else None,
        "inference_configs": CURRENT_INFERENCE_CONFIGS
    }


@app.post("/setModel")
async def set_model(request: SetModel):
    global CURRENT_INFERENCE_CONFIGS
    try:
        load_model(request.model_name, request.load_model_configs)
        # Store inference configs if provided
        if request.inference_configs:
            CURRENT_INFERENCE_CONFIGS = request.inference_configs
            logger.info(f"Updated inference configs: {CURRENT_INFERENCE_CONFIGS}")
        return {"status": "ok", "message": "model is change to " + request.model_name}
    except Exception as e:
        logger.error(f"Error setting model: {e}")
        raise HTTPException(status_code=500, detail=f"Error set models: {str(e)}")


def load_model(model_name, load_model_configs: dict[str, Any]):
    global MODEL
    global MODEL_NAME
    global CURRENT_CACHE
    
    model_path = os.path.join(os.path.dirname(__file__), "models", model_name)
    if not os.path.exists(model_path):
        raise ValueError(f"Model '{model_name}' not found in models directory")

    # If we're changing models, invalidate current cache
    if MODEL_NAME != model_name:
        logger.info(f"Model changing from {MODEL_NAME} to {model_name}, invalidating cache")
        CURRENT_CACHE = None

    MODEL = Llama(
        model_path=str(model_path),
        verbose=True,
        n_gpu_layers=0,
        n_ctx=load_model_configs["n_ctx"],
    )

    MODEL_NAME = model_name
    logger.info(f"Loaded model: {model_name}")
    return True


def _chat_completion(messages, tools, inference_configs):
    """Non-streaming version"""
    logger.debug("Generating non-streaming chat completion...")
    
    # Set consistent seed for reproducible results
    seed = inference_configs.get("seed", 12345)  # Use consistent default seed
    MODEL.set_seed(seed)
    
    response = MODEL.create_chat_completion(
        messages=messages,
        tools=tools,
        temperature=inference_configs["temperature"],
        max_tokens=inference_configs["max_tokens"],
        top_k=inference_configs["top_k"],
        top_p=inference_configs["top_p"],
        min_p=inference_configs["min_p"],
        repeat_penalty=inference_configs["repetition_penalty"],
        stop=inference_configs["stop"],
        stream=False,
    )
    return response


def _stream_chat_completion(messages, tools, inference_configs):
    """Streaming version"""
    logger.debug("Generating streaming chat completion...")
    
    # Set consistent seed for reproducible results
    seed = inference_configs.get("seed", 12345)  # Use consistent default seed
    MODEL.set_seed(seed)
    
    try:
        response_stream = MODEL.create_chat_completion(
            messages=messages,
            tools=tools,
            temperature=inference_configs["temperature"],
            max_tokens=inference_configs["max_tokens"],
            top_k=inference_configs["top_k"],
            top_p=inference_configs["top_p"],
            min_p=inference_configs["min_p"],
            repeat_penalty=inference_configs["repetition_penalty"],
            stop=inference_configs["stop"],
            stream=True,
        )

        chunk_count = 0
        for chunk in response_stream:
            chunk_count += 1
            # Convert dictionary to JSON string before yielding
            yield f"data: {json.dumps(chunk)}\n\n"
        logger.debug(f"Streaming finished after {chunk_count} chunks.")
        
        # Send proper SSE termination
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Error during streaming: {e}")
        # Send error chunk before closing
        error_chunk = {
            "error": {
                "type": "server_error",
                "message": str(e)
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"


async def _async_stream_wrapper(messages, tools, inference_configs):
    """Async wrapper for streaming to ensure proper connection handling"""
    loop = asyncio.get_event_loop()
    
    # Run the sync generator in a thread to avoid blocking
    async def generate():
        for chunk in _stream_chat_completion(messages, tools, inference_configs):
            yield chunk
            # Small delay to allow proper flushing
            await asyncio.sleep(0)
    
    async for chunk in generate():
        yield chunk


def format_prompt(messages, tools):
    # Actual input received by the model
    model_template = MODEL.metadata.get("tokenizer.chat_template")
    template = Template(model_template)
    logger.debug(
        f"format_prompt called with {len(messages)} messages and {len(tools) if tools else 0} tools."
    )
    rendered_prompt = template.render(messages=messages, tools=tools)
    # logger.debug(f"MODEL.chat_handler: {MODEL.chat_handler}")
    # rendered_prompt = MODEL.chat_handler(llama=MODEL, messages=messages, tools=tools)
    # rendered_prompt = FORMATTER(messages=messages, tools=tools).prompt
    # logger.debug(
    #     "Actual prompt into llm:\n"
    #     + rendered_prompt
    # )
    return rendered_prompt


def format_messages(messages):
    # if tool_call is None, remove it
    formatted_messages = []
    for msg in messages:
        if msg.tool_calls is not None:
            formatted_messages.append({"role": msg.role, "content": msg.content, "tool_calls": msg.tool_calls})
        else:
            formatted_messages.append({"role": msg.role, "content": msg.content})
    return formatted_messages


def format_tools(tools):
    t_tools = []
    for tool in tools:
        t_tools.append(
            {
                "type": tool.type,
                "function": {
                    "name": tool.function.name,
                    "description": tool.function.description,
                    "parameters": tool.function.parameters,
                },
            }
        )
    return t_tools


@app.post("/restore_cache")
async def restore_cache(request: RestoreCacheRequest):
    global MODEL
    global MODEL_NAME
    global CURRENT_CACHE
    
    try:
        # extract messages and tools
        messages = format_messages(request.messages)
        tools = format_tools(request.tools)
        
        # Get consistent seed and temperature
        seed = request.inference_configs.get("seed", 12345)  # Use consistent default
        temperature = request.inference_configs.get("temperature", 0.0)
        
        # handle cache
        prompt = format_prompt(messages, tools)
        cache_context = Cache.build_cache(
            cache_dir=os.path.join(os.path.dirname(__file__), "cache"),
            prompts=prompt,
            model=MODEL,
            model_name=MODEL_NAME,
            temperature=temperature,
            seed=seed,  # Pass seed explicitly
        )
        MODEL.load_state(cache_context)
        CURRENT_CACHE = cache_context  # Track current cache
        
        logger.info(f"Cache restored successfully for model {MODEL_NAME} with seed {seed}")
        return {"status": "ok", "message": "cache is restored"}
    except Exception as e:
        logger.error(f"Error restoring cache: {e}")
        raise HTTPException(status_code=500, detail=f"Error restoring cache: {str(e)}")


@app.post("/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    global MODEL
    global MODEL_NAME
    global CURRENT_CACHE
    
    if request.model is None or request.model == "":
        raise HTTPException(status_code=400, detail="Model name must be provided")
    elif request.model != MODEL_NAME:
        try:
            load_model(request.model, request.load_model_configs)
            logger.info(f"Model has been changed to {MODEL_NAME}")
        except ValueError as e:
            logger.error(f"Failed to load requested model '{request.model}': {e}")
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(
                f"Unexpected error loading model '{request.model}': {e}", exc_info=True
            )
            raise HTTPException(
                status_code=500, detail=f"Error loading model: {str(e)}"
            )

    try:
        # Log request details at DEBUG level (excluding potentially sensitive message content)
        debug_request_summary = {
            "model": request.model,
            "num_messages": len(request.messages),
            "num_tools": len(request.tools) if request.tools else 0,
            "stream": request.stream,
            "inference_keys": list(request.inference_configs.keys()),
            "load_model_keys": list(request.load_model_configs.keys()),
            "seed": request.inference_configs.get("seed", "default(12345)"),
            "temperature": request.inference_configs.get("temperature", 0.0),
        }
        logger.debug(f"Chat completion request details: {debug_request_summary}")

        # Validate cache consistency
        if not is_cache_valid_for_request(request.messages, request.tools, request.inference_configs):
            logger.info("Current cache is not valid for this request, clearing cache")
            CURRENT_CACHE = None

        messages = format_messages(request.messages)
        tools = format_tools(request.tools) if request.tools else []

        # Check if stream parameter is in request
        stream = request.stream

        if stream:
            logger.debug("Starting stream response generation.")
            return StreamingResponse(
                _async_stream_wrapper(messages, tools, request.inference_configs),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
        else:
            logger.debug("Starting non-stream response generation.")
            # Get the generator object
            return _chat_completion(messages, tools, request.inference_configs)

    except Exception as e:
        logger.error(f"Error creating chat completion: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error creating chat completion: {str(e)}"
        )


def main():
    parser = argparse.ArgumentParser(description="LLM Server")
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Host to bind the server to"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind the server to"
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="qwen2.5-3b-instruct-q4_k_m.gguf",
        help="Default LLM model to use",
    )
    parser.add_argument("--n_ctx", type=int, default=4096, help="Default LLM N_CTX")
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log level",
    )
    args = parser.parse_args()

    # --- Setup Logging ---
    # Convert log level string from args to logging constant
    log_level_int = getattr(logging, args.log_level.upper(), logging.INFO)
    # Configure logging using the centralized setup, sending to stdout for LLM server
    setup_logging(log_level=log_level_int, stream=sys.stdout)
    # --- Logging is now configured ---
    logger.info(f"Logging level set to: {args.log_level.upper()}")

    # Set default model if provided via command line, otherwise use the one from request
    global MODEL_NAME
    if args.model_name:
        try:
            MODEL_NAME = args.model_name
            load_model_configs = {"n_ctx": args.n_ctx}
            load_model(MODEL_NAME, load_model_configs)
            # Logger is already configured, level is set
        except ValueError as e:
            logger.error(
                f"Failed to load default model '{args.model_name}' from command line: {e}"
            )
            # Decide if server should exit or continue without a default model
            sys.exit(f"Error: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error loading default model '{args.model_name}': {e}",
                exc_info=True,
            )
            sys.exit("Error loading default model.")

    logger.info(f"Starting LLM Server on {args.host}:{args.port}")

    # Start the server
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
