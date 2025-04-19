"""
LLM Server Provider - Unified provider for all LLM backends via HTTP
"""
import json
import aiohttp
import time
import requests # Add requests for sync check
from typing import Any, Dict, List, Optional, AsyncGenerator, Callable
from colorama import Fore, Style, init as colorama_init
from utils.logger import logger
from utils.config import (TEMPERATURE, TOP_P, TOP_K, REPETITION_PENALTY, N_CTX,
                            MAX_TOKENS, STOP) # Removed unused OPENAI_URL, DEEPSEEK_URL
from utils.distiller_exception import UserVisibleError, LogOnlyError
# Import parsing utils
from client.llm_infra.parsing_utils import (
    normalize_tool_call_json, parse_tool_calls, check_is_c_ntx_too_long
)
# Import Llama Manager - Removed: No longer needed here
# from client.llm_infra.llama_manager import LlamaCppServerManager


class LLMClient:
    """Provides LLM capabilities through HTTP API calls to various backends"""

    def __init__(self,
                 server_url: str,
                 model: str,
                 provider_type: str = "llama-cpp", # Default to llama-cpp
                 api_key: Optional[str] = None,
                 timeout: int = 30,
                 streaming: bool = True):
        """Initialize the LLM server provider. Assumes server is already running.

        Args:
            server_url: URL of the LLM server (e.g., "http://localhost:8000" for llama-cpp or "https://openrouter.ai/api/v1" for openrouter)
            model: Model to use for completions (e.g., "local-model.gguf" or "openai/gpt-4o")
            provider_type: Type of provider ("llama-cpp" or "openrouter")
            api_key: API key (required for "openrouter")
            timeout: Request timeout in seconds
            streaming: Whether to use streaming responses by default
        """
        self.server_url = server_url.rstrip('/') # Ensure no trailing slash
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
            "repetition_penalty": REPETITION_PENALTY,
            "max_tokens": MAX_TOKENS,
            "stop": STOP
        }

        # Simplified initialization: Check connection but don't try to start server
        if self.provider_type == "llama-cpp":
             if not self._check_llama_cpp_connection_sync():
                  # Log a warning, but don't raise an error immediately.
                  # Let the first actual request fail if connection is terrible.
                  logger.warning(f"LLMClient.__init__: Initial check failed for llama-cpp server at {self.server_url}. Client will proceed, but requests may fail.")
             else:
                  logger.info(f"LLMClient.__init__: Initial check successful for llama-cpp server at {self.server_url}, model={self.model}")

        elif self.provider_type == "openrouter":
            # Check connection for OpenRouter (or compatible API)
            if not self._check_cloud_api_connection_sync(): # Use sync check during init
                 logger.error(f"LLMClient.__init__: Could not connect to API at {self.server_url}")
                 raise UserVisibleError(f"Could not connect to API at {self.server_url}. Check URL and API key.")
            logger.info(
                f"LLMClient.__init__: Initialized openrouter client with server_url={self.server_url}, model={self.model}")
        else:
             logger.error(f"LLMClient.__init__: Unsupported provider type specified: '{self.provider_type}'. Use 'llama-cpp' or 'openrouter'.")
             raise ValueError(f"Unsupported provider type: {self.provider_type}")

    def _get_endpoint(self, path: str) -> str:
        """Constructs the full endpoint URL"""
        base = self.server_url.rstrip('/')
        path = path.lstrip('/')
        return f"{base}/{path}"

    # TODO : questionable implementation, revisit later 
    def switch_provider(self, server_url: str,
                        model: str,
                        provider_type: str,
                        api_key: Optional[str] = None,
                        timeout: Optional[int] = None,
                        streaming: Optional[bool] = None):
        """Switch the LLM provider configuration, checking connection for the new provider."""
        new_provider_type = provider_type.lower()
        new_server_url = server_url.rstrip('/')
        new_model = model
        new_api_key = api_key
        new_timeout = timeout if timeout is not None else self.timeout
        new_streaming = streaming if streaming is not None else self.streaming

        logger.info(f"Attempting to switch LLM provider from {self.provider_type}@{self.server_url} to {new_provider_type}@{new_server_url}")

        if new_provider_type not in ["llama-cpp", "openrouter"]:
             logger.error(f"Cannot switch provider: Unsupported provider type '{new_provider_type}'. Must be 'llama-cpp' or 'openrouter'.")
             return False

        if self.provider_type == new_provider_type and self.model == new_model and self.server_url == new_server_url:
            logger.info("Provider configuration is already set. No switch needed.")
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
                 self.server_url = original_url # Restore
            elif new_provider_type == "openrouter":
                # Check cloud connection using temporary values
                original_values = (self.server_url, self.api_key)
                self.server_url = new_server_url
                self.api_key = new_api_key
                connection_valid = self._check_cloud_api_connection_sync() # Sync check
                self.server_url, self.api_key = original_values # Restore

        except (UserVisibleError, ValueError, Exception) as e:
             logger.error(f"Connection check failed during provider switch attempt: {e}")
             connection_valid = False
        # Removed temporary manager stop logic

        # --- End Pre-switch Validation ---

        if not connection_valid:
            logger.error(f"Cannot switch provider: Failed connection check for {new_provider_type} at {new_server_url} with model {new_model}.")
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

        logger.info(f"LLMClient switched successfully to provider={self.provider_type}, model={self.model}, server={self.server_url}")
        return True

    # Removed terminate_llama_cpp_server method


    def check_connection(self) -> bool:
        """Check if the connection to the configured server is valid"""
        logger.debug(f"Checking connection for provider: {self.provider_type}")
        if self.provider_type == "llama-cpp":
            # Use the synchronous check for external calls
            return self._check_llama_cpp_connection_sync()
        elif self.provider_type == "openrouter":
            # Use the synchronous check for external calls to check_connection
            return self._check_cloud_api_connection_sync()
        else:
            logger.error(f"Checking connection for unknown provider type: {self.provider_type}")
            return False

    # --- New method for Llama-cpp sync connection check ---
    def _check_llama_cpp_connection_sync(self) -> bool:
        """Synchronously check connection for llama-cpp server using health endpoint."""
        endpoint = self._get_endpoint(self.health_endpoint)
        try:
            logger.debug(f"Checking llama-cpp connection sync at: {endpoint}")
            # Use requests for sync check, short timeout
            response = requests.get(endpoint, timeout=2)
            if response.status_code == 200:
                 logger.debug(f"Sync llama-cpp connection successful to {self.server_url}.")
                 return True
            else:
                 logger.warning(f"Sync llama-cpp connection check failed at {endpoint}. Status: {response.status_code}")
                 return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"Sync llama-cpp connection check failed at {endpoint}. Error: {e}")
            return False
        except Exception as e:
             logger.error(f"Unexpected error during sync llama-cpp connection check: {e}")
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
                logger.error(f"Cannot check connection sync to {self.server_url}: API key is missing.")
                return False

            # Use standard requests for sync check
            response = requests.get(endpoint, timeout=10, headers=headers)

            if response.status_code == 200:
                logger.debug(f"Sync cloud API connection successful to {self.server_url}.")
                return True
            else:
                logger.warning(f"Sync cloud API connection check failed at {endpoint}. Status: {response.status_code}, Response: {response.text[:100]}...")
                return False
        except requests.exceptions.RequestException as e:
            logger.warning(f"Sync cloud API connection check failed at {endpoint}. Error: {e}")
            return False
        except Exception as e:
             logger.error(f"Unexpected error during sync cloud connection check: {e}")
             return False

    # Async version for internal use during API calls if needed later (currently unused)
    async def _check_cloud_api_connection_async(self) -> bool:
        """Asynchronously check connection for cloud-based APIs (e.g., OpenRouter)."""
        endpoint = self._get_endpoint(self.models_url)
        logger.debug(f"Checking cloud API connection async at: {endpoint}")
        headers = self._get_headers()
        if not headers.get("Authorization"):
             logger.error(f"Cannot check connection async to {self.server_url}: API key is missing.")
             return False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, timeout=10, headers=headers) as response:
                    if response.status == 200:
                        logger.debug(f"Async cloud API connection successful to {self.server_url}.")
                        return True
                    else:
                        response_text = await response.text()
                        logger.warning(f"Async cloud API connection check failed at {endpoint}. Status: {response.status}, Response: {response_text[:100]}...")
                        return False
        except aiohttp.ClientError as e:
            logger.warning(f"Async cloud API connection check failed at {endpoint}. Error: {e}")
            return False
        except Exception as e:
             logger.error(f"Unexpected error during async cloud connection check: {e}")
             return False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests, including Authorization if api_key is set."""
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


    def _prepare_chat_completion_payload(self, messages: List[Dict], tools: Optional[List[Dict]], stream: bool) -> Dict:
        """Prepare the payload for the /chat/completions endpoint."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "inference_configs": self.inference_configs
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        
        logger.debug(f"Prepared payload for {self.provider_type}: {payload}")
        return payload


    async def restore_cache(self, messages: List[Dict], tools: List[Dict]):
        """(Llama-cpp only) Restore the KV cache via API call."""
        if self.provider_type != "llama-cpp":
            logger.warning("Restore cache is only supported for llama-cpp provider. Skipping.")
            return {"status": "skipped", "detail": "Not a llama-cpp provider"}

        logger.debug("LLMClient.restore_cache: Restoring llama-cpp cache via API")
        endpoint = self._get_endpoint(self.restore_cache_url)
        payload = {
            "messages": messages,
            "tools": tools,
            "inference_configs": self.inference_configs
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, json=payload, headers=self._get_headers(), timeout=self.timeout) as response:
                    response_data = await response.json()
                    logger.debug(f"Restore cache response status: {response.status}, data: {response_data}")
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
            logger.warning("Loading model is only supported for llama-cpp provider. Skipping.")
            return {"status": "skipped", "detail": "Not a llama-cpp provider"}

        logger.debug(f"LLMClient.load_model: Requesting server to load model '{self.model}' via API")
        endpoint = self._get_endpoint(self.load_model_url)
        payload = {
            "model_name": self.model,
            "inference_configs": { "n_ctx": N_CTX }
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, json=payload, headers=self._get_headers(), timeout=max(self.timeout, 120)) as response:
                     response_data = await response.json()
                     logger.debug(f"Load model response status: {response.status}, data: {response_data}")
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
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Get a non-streaming response from the /chat/completions endpoint."""
        logger.info(f"LLMClient.get_chat_completion_response ===== SENDING REQUEST TO LLM ({self.provider_type}) =====")
        start_time_req = time.time() # Use time directly here

        endpoint = self._get_endpoint(self.chat_completion_url)
        payload = self._prepare_chat_completion_payload(messages, tools, stream=False)
        headers = self._get_headers()

        log_payload = {k: v for k, v in payload.items() if k != 'messages'} # Avoid logging full messages
        log_payload['messages'] = f"<{len(payload.get('messages', []))} messages>"
        if 'tools' in log_payload: log_payload['tools'] = f"<{len(payload.get('tools', []))} tools>"
        logger.debug(f"Request Endpoint: {endpoint}")
        logger.debug(f"Request Payload (summary): {log_payload}")

        response_data = {}
        try:
            async with aiohttp.ClientSession() as session:
                 async with session.post(endpoint, json=payload, headers=headers, timeout=self.timeout) as response:
                     status_code = response.status
                     response_text = await response.text()
                     logger.debug(f"Response Status: {status_code}")
                     logger.debug(f"Response Text (first 500 chars): {response_text[:500]}")

                     if status_code != 200:
                        error_detail = response_text
                        try:
                            error_json = json.loads(response_text)
                            error_detail = error_json.get("detail", error_json.get("error", response_text))
                        except json.JSONDecodeError: pass

                        if self.provider_type == "llama-cpp":
                            req_tokens, ctx_window = check_is_c_ntx_too_long(str(error_detail))
                            if req_tokens is not None:
                                error_msg = f"Requested tokens ({req_tokens}) exceed context window ({ctx_window})."
                                logger.error(f"LLMClient.get_chat_completion_response: {error_msg}")
                                raise UserVisibleError(f"{error_msg} Please reduce message history length or query size.")

                        logger.error(f"LLMClient.get_chat_completion_response: Request failed. Status: {status_code}, Detail: {error_detail}")
                        response.raise_for_status()

                     response_data = json.loads(response_text)

            end_time_req = time.time()
            logger.info(f"LLMClient.get_chat_completion_response: Received successful response in {end_time_req - start_time_req:.2f}s")
            logger.debug(f"Response Data: {response_data}")

            if not response_data.get("choices") or not response_data["choices"][0].get("message"):
                 raise ValueError("Invalid response structure: 'choices[0].message' missing.")

            message = response_data["choices"][0]["message"]
            full_response_content = message.get("content", "")
            tool_calls = []

            if "tool_calls" in message and message["tool_calls"]:
                 logger.debug("Found tool calls directly in response message object.")
                 tool_calls = message["tool_calls"]
            elif isinstance(full_response_content, str) and "<tool_call>" in full_response_content:
                logger.debug("Found <tool_call> tags in response content, attempting to parse.")
                parsed_calls = parse_tool_calls(full_response_content)
                if parsed_calls:
                     tool_calls = parsed_calls
                     full_response_content = full_response_content.split("<tool_call>")[0].strip()
                     logger.debug(f"Content updated after extracting tool calls: '{full_response_content[:100]}...'")
                else:
                    logger.warning("Found <tool_call> tag in response, but failed to parse any valid calls.")

            result = {
                "message": {
                    "content": full_response_content,
                    "role": "assistant",
                    "tool_calls": tool_calls
                }
            }
            logger.info(f"LLMClient.get_chat_completion_response: Processed result. Content length: {len(full_response_content)}, Tool calls: {len(tool_calls)}")
            return result

        except UserVisibleError:
            raise
        except aiohttp.ClientResponseError as e:
             error_msg = f"HTTP Error {e.status} from LLM server: {e.message}"
             logger.error(error_msg, exc_info=True)
             return {"message": { "content": error_msg, "role": "assistant", "tool_calls": [] }}
        except Exception as e:
            error_msg = f"Error communicating with LLM server: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"message": { "content": error_msg, "role": "assistant", "tool_calls": [] }}

    async def get_chat_completion_streaming_response(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        callback: Optional[Callable[[str], None]] = lambda x: print(f"{Fore.CYAN}{x}{Style.RESET_ALL}", end="", flush=True)
    ) -> Dict[str, Any]:
        """Get a streaming response from the /chat/completions endpoint.
           Yields content chunks into the callback function.
        """
        logger.info(f"LLMClient.get_chat_completion_streaming_response ===== SENDING STREAMING REQUEST TO LLM ({self.provider_type}) =====")
        start_time_req = time.time()

        endpoint = self._get_endpoint(self.chat_completion_url)
        payload = self._prepare_chat_completion_payload(messages, tools, stream=True)
        headers = self._get_headers()

        log_payload = {k: v for k, v in payload.items() if k != 'messages'}
        log_payload['messages'] = f"<{len(payload.get('messages', []))} messages>"
        if 'tools' in log_payload: log_payload['tools'] = f"<{len(payload.get('tools', []))} tools>"
        logger.debug(f"Streaming Request Endpoint: {endpoint}")
        logger.debug(f"Streaming Request Payload (summary): {log_payload}")

        full_response_content = ""
        accumulated_tool_calls = []
        data_str = ""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, json=payload, headers=headers, timeout=self.timeout) as response:
                    if response.status != 200:
                         response_text = await response.text()
                         error_detail = response_text
                         try:
                             error_json = json.loads(response_text)
                             error_detail = error_json.get("detail", error_json.get("error", response_text))
                         except json.JSONDecodeError: pass

                         if self.provider_type == "llama-cpp":
                             req_tokens, ctx_window = check_is_c_ntx_too_long(str(error_detail))
                             if req_tokens is not None:
                                 error_msg = f"Requested tokens ({req_tokens}) exceed context window ({ctx_window})."
                                 logger.error(f"LLMClient.get_chat_completion_streaming_response: {error_msg}")
                                 raise UserVisibleError(f"{error_msg} Please reduce message history length or query size.")

                         logger.error(f"LLMClient.get_chat_completion_streaming_response: Stream request failed. Status: {response.status}, Detail: {error_detail}")
                         response.raise_for_status()

                    buffer = ""
                    async for chunk in response.content.iter_any():
                        if not chunk: continue
                        buffer += chunk.decode('utf-8')

                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()

                            if line.startswith("data:"):
                                data_str = line[len("data:"):].strip()
                                if data_str == "[DONE]":
                                    logger.debug("Received [DONE] marker.")
                                    break

                                if not data_str: continue

                                try:
                                    logger.debug(f"Processing line: '{line}'")
                                    chunk_data = json.loads(data_str)
                                    if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                                        delta = chunk_data["choices"][0].get("delta", {})

                                        if "content" in delta and delta["content"] is not None:
                                            content_piece = delta["content"]
                                            callback(content_piece)
                                            full_response_content += content_piece

                                        if "tool_calls" in delta and delta["tool_calls"]:
                                            for tool_call_chunk in delta["tool_calls"]:
                                                 index = tool_call_chunk.get("index")
                                                 if index is None: continue
                                                 while len(accumulated_tool_calls) <= index:
                                                     accumulated_tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                                                 current_tool = accumulated_tool_calls[index]
                                                 if "id" in tool_call_chunk and tool_call_chunk["id"]:
                                                     current_tool["id"] += tool_call_chunk["id"]
                                                 if "function" in tool_call_chunk:
                                                      if "name" in tool_call_chunk["function"] and tool_call_chunk["function"]["name"]:
                                                          current_tool["function"]["name"] += tool_call_chunk["function"]["name"]
                                                      if "arguments" in tool_call_chunk["function"] and tool_call_chunk["function"]["arguments"]:
                                                          current_tool["function"]["arguments"] += tool_call_chunk["function"]["arguments"]

                                except json.JSONDecodeError:
                                    logger.error(f"LLMClient.get_chat_completion_streaming_response: Failed to parse JSON from line: '{data_str}'")
                                    logger.debug(f"Raw data_str causing JSON error: '{data_str}'")
                        if data_str == "[DONE]": break
                    logger.debug("Finished iterating through response content chunks.")
                    logger.debug(f"Final buffer state before processing end: '{buffer}'")

            end_time_req = time.time()
            logger.info(f"LLMClient.get_chat_completion_streaming_response ===== STREAMING COMPLETED ({end_time_req - start_time_req:.2f}s) =====")
            logger.info(f"Total accumulated response length: {len(full_response_content)} characters")
            logger.debug(f"Full accumulated response content: {full_response_content}")

            final_tool_calls = []
            for i, tool in enumerate(accumulated_tool_calls):
                 if tool.get("id") and tool.get("function", {}).get("name"):
                     final_tool_calls.append(tool)
                 else:
                      logger.warning(f"Skipping incomplete accumulated tool call at index {i}: {tool}")

            if not final_tool_calls and isinstance(full_response_content, str) and "<tool_call>" in full_response_content:
                 logger.warning("Stream ended, but found <tool_call> tags in accumulated text content. Attempting parse.")
                 parsed_calls = parse_tool_calls(full_response_content)
                 if parsed_calls:
                     final_tool_calls = parsed_calls
                     full_response_content = full_response_content.split("<tool_call>")[0].strip()
                     logger.debug(f"Content updated after extracting tool calls from text: '{full_response_content[:100]}...'")

            logger.info(f"LLMClient.get_chat_completion_streaming_response: Processed result. Content length: {len(full_response_content)}, Tool calls: {len(final_tool_calls)}")

            return {
                "message": {
                    "content": full_response_content,
                    "role": "assistant",
                    "tool_calls": final_tool_calls
                }
            }

        except UserVisibleError:
            raise
        except aiohttp.ClientResponseError as e:
             error_msg = f"HTTP Error {e.status} during streaming from LLM server: {e.message}"
             logger.error(error_msg, exc_info=True)
             raise LogOnlyError(error_msg) from e
        except aiohttp.ClientError as e: # Catch other ClientErrors like TransferEncodingError
            error_msg = f"HTTP Client Error during streaming: {e}"
            # Attempt to get more details if possible
            try:
                 # Check if response is defined in this scope
                 if 'response' in locals() and response:
                     error_msg += f" (Status: {response.status}, Reason: {response.reason})"
                     # logger.debug(f"Response headers on error: {response.headers}") # Optional: uncomment for more detail
            except AttributeError: # response might not have status/reason
                pass
            logger.error(error_msg, exc_info=True) # Log with traceback
            # Re-raise a specific error type the caller might expect
            raise LogOnlyError(error_msg) from e
        except Exception as e:
            error_msg = f"Error in streaming from LLM server: {str(e)}"
            # Add type of exception for clarity
            error_msg += f" (Type: {type(e).__name__})"
            logger.error(error_msg, exc_info=True)
            raise LogOnlyError(error_msg) from e
