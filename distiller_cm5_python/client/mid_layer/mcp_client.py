import time
import asyncio
from typing import Optional, List, Dict, Any, AsyncGenerator, Callable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import sys
import os

# Change back to absolute imports
from distiller_cm5_python.client.mid_layer.llm_client import LLMClient
from distiller_cm5_python.client.mid_layer.processors import MessageProcessor, ToolProcessor, PromptProcessor
from distiller_cm5_python.utils.logger import logger
from distiller_cm5_python.utils.config import (STREAMING_ENABLED, LOGGING_LEVEL,
                          SERVER_URL, PROVIDER_TYPE, MODEL_NAME, TIMEOUT)
from contextlib import AsyncExitStack
# Remove colorama import
from distiller_cm5_python.utils.distiller_exception import UserVisibleError, LogOnlyError


class MCPClient:
    def __init__(
            self,
            streaming: Optional[bool] = None,
            llm_server_url: Optional[str] = None,
            provider_type: Optional[str] = None,
            model: Optional[str] = None,
            api_key: Optional[str] = None,
            timeout: Optional[int] = None
    ):
        self.session = None
        self.write = None
        self.stdio = None
        self.exit_stack = AsyncExitStack()
        # Use provided value or fallback to config default
        # The streaming flag here is primarily for informing the UI layer.
        # MCPClient internal logic will use non-streaming calls.
        self.streaming = streaming if streaming is not None else STREAMING_ENABLED
        _llm_server_url = llm_server_url or SERVER_URL
        _provider_type = provider_type or PROVIDER_TYPE
        _model = model or MODEL_NAME
        _api_key = api_key # Optional, can be None
        _timeout = timeout or TIMEOUT
        # TODO questionable if we need to keep both config system and init params system
        self.server_name = None

        # Initialize log level
        logger.setLevel(LOGGING_LEVEL)

        logger.info(f"Initializing MCPClient (streaming={self.streaming}, provider={_provider_type})")

        # Initialize available tools, resources, and prompts
        self.available_tools = []
        self.available_resources = [] # Store for potential future use/inspection
        self.available_prompts = [] # Store for potential future use/inspection

        # Initialize processors
        self.message_processor = MessageProcessor()
        self.prompt_processor = PromptProcessor()

        # Initialize the LLM provider with unified configuration
        # Pass the streaming flag to LLMClient as it might have internal uses
        logger.debug(
            f"Initializing LLMClient with server_url={_llm_server_url}, model={_model}, type={_provider_type}, stream={self.streaming}")
        self.llm_provider = LLMClient(
            server_url=_llm_server_url,
            model=_model,
            provider_type=_provider_type,
            api_key=_api_key,
            timeout=_timeout,
            streaming=self.streaming
        )

        # ToolProcessor initialized after session creation in connect_to_server
        self.tool_processor = None

        logger.debug("Client initialized with components")

    async def connect_to_server(self, server_script_path: str) -> bool:
        """Connect to an MCP server"""
        logger.info(f"Connecting to server at {server_script_path}")

        if not server_script_path.endswith('.py'):
            raise UserVisibleError("Server script must be a .py file")

        # use current python interpreter by default
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[server_script_path],
            env=None
        )

        try:
            logger.debug(f"Setting up stdio transport")

            start_time = time.time()
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

            logger.debug(f"Session established, initializing")

            init_result = await self.session.initialize()
            self.server_name = init_result.serverInfo.name

            end_time = time.time()
            logger.debug(f"Server connection completed in {end_time - start_time:.2f}s")

            logger.info(f"Connected to server: {self.server_name} v{init_result.serverInfo.version}")

            # Initialize tool processor after session is created
            self.tool_processor = ToolProcessor(self.session)

            logger.debug(f"Refreshing tool capabilities")

            await self.refresh_capabilities()

            # Information about tools
            logger.debug("Connected to MCP server with tools:")
            for i, tool in enumerate(self.available_tools):
                logger.debug(f"  - Tool {i + 1}: {tool['function']['name']}")
                logger.debug(f"    Description: {tool['function']['description']}")

            logger.debug(f"Connection and initialization successful")

            # setup system prompt
            self.message_processor.set_system_message(self.prompt_processor.generate_system_prompt())

            # setup sample (few shot) prompts
            for prompt in self.available_prompts:
                logger.debug(f"Sample Prompt:{prompt}")
                for message in prompt["messages"]:
                    if message["role"] in ["user", "assistant"]:
                        self.message_processor.add_message(message["role"], message["content"])
                    else:
                        logger.warning(f"Few shot injection message role not supported: {message['role']}")
            logger.debug(f"Refreshed tool capabilities")

            # enable cache restore if provider is llama-cpp
            if self.llm_provider.provider_type == "llama-cpp":
                await self.llm_provider.restore_cache(self.message_processor.get_formatted_messages(), self.available_tools)
            return True

        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            return False

    async def refresh_capabilities(self):
        """Refresh the client's knowledge of server capabilities"""
        if not self.session:
            raise UserVisibleError("Not connected to Mcp Server, so can't refresh capabilities")

        # First refresh tools through the tool processor
        await self.tool_processor.refresh_capabilities()

        # Set available tools
        self.available_tools = self.tool_processor.format_tools()

        # Set available resources
        try:
            resources_response = await self.session.list_resources()
            self.available_resources = resources_response.resources
        except Exception as e:
            logger.warning(f"Failed to get resources: {e}")
            self.available_resources = []

        # Set available prompts
        try:
            self.available_prompts = await self.prompt_processor.format_prompts(self.session)

        except Exception as e:
            logger.warning(f"Failed to get prompts: {e}")
            self.available_prompts = []

        logger.info(f"Mcp Server capabilities refreshed, total {len(self.available_tools)} tools, {len(self.available_resources)} resources, {len(self.available_prompts)} prompts")

    async def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> None:
        """Helper method to execute tool calls and add results to history."""
        if not tool_calls:
            return

        logger.info(f"Found {len(tool_calls)} tool calls to execute")
        for i, tool_call in enumerate(tool_calls):
            logger.info(f"Executing tool call {i + 1}/{len(tool_calls)}")
            tool_result_content = "Error: Tool call execution failed."
            try:
                if not isinstance(tool_call, dict) or 'function' not in tool_call:
                    error_msg = f"Invalid tool call format: {tool_call}"
                    logger.error(error_msg)
                    tool_result_content = error_msg
                else:
                    # Note: MessageProcessor.add_tool_call might be redundant now if _process_llm_response handles it.
                    # self.message_processor.add_tool_call(tool_call)
                    tool_result_content = await self.tool_processor.execute_tool_call_async(tool_call)
                    logger.info(f"Executed tool name: {tool_call.get('id', 'N/A')}")
                    logger.info(f"Executed tool result: {tool_result_content}")

            except Exception as e:
                error_msg = f"Error executing tool call {tool_call.get('function',{}).get('name', 'N/A')}: {e}"
                logger.error(f"{error_msg}")
                tool_result_content = error_msg # Store error as result
            finally:
                # Add the tool call result (or error) to the message history
                self.message_processor.add_tool_result(
                    tool_call, # Pass the original tool_call dict
                    tool_result_content
                )

    async def process_query(self, query: str , callback: Callable[[str], None] = lambda x: print(f"\033[94m{x}\033[0m")) -> None:
        """Process a user query, handle LLM calls, tool execution, and streaming.

        Yields:
            Content chunks from the LLM response.
        """
        logger.info(f"Processing query: '{query}'")
        self.message_processor.add_message("user", query)
        callback("\n\n thinking ... \n\n")


        max_tool_iterations = 5 # Prevent infinite loops
        current_iteration = 0

        while current_iteration < max_tool_iterations:
            current_iteration += 1
            logger.info(f"--- LLM Call Iteration {current_iteration} ---")
            messages = self.message_processor.get_formatted_messages()

            # Decide whether to use streaming for this specific call
            # Use streaming for the first call if globally enabled, otherwise non-streaming.
            use_stream_this_call = self.streaming and current_iteration == 1

            full_response_content = ""
            accumulated_tool_calls = []

            try:
                if use_stream_this_call:
                    logger.info("Initiating streaming LLM call...")
                    response = await self.llm_provider.get_chat_completion_streaming_response(
                        messages, self.available_tools, callback=callback
                    )
                else: # Use non-streaming call
                    logger.info("Initiating non-streaming LLM call...")
                    response = await self.llm_provider.get_chat_completion_response(messages, self.available_tools)
                    # Yield the full response content to callback
                    if callback:
                        callback(response.get("message", {}).get("content", ""))

                message_data = response.get("message", {})
                full_response_content = message_data.get("content", "")
                accumulated_tool_calls = message_data.get("tool_calls", [])
                
                                # --- Process Response (common logic for both stream fallback and non-stream) ---
                logger.debug(f"LLM full response content: {full_response_content}")
                logger.debug(f"LLM tool calls: {accumulated_tool_calls}")

                # Add assistant message (even if empty, tool calls might be present)
                # Ensure message_processor handles adding message with potential tool calls
                self.message_processor.add_message("assistant", full_response_content, tool_calls=accumulated_tool_calls)

                if not accumulated_tool_calls:
                    logger.info("No tool calls received, completing interaction.")
                    break # Exit the loop if no tools need execution

                # --- Execute Tool Calls ---
                callback("\n\n executing tool calls ... \n\n")
                await self._execute_tool_calls(accumulated_tool_calls)
                # History is updated within _execute_tool_calls

                # Continue loop to potentially call LLM again with tool results
                logger.info("Tool calls executed, preparing for potential next LLM call.")

            except (UserVisibleError, LogOnlyError) as e:
                logger.error(f"Error during LLM call or processing: {e}", exc_info=isinstance(e, LogOnlyError))
                callback(f"\n[Error: {e}]\n") # Yield error message to user
                break # Stop processing on error
            except Exception as e:
                logger.error(f"Unexpected error during LLM call or processing: {e}", exc_info=True)
                callback(f"\n[Unexpected Error: {e}]\n")
                break # Stop processing on unexpected error

        if current_iteration >= max_tool_iterations:
            logger.warning("Reached maximum tool execution iterations.")
            callback("\n[Reached max tool iterations]\n")

        logger.info("--- Query Processing Complete ---")

    async def cleanup(self):
        """Cleanup resources, like closing the session"""
        logger.debug("Cleaning up resources")

        # Perform any cleanup
        await self.exit_stack.aclose()

        logger.debug("Cleanup complete")

        return True
