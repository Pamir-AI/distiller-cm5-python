#!/usr/bin/env python3
"""
LLM Server - Provides LLM services over HTTP
"""
import argparse
import logging
import json
import os
import sys
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

MODEL_NAME = None
MODEL = None


# Define request and response models
class Message(BaseModel):
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None


class SetModel(BaseModel):
    model_name: str
    load_model_configs: Dict[str, Any] = dict()


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

    def get_cache_key(self, prompt: str):
        return self.model.tokenize(prompt.encode("utf-8"))

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
        if seed:
            model.set_seed(seed)
        
        # Create a model-specific cache directory
        model_specific_cache_dir = os.path.join(cache_dir, model_name)
        os.makedirs(model_specific_cache_dir, exist_ok=True) # Ensure the directory exists

        cache_context = LlamaDiskCache(cache_dir=model_specific_cache_dir)
        model.set_cache(cache_context)
        prompt_tokens = cache.get_cache_key(prompts)

        try:
            cached_state = cache_context[prompt_tokens]
            return cached_state
        except Exception as e:
            # cache non exist
            model.reset()
            _ = model(
                prompts,
                max_tokens=1,  # Minimal tokens for cache creation
                temperature=temperature,
                echo=False,
            )
            # Save the state to cache
            cache_context[prompt_tokens] = model.save_state()
            return cache_context[prompt_tokens]


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


@app.post("/setModel")
async def set_model(request: SetModel):
    try:
        load_model(request.model_name, request.load_model_configs)
        return {"status": "ok", "message": "model is change to " + request.model_name}
    except Exception as e:
        logger.error(f"Error setting model: {e}")
        raise HTTPException(status_code=500, detail=f"Error set models: {str(e)}")


def load_model(model_name, load_model_configs: dict[str, Any]):
    global MODEL
    global MODEL_NAME
    model_path = os.path.join(os.path.dirname(__file__), "models", model_name)
    if not os.path.exists(model_path):
        raise ValueError(f"Model '{model_name}' not found in models directory")

    MODEL = Llama(
        model_path=str(model_path),
        verbose=False,
        n_gpu_layers=0,
        n_ctx=load_model_configs["n_ctx"],
    )

    MODEL_NAME = model_name
    logger.info(f"Loaded model: {model_name}")
    return True


def _chat_completion(messages, tools, inference_configs):
    """Non-streaming version"""
    logger.debug("Generating non-streaming chat completion...")
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
    try:
        # extract messages and tools
        messages = format_messages(request.messages)
        tools = format_tools(request.tools)
        # handle cache
        prompt = format_prompt(messages, tools)
        cache_context = Cache.build_cache(
            cache_dir=os.path.join(os.path.dirname(__file__), "cache"),
            prompts=prompt,
            model=MODEL,
            model_name=MODEL_NAME,
            temperature=request.inference_configs["temperature"],
        )
        MODEL.load_state(cache_context)
        return {"status": "ok", "message": "cache is restored"}
    except Exception as e:
        logger.error(f"Error restoring cache: {e}")
        raise HTTPException(status_code=500, detail=f"Error restoring cache: {str(e)}")


@app.post("/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    global MODEL
    global MODEL_NAME
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
        }
        logger.debug(f"Chat completion request details: {debug_request_summary}")

        messages = format_messages(request.messages)
        tools = format_tools(request.tools) if request.tools else []

        # Check if stream parameter is in request
        stream = request.stream

        if stream:
            logger.debug("Starting stream response generation.")
            return StreamingResponse(
                _stream_chat_completion(messages, tools, request.inference_configs),
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
