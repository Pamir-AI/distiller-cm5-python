"""
LLM Server Provider - Unified provider for all LLM backends via HTTP
"""

import json
import aiohttp
import time
import requests  # Add requests for sync check
import uuid
import logging  # Added
from typing import Any, Dict, List, Optional, AsyncGenerator, Callable, AsyncIterator
from distiller_cm5_python.utils.config import (
    TEMPERATURE,
    TOP_P,
    TOP_K,
    REPETITION_PENALTY,
    N_CTX,
    MAX_TOKENS,
    STOP,
    MIN_P,
)  # Removed unused OPENAI_URL, DEEPSEEK_URL
from distiller_cm5_python.utils.distiller_exception import (
    UserVisibleError,
    LogOnlyError,
)

# Import parsing utils
from distiller_cm5_python.client.llm_infra.parsing_utils import (
    normalize_tool_call_json,
    parse_tool_calls,
    check_is_c_ntx_too_long,
    transform_tool_arguments,
)

# Get logger instance for this module
logger = logging.getLogger(__name__)


class _ToolCallAccumulator:
    """Helper class to accumulate tool call chunks from a stream."""

    def __init__(self):
        self._calls: List[Dict[str, Any]] = []

    def add_chunk(self, index: int, chunk: Dict[str, Any]):
        """Adds a tool call chunk (delta) to the accumulator."""
        if index is None:
            logger.warning(f"Tool call chunk missing index: {chunk}")
            return

        # Ensure list is long enough
        while len(self._calls) <= index:
            self._calls.append(
                {
                    "id": "",
                    "type": "function",
                    "function": {"name": "", "arguments": ""},
                    "_dispatched": False,
                }
            )

        current_tool = self._calls[index]

        # Merge chunk data
        if "id" in chunk and chunk["id"]:
            current_tool["id"] += chunk["id"]
        if "type" in chunk and chunk["type"]:  # Store type if provided
            current_tool["type"] = chunk["type"]
        if "function" in chunk:
            if "name" in chunk["function"] and chunk["function"]["name"]:
                current_tool["function"]["name"] += chunk["function"]["name"]
            if "arguments" in chunk["function"] and chunk["function"]["arguments"]:
                current_tool["function"]["arguments"] += chunk["function"]["arguments"]

        # Check for completion
        self._check_completion(current_tool)

    def _check_completion(self, tool_call: Dict[str, Any]):
        """Checks if a tool call is complete and logs it."""
        if (
            not tool_call.get("_dispatched")
            and tool_call.get("id")
            and tool_call.get("function", {}).get("name")
        ):
            # Mark as dispatched *before* logging to prevent race conditions
            tool_call["_dispatched"] = True
            logger.debug(
                f"Completed tool call: {tool_call['id']} - {tool_call['function']['name']}"
            )

    def get_final_calls(self) -> List[Dict[str, Any]]:
        """Returns the list of fully accumulated and valid tool calls."""
        final_calls = []
        for i, tool in enumerate(self._calls):
            tool_function = tool.get("function", {})
            tool_name = tool_function.get("name")
            tool_id = tool.get("id")

            # Ensure essential fields are present
            if tool_id and tool_name:
                try:
                    # Get the raw arguments
                    raw_arguments = tool_function.get("arguments")
                    parsed_arguments = transform_tool_arguments(raw_arguments, tool_name)
                    
                    # Update the tool with parsed arguments
                    final_tool_function = tool_function.copy() # Avoid modifying the original _calls entry directly if not needed elsewhere
                    final_tool_function["arguments"] = parsed_arguments
                    
                    final_tool = {
                        "id": tool_id,
                        "type": tool.get("type", "function"), # Preserve type if present, default to function
                        "function": final_tool_function
                    }
                    
                    final_calls.append(final_tool)

                except ValueError as e:
                    logger.warning(
                        f"_ToolCallAccumulator: Skipping tool call at index {i} due to argument parsing error for tool '{tool_name}': {e}. Original tool: {tool}"
                    )
            else:
                logger.warning(
                    f"_ToolCallAccumulator: Skipping incomplete accumulated tool call at index {i} (missing id or name): {tool}"
                )
        logger.debug(
            f"_ToolCallAccumulator: Returning {len(final_calls)} final tool calls."
        )
        return final_calls


async def _parse_llm_stream(
    response: aiohttp.ClientResponse,
) -> AsyncIterator[Dict[str, Any]]:
    """Parses Server-Sent Events (SSE) from an LLM stream response."""
    buffer = ""
    async for chunk in response.content.iter_any():
        if not chunk:
            continue
        try:
            buffer += chunk.decode("utf-8")
        except UnicodeDecodeError as e:
            logger.error(
                f"Unicode decode error in stream chunk: {e}. Chunk (bytes): {chunk!r}"
            )
            yield {"type": "error", "error": e, "detail": "Unicode decode error"}
            continue  # Skip this chunk

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()

            if not line:  # Skip empty lines (often between events)
                continue

            if line.startswith("data:"):
                data_str = line[len("data:") :].strip()
                if data_str == "[DONE]":
                    yield {"type": "done"}
                    return  # End iteration

                if not data_str:
                    continue  # Skip empty data lines

                try:
                    # logger.debug(f"Processing stream data line: '{data_str}'") # Re-commented: Very verbose, uncomment for deep stream debugging
                    chunk_data = json.loads(data_str)
                    yield {"type": "data", "payload": chunk_data}
                except json.JSONDecodeError as json_err:
                    log_buffer_snippet = buffer[:200] + (
                        "..." if len(buffer) > 200 else ""
                    )
                    logger.error(
                        f"JSON Decode Error in streaming response line: '{line}' | Error: {json_err}. Buffer snippet: '{log_buffer_snippet}'"
                    )  # Added buffer
                    yield {"type": "error", "error": json_err, "line": line}
                except Exception as e:  # Catch other potential errors during processing
                    log_buffer_snippet = buffer[:200] + (
                        "..." if len(buffer) > 200 else ""
                    )
                    logger.error(
                        f"Unexpected error processing stream line '{line}': {e}. Buffer snippet: '{log_buffer_snippet}'",
                        exc_info=True,
                    )  # Added buffer
                    yield {"type": "error", "error": e, "line": line}
            else:
                # Log lines that don't conform to SSE "data:" format, if any
                logger.warning(f"Received unexpected non-data line in stream: '{line}'")

    # If the loop finishes without receiving "[DONE]", log a warning.
    logger.warning("LLM stream ended without a '[DONE]' marker.")
    yield {"type": "done"}  # Still signal completion


class LLMClient:
    """Provides LLM capabilities through HTTP API calls to various backends"""

    def __init__(
        self,
        server_url: str,
        model: str,
        provider_type: str = "llama-cpp",  # Default to llama-cpp
        api_key: Optional[str] = None,
        timeout: int = 30,
        streaming: bool = True,
    ):
        """Initialize the LLM server provider. Assumes server is already running.

        Args:
            server_url: URL of the LLM server (e.g., "http://localhost:8000" for llama-cpp or "https://openrouter.ai/api/v1" for openrouter)
            model: Model to use for completions (e.g., "local-model.gguf" or "openai/gpt-4o")
            provider_type: Type of provider ("llama-cpp" or "openrouter")
            api_key: API key (required for "openrouter")
            timeout: Request timeout in seconds
            streaming: Whether to use streaming responses by default
        """
        self.server_url = server_url.rstrip("/")  # Ensure no trailing slash
        self.model = model
        self.provider_type = provider_type.lower()
        self.api_key = api_key
        self.timeout = timeout
        self.streaming = streaming
        # Removed manager instance: self.llama_manager = None

        # Define common endpoint paths
        self.chat_completion_url = "/chat/completions"
        self.models_url = "/models"

        # Llama.cpp specific paths (relative to its server_url)
        self.restore_cache_url = "/restore_cache"
        self.load_model_url = "/setModel"
        # Llama.cpp health endpoint (used for simple check)
        self.health_endpoint = "/health"

        self.inference_configs = {
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "top_k": TOP_K,
            "min_p": MIN_P,
            "repetition_penalty": REPETITION_PENALTY,
            "max_tokens": MAX_TOKENS,
            "stop": STOP,
        }

        # Simplified initialization: Check connection but don't try to start server
        if self.provider_type == "llama-cpp":
            if not self._check_llama_cpp_connection_sync():
                # Log a warning, but don't raise an error immediately.
                # Let the first actual request fail if connection is terrible.
                logger.warning(
                    f"LLMClient.__init__: Initial check failed for llama-cpp server at {self.server_url}. Client will proceed, but requests may fail."
                )

        elif self.provider_type == "openrouter":
            # Check connection for OpenRouter (or compatible API)
            if (
                not self._check_cloud_api_connection_sync()
            ):  # Use sync check during init
                #  logger.error(f"LLMClient.__init__: Could not connect to API at {self.server_url}")
                raise UserVisibleError(
                    f"Could not connect to API at {self.server_url}. Check URL and API key."
                )
        else:
            logger.error(
                f"LLMClient.__init__: Unsupported provider type specified: '{self.provider_type}'. Use 'llama-cpp' or 'openrouter'."
            )
            raise ValueError(f"Unsupported provider type: {self.provider_type}")

    def _get_endpoint(self, path: str) -> str:
        """Constructs the full endpoint URL"""
        base = self.server_url.rstrip("/")
        path = path.lstrip("/")
        return f"{base}/{path}"

    # TODO : questionable implementation, revisit later
    def switch_provider(
        self,
        server_url: str,
        model: str,
        provider_type: str,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        streaming: Optional[bool] = None,
    ):
        """Switch the LLM provider configuration, checking connection for the new provider."""
        new_provider_type = provider_type.lower()
        new_server_url = server_url.rstrip("/")
        new_model = model
        new_api_key = api_key
        new_timeout = timeout if timeout is not None else self.timeout
        new_streaming = streaming if streaming is not None else self.streaming

        logger.info(
            f"Attempting to switch LLM provider from {self.provider_type}@{self.server_url} to {new_provider_type}@{new_server_url}"
        )

        if new_provider_type not in ["llama-cpp", "openrouter"]:
            logger.error(
                f"Cannot switch provider: Unsupported provider type '{new_provider_type}'. Must be 'llama-cpp' or 'openrouter'."
            )
            return False

        if (
            self.provider_type == new_provider_type
            and self.model == new_model
            and self.server_url == new_server_url
        ):
            return True

        # --- Pre-switch Validation ---
        # Check connection for the *new* provider *before* changing self state
        connection_valid = False
        # Removed temporary manager logic
        try:
            if new_provider_type == "llama-cpp":
                # Check connection using temporary values
                original_url = self.server_url
                self.server_url = new_server_url
                connection_valid = self._check_llama_cpp_connection_sync()
                self.server_url = original_url  # Restore
            elif new_provider_type == "openrouter":
                # Check cloud connection using temporary values
                original_values = (self.server_url, self.api_key)
                self.server_url = new_server_url
                self.api_key = new_api_key
                connection_valid = self._check_cloud_api_connection_sync()  # Sync check
                self.server_url, self.api_key = original_values  # Restore

        except (UserVisibleError, ValueError, Exception) as e:
            logger.error(f"Connection check failed during provider switch attempt: {e}")
            connection_valid = False
        # Removed temporary manager stop logic

        # --- End Pre-switch Validation ---

        if not connection_valid:
            logger.error(
                f"Cannot switch provider: Failed connection check for {new_provider_type} at {new_server_url} with model {new_model}."
            )
            return False

        # --- Finalize Switch ---
        # Removed stopping of previous manager

        # Apply new settings
        self.server_url = new_server_url
        self.model = new_model
        self.provider_type = new_provider_type
        self.api_key = new_api_key
        self.timeout = new_timeout
        self.streaming = new_streaming

        # Removed creation/start of new manager
        return True

    # Removed terminate_llama_cpp_server method

    def check_connection(self) -> bool:
        """Check if the connection to the configured server is valid"""
        if self.provider_type == "llama-cpp":
            # Use the synchronous check for external calls
            return self._check_llama_cpp_connection_sync()
        elif self.provider_type == "openrouter":
            # Use the synchronous check for external calls to check_connection
            return self._check_cloud_api_connection_sync()
        else:
            logger.error(
                f"Checking connection for unknown provider type: {self.provider_type}"
            )
            return False

    # --- New method for Llama-cpp sync connection check ---
    def _check_llama_cpp_connection_sync(self) -> bool:
        """Synchronously check connection for llama-cpp server using health endpoint."""
        endpoint = self._get_endpoint(self.health_endpoint)
        try:
            # Use requests for sync check, short timeout
            response = requests.get(endpoint, timeout=2)
            if response.status_code == 200:
                return True
            else:
                logger.warning(
                    f"Sync llama-cpp connection check failed at {endpoint}. Status: {response.status_code}"
                )
                return False
        except requests.exceptions.RequestException as e:
            logger.warning(
                f"Sync llama-cpp connection check failed at {endpoint}. Error: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error during sync llama-cpp connection check: {e}"
            )
            return False

    # --- End new method ---

    # Sync version for use in __init__ and external checks
    def _check_cloud_api_connection_sync(self) -> bool:
        """Synchronously check connection for cloud-based APIs (e.g., OpenRouter)."""
        endpoint = self._get_endpoint(self.models_url)
        logger.debug(f"Checking cloud API connection sync at: {endpoint}")
        try:
            headers = self._get_headers()
            if not headers.get("Authorization"):
                logger.error(
                    f"Cannot check connection sync to {self.server_url}: API key is missing."
                )
                return False

            # Use standard requests for sync check
            response = requests.get(endpoint, timeout=10, headers=headers)

            if response.status_code == 200:
                logger.debug(
                    f"Sync cloud API connection successful to {self.server_url}."
                )
                return True
            else:
                logger.warning(
                    f"Sync cloud API connection check failed at {endpoint}. Status: {response.status_code}, Response: {response.text[:100]}..."
                )
                return False
        except requests.exceptions.RequestException as e:
            logger.warning(
                f"Sync cloud API connection check failed at {endpoint}. Error: {e}"
            )
            return False
        except Exception as e:
            logger.error(f"Unexpected error during sync cloud connection check: {e}")
            return False

    # Async version for internal use during API calls if needed later (currently unused)
    async def _check_cloud_api_connection_async(self) -> bool:
        """Asynchronously check connection for cloud-based APIs (e.g., OpenRouter)."""
        endpoint = self._get_endpoint(self.models_url)
        headers = self._get_headers()
        if not headers.get("Authorization"):
            logger.error(
                f"Cannot check connection async to {self.server_url}: API key is missing."
            )
            return False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    endpoint, timeout=10, headers=headers
                ) as response:
                    if response.status == 200:
                        return True
                    else:
                        response_text = await response.text()
                        logger.warning(
                            f"Async cloud API connection check failed at {endpoint}. Status: {response.status}, Response: {response_text[:100]}..."
                        )
                        return False
        except aiohttp.ClientError as e:
            logger.warning(
                f"Async cloud API connection check failed at {endpoint}. Error: {e}"
            )
            return False
        except Exception as e:
            logger.error(f"Unexpected error during async cloud connection check: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests, including Authorization if api_key is set."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _prepare_chat_completion_payload(
        self, messages: List[Dict], tools: Optional[List[Dict]], stream: bool
    ) -> Dict:
        """Prepares the payload for the /chat/completions endpoint."""
        payload = {
            "messages": messages,
            "model": self.model,
            "stream": stream,
            "inference_configs": self.inference_configs,
            # Include load_model_configs for llama.cpp provider
            "load_model_configs": (
                {"n_ctx": N_CTX} if self.provider_type == "llama-cpp" else {}
            ),
        }
        if tools:
            payload["tools"] = tools

        # Log summary
        log_summary = {
            "model": payload["model"],
            "num_messages": len(payload["messages"]),
            "num_tools": len(payload.get("tools", [])),
            "stream": payload["stream"],
            "provider": self.provider_type,
        }
        logger.debug(f"Prepared chat completion payload: {log_summary}")
        return payload

    async def restore_cache(self, messages: List[Dict], tools: List[Dict]):
        """(Llama-cpp only) Restore the KV cache via API call."""
        if self.provider_type != "llama-cpp":
            logger.warning(
                "Restore cache is only supported for llama-cpp provider. Skipping."
            )
            return {"status": "skipped", "detail": "Not a llama-cpp provider"}

        logger.debug("LLMClient.restore_cache: Restoring llama-cpp cache via API")
        endpoint = self._get_endpoint(self.restore_cache_url)
        payload = {
            "messages": messages,
            "tools": tools,
            "inference_configs": self.inference_configs,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=self.timeout,
                ) as response:
                    response_data = await response.json()
                    logger.debug(
                        f"Restore cache response status: {response.status}, data: {response_data}"
                    )
                    response.raise_for_status()
                    return response_data
        except aiohttp.ClientError as e:
            logger.error(f"Error restoring cache: {e}")
            return {"status": "error", "detail": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error restoring cache: {e}")
            return {"status": "error", "detail": str(e)}

    async def load_model(self):
        """(Llama-cpp only) Request the server to load the current model via API call."""
        if self.provider_type != "llama-cpp":
            logger.warning(
                "Loading model is only supported for llama-cpp provider. Skipping."
            )
            return {"status": "skipped", "detail": "Not a llama-cpp provider"}

        logger.debug(
            f"LLMClient.load_model: Requesting server to load model '{self.model}' via API"
        )
        endpoint = self._get_endpoint(self.load_model_url)
        payload = {"model_name": self.model, "inference_configs": {"n_ctx": N_CTX}}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=max(self.timeout, 120),
                ) as response:
                    response_data = await response.json()
                    logger.debug(
                        f"Load model response status: {response.status}, data: {response_data}"
                    )
                    response.raise_for_status()
                    return response_data
        except aiohttp.ClientError as e:
            logger.error(f"Error requesting model load: {e}")
            return {"status": "error", "detail": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error requesting model load: {e}")
            return {"status": "error", "detail": str(e)}

    # --- Get Completion Methods ---

    async def get_chat_completion_response(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = [],
        callback: Optional[
            Callable[[str, uuid.UUID], None]
        ] = lambda text, msg_id: logger.info(f"LLM Response Text: {text}"),
        print_content: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Sends a request to the LLM and returns the full response (non-streaming).

        Args:
            messages: List of messages to send to the LLM
            tools: List of tools to include in the request
            callback: Optional callback function to call with the response text and msg_id
            print_content: Optional callback function to call with each content chunk

        Returns:
            Dict: The full response from the LLM, formatted as {"message": {...}}
        """
        endpoint = self._get_endpoint(self.chat_completion_url)
        payload = self._prepare_chat_completion_payload(messages, tools, stream=False)
        headers = self._get_headers()

        start_time_req = time.time()

        response_data = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint, json=payload, headers=headers, timeout=self.timeout
                ) as response:
                    status_code = response.status
                    response_text = await response.text()

                    if status_code != 200:
                        error_detail = response_text
                        try:
                            error_json = json.loads(response_text)
                            error_detail = error_json.get(
                                "detail", error_json.get("error", response_text)
                            )
                        except json.JSONDecodeError:
                            pass

                        if self.provider_type == "llama-cpp":
                            ctx_info = check_is_c_ntx_too_long(str(error_detail))
                            if ctx_info:
                                error_msg = f"Requested tokens ({ctx_info[0]}) exceed context window ({ctx_info[1]})."
                                logger.error(
                                    f"LLMClient.get_chat_completion_response: {error_msg}"
                                )
                                raise UserVisibleError(
                                    f"{error_msg} Please reduce message history length or query size."
                                )

                        logger.error(
                            f"LLMClient.get_chat_completion_response: Request failed. Status: {status_code}, Detail: {error_detail}"
                        )
                        response.raise_for_status()

                    response_data = json.loads(response_text)

            end_time_req = time.time()
            # Log summary of successful response at DEBUG
            log_summary = {
                "id": response_data.get("id"),
                "model": response_data.get("model"),
                "usage_prompt": response_data.get("usage", {}).get("prompt_tokens"),
                "usage_completion": response_data.get("usage", {}).get(
                    "completion_tokens"
                ),
                "has_content": bool(
                    response_data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content")
                ),
                "num_tool_calls": len(
                    response_data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("tool_calls", [])
                ),
                "duration_s": round(end_time_req - start_time_req, 2),
            }
            logger.debug(
                f"Received successful non-streaming LLM response: {log_summary}"
            )

            if not response_data.get("choices") or not response_data["choices"][0].get(
                "message"
            ):
                raise ValueError(
                    "Invalid response structure: 'choices[0].message' missing."
                )

            message = response_data["choices"][0]["message"]
            full_response_content = message.get("content", "")
            tool_calls = []

            if "tool_calls" in message and message["tool_calls"]:
                logger.debug("Found tool calls directly in response message object.")
                tool_calls = message["tool_calls"]
            elif (
                isinstance(full_response_content, str)
                and "<tool_call>" in full_response_content
            ):
                logger.debug(
                    "Found <tool_call> tags in response content, attempting to parse."
                )
                tool_calls = parse_tool_calls(full_response_content)
                if tool_calls:
                    full_response_content = full_response_content.split("<tool_call>")[
                        0
                    ].strip()
                    logger.debug(
                        f"Content updated after extracting tool calls: '{full_response_content[:100]}...'"
                    )
                    
            result = {
                "message": {
                    "content": full_response_content,
                    "role": "assistant",
                    "tool_calls": tool_calls,
                }
            }
            logger.info(
                f"LLMClient.get_chat_completion_response: Processed result. Content length: {len(full_response_content)}, Tool calls: {len(tool_calls)}"
            )

            # trigger callback if provided
            if callback and full_response_content:
                # Create a unique ID for this non-streaming message
                msg_id = uuid.uuid4()
                try:
                    callback(full_response_content, msg_id)
                except Exception as cb_err:
                    logger.error(
                        f"Error executing non-streaming callback: {cb_err}",
                        exc_info=True,
                    )

            # Call print_content if provided
            if print_content and full_response_content:
                try:
                    print_content(full_response_content)
                except Exception as cb_err:
                    logger.error(f"Error executing print_content callback: {cb_err}", exc_info=True)

            return result

        except UserVisibleError:
            raise
        except aiohttp.ClientResponseError as e:
            error_msg = f"HTTP Error {e.status} from LLM server: {e.message}"
            logger.error(error_msg, exc_info=True)
            # Return an error structure consistent with the success structure
            return {
                "message": {
                    "content": f"Error: {error_msg}",
                    "role": "assistant",
                    "tool_calls": [],
                }
            }
        except Exception as e:
            error_msg = f"Error communicating with LLM server: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "message": {
                    "content": f"Error: {error_msg}",
                    "role": "assistant",
                    "tool_calls": [],
                }
            }

    async def get_chat_completion_streaming_response(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = [],
        print_content: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Sends a request to the LLM and processes the streaming response asynchronously.

        Args:
            messages: List of messages to send to the LLM
            tools: List of tools to include in the request
            print_content: Optional callback function to call with each content chunk

        Returns:
            Dict: The final aggregated response dictionary after the stream ends.
        """
        start_time_req = time.time()
        endpoint = self._get_endpoint(self.chat_completion_url)
        payload = self._prepare_chat_completion_payload(messages, tools, stream=True)
        headers = self._get_headers()

        # Use a unique ID for this streaming request for event tracking
        stream_request_id = str(uuid.uuid4())
        logger.info(
            f"Starting streaming chat completion request ({stream_request_id}) to {endpoint} for model {self.model}"
        )

        full_response_content = ""
        tool_accumulator = _ToolCallAccumulator()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint, json=payload, headers=headers, timeout=self.timeout
                ) as response:
                    # --- Initial Response Check ---
                    if response.status != 200:
                        response_text = await response.text()
                        error_detail = response_text
                        try:
                            error_json = json.loads(response_text)
                            error_detail = error_json.get(
                                "detail", error_json.get("error", response_text)
                            )
                        except json.JSONDecodeError:
                            pass

                        # Check for specific llama-cpp context length error
                        if self.provider_type == "llama-cpp":
                            req_tokens, ctx_window = check_is_c_ntx_too_long(
                                str(error_detail)
                            )
                            if req_tokens is not None:
                                error_msg = f"Requested tokens ({req_tokens}) exceed context window ({ctx_window})."
                                logger.error(
                                    f"LLMClient.get_chat_completion_streaming_response: {error_msg}"
                                )
                                raise UserVisibleError(
                                    f"{error_msg} Please reduce message history length or query size."
                                )

                        # General HTTP error logging and exception
                        logger.error(
                            f"LLMClient.get_chat_completion_streaming_response: Stream request failed. Status: {response.status}, Detail: {error_detail}"
                        )
                        response.raise_for_status()  # Raise ClientResponseError for non-200 status

                    # --- Stream Processing ---
                    async for event in _parse_llm_stream(response):
                        if event["type"] == "data":
                            try:
                                chunk_data = event["payload"]
                                if (
                                    "choices" in chunk_data
                                    and len(chunk_data["choices"]) > 0
                                ):
                                    delta = chunk_data["choices"][0].get("delta", {})

                                    # -- Handle Content Delta --
                                    if (
                                        "content" in delta
                                        and delta["content"] is not None
                                    ):
                                        delta_content = delta["content"]
                                        # adapt for thinking method in Qwen 3 
                                        if "<think>" in delta_content or "</think>" in delta_content: 
                                            delta_content = delta_content.replace("<think>", "").replace("</think>", "").strip()

                                        if delta_content == "" or delta_content == "\n\n":
                                            continue
                                            
                                        full_response_content += delta_content
                                        
                                        # Call print callback if provided
                                        if print_content and delta_content:
                                            try:
                                                print_content(delta_content)
                                            except Exception as cb_err:
                                                logger.error(f"Error executing print_content callback: {cb_err}", exc_info=True)
                                        
                                        # Log content chunks for debugging
                                        if "<tool_call>" in delta_content:
                                            logger.info("Detected '<tool_call>' tag in content stream.")

                                    # -- Handle Tool Call Delta --
                                    if "tool_calls" in delta and delta["tool_calls"]:
                                        for tool_call_chunk in delta["tool_calls"]:
                                            index = tool_call_chunk.get("index")
                                            tool_accumulator.add_chunk(
                                                index, tool_call_chunk
                                            )

                            except Exception as processing_error:
                                logger.error(
                                    f"Error processing stream data chunk: {processing_error}",
                                    exc_info=True,
                                )

                        elif event["type"] == "done":
                            break  # Exit the async for loop

                        elif event["type"] == "error":
                            logger.error(
                                f"Stream parsing error: {event.get('error')} on line: {event.get('line', 'N/A')}"
                            )

                    # --- Stream Finished ---
                    end_time_req = time.time()
                    logger.info(
                        f"LLMClient.get_chat_completion_streaming_response ===== STREAMING COMPLETED ({end_time_req - start_time_req:.2f}s) ====="
                    )

            # --- Post-Stream Processing ---
            final_tool_calls = tool_accumulator.get_final_calls()

            logger.debug(
                f"LLMClient.get_chat_completion_streaming_response: Full response content: {full_response_content}"
            )

            # Fallback: Check accumulated text content for tool calls if none were found structurally
            if (
                not final_tool_calls
                and isinstance(full_response_content, str)
                and "<tool_call>" in full_response_content
            ):
                logger.warning(
                    "Stream ended. No structured tool calls found, but found '<tool_call>' tags in accumulated text. Attempting parse."
                )
                final_tool_calls = parse_tool_calls(full_response_content)
                if final_tool_calls:
                    # Remove the tool call section from the final content
                    full_response_content = full_response_content.split("<tool_call>")[
                        0
                    ].strip()
                    logger.debug(
                        f"Content updated after extracting tool calls from text: '{full_response_content[:100]}...'"
                    )
                    logger.info(
                        f"Parsed {len(final_tool_calls)} tool calls from text."
                    )
                else:
                    logger.warning("Tool call parsing failed")

            logger.info(
                f"LLMClient.get_chat_completion_streaming_response: Processed result. Content length: {len(full_response_content)}, Tool calls: {len(final_tool_calls)}"
            )

            
            return {
                "message": {
                    "content": full_response_content,
                    "role": "assistant",
                    "tool_calls": final_tool_calls,
                }
            }

        except UserVisibleError:
            # Logged and raised within the stream check
            raise
        except aiohttp.ClientResponseError as e:
            # Error during initial connection or non-200 status before stream starts fully
            error_msg = f"HTTP Error {e.status} during streaming setup from LLM server: {e.message}"
            logger.error(error_msg, exc_info=True)
            raise LogOnlyError(
                error_msg
            ) from e  # Convert to LogOnlyError for MCPClient
        except (
            aiohttp.ClientError
        ) as e:  # Catch other ClientErrors like connection issues, timeouts during streaming
            error_msg = f"HTTP Client Error during streaming: {e}"
            try:
                if "response" in locals() and response:
                    error_msg += (
                        f" (Status: {response.status}, Reason: {response.reason})"
                    )
            except (AttributeError, NameError):
                pass
            logger.error(error_msg, exc_info=True)
            raise LogOnlyError(error_msg) from e  # Convert to LogOnlyError
        except Exception as e:
            # Catch-all for unexpected errors during the process
            error_msg = f"Unexpected error during streaming chat completion: {str(e)} (Type: {type(e).__name__})"
            logger.error(error_msg, exc_info=True)
            # Convert to LogOnlyError so MCPClient can handle UI feedback gracefully
            raise LogOnlyError(error_msg) from e
