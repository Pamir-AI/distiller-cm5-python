#!/usr/bin/env python3
"""
LLM Server - Provides LLM services over HTTP
"""
import argparse
import logging
import json
import os
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn
from llama_cpp import Llama

from llama_cpp.llama_cache import LlamaDiskCache
from jinja2 import Template
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("llm-server")

# Create FastAPI app
app = FastAPI(title="LLM Server", description="A simple LLM server that provides LLM services")

MODEL_NAME = None
MODEL = None

# Define request and response models
class Message(BaseModel):
    role: str
    content: str


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
        temperature: float = 0.0,
        capacity_bytes: int = 2 << 30,
        seed: Optional[int] = None,
    ):
        cache = Cache(model)
        if seed: model.set_seed(seed)
        cache_context = LlamaDiskCache(cache_dir=cache_dir)
        model.set_cache(cache_context)
        prompt_tokens = cache.get_cache_key(prompts)

        try :
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
            return {"status": "warning", "message": "LLM model loaded but no model name set"}
        return {"status": "ok", "message": f"LLM Server is healthy, using model: {MODEL_NAME}"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.get("/models")
async def list_models():
    try:
        # 扫描models目录下的所有gguf文件
        path = os.path.join(os.path.dirname(__file__), "models")
        model_names = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and f.endswith('.gguf')]
        logger.info(f"Found {len(model_names)} models in models directory")
        return {"models": [m for m in model_names]}
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing models: {str(e)}")


@app.post("/setModel")
async def set_model(request: SetModel):
    try:
        load_model(request.model_name, request.load_model_configs)
        return {"status": "ok", "message": "model is change to " + request.modelName}
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=500, detail=f"Error set models: {str(e)}")

def load_model(model_name, load_model_configs:dict[str, Any]):
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

# TODO : we need to use config file to set the all the general parameters

def _chat_completion(messages, tools, inference_configs):
    """Non-streaming version"""
    response = MODEL.create_chat_completion(
        messages=messages,
        tools=tools,
        temperature=inference_configs["temperature"],
        max_tokens=inference_configs["max_tokens"],
        top_k=inference_configs["top_k"],
        top_p=inference_configs["top_p"],
        repeat_penalty=inference_configs["repetition_penalty"],
        stop=inference_configs["stop"],
        stream=False
    )
    return response

def _stream_chat_completion(messages, tools, inference_configs):
    """Streaming version"""
    response_stream = MODEL.create_chat_completion(
        messages=messages,
        tools=tools,
        temperature=inference_configs["temperature"],
        max_tokens=inference_configs["max_tokens"],
        top_k=inference_configs["top_k"],
        top_p=inference_configs["top_p"],
        repeat_penalty=inference_configs["repetition_penalty"],
        stop=inference_configs["stop"],
        stream=True
    )

    for chunk in response_stream:
        # Convert dictionary to JSON string before yielding
        yield f"data: {json.dumps(chunk)}\n\n"

def format_prompt(messages, tools):
    # Actual input received by the model
    model_template = MODEL.metadata.get('tokenizer.chat_template')
    template = Template(model_template)
    logger.info(f"format_prompt: {messages}, {tools}")
    rendered_prompt = template.render(messages=messages, tools=tools)
    logger.info("Actual prompt into llm:\n" + rendered_prompt)
    return rendered_prompt

def format_messages(messages):
    formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
    # Move the followig to the client side
    # for i in range(len(formatted_messages)):
    #     if formatted_messages[i]["role"] == "function":
    #         formatted_messages[i]["role"] = "user"
    #         formatted_messages[i]["content"] = "[TOOL EXECUTION RESULT]" + formatted_messages[i]["content"]
    return formatted_messages

def format_tools(tools):
    t_tools = []
    for tool in tools:
        t_tools.append({
            "type": tool.type,
            "function": {
                "name": tool.function.name,
                "description": tool.function.description,
                "parameters": tool.function.parameters
            }
        })
    return t_tools

@app.post("/restore_cache")
async def restore_cache(request: RestoreCacheRequest):
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
        return HTTPException(status_code=500, detail="please set model name")
    elif request.model !=MODEL_NAME:
        MODEL_NAME = request.model
        load_model(MODEL_NAME,request.load_model_configs)
        logger.info(f"Model is change to {MODEL_NAME}")

    try:
        logger.info(f"Received chat completion request: {request}")

        messages = format_messages(request.messages)
        tools = format_tools(request.tools)   
    
        # Check if stream parameter is in request
        stream = request.stream
            
        logger.info(f"Creating completion with model={MODEL_NAME}, messages={len(messages)}, stream={stream}")
        if tools:
            logger.info(f"Including {len(tools)} tools")

        if stream:
            logger.info("Use stream to response")
            return StreamingResponse(_stream_chat_completion(messages, tools, request.inference_configs),
                                    media_type="text/event-stream",
                                    headers={
                                        "Cache-Control": "no-cache",
                                        "Connection": "keep-alive",
                                    })
        else:
            # Get the generator object
            return _chat_completion(messages, tools, request.inference_configs)
            
    except Exception as e:
        logger.error(f"Error creating chat completion: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating chat completion: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="LLM Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    parser.add_argument("--model_name", type=str, default="qwen2.5-3b-instruct-q4_k_m.gguf", help="Default LLM model to use")
    parser.add_argument("--n_ctx", type=int, default=4096, help="Default LLM N_CTX")
    parser.add_argument("--log-level", type=str, default="info", choices=["debug", "info", "warning", "error"],
                        help="Log level")
    args = parser.parse_args()

    # Set log level
    log_level = getattr(logging, args.log_level.upper())
    logger.setLevel(log_level)

    # Set default model if provided via command line, otherwise use the one from request
    global MODEL_NAME
    if args.model_name:
        MODEL_NAME = args.model_name
        load_model_configs = {"n_ctx": args.n_ctx}
        load_model(MODEL_NAME, load_model_configs)
        logger.info(f"Default model set to {MODEL_NAME} (from command line)")

    logger.info(f"Starting LLM Server on {args.host}:{args.port}")

    # Start the server
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
