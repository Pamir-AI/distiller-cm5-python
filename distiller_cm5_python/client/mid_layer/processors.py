"""
Processing layer for MCP client.
This file combines message, tool and prompt processors into a single module.
"""

import time
import json
import logging
from mcp import ClientSession
from datetime import datetime
from typing import List, Dict, Any, Union, Optional, Coroutine

from distiller_cm5_python.utils.logger import logger
from distiller_cm5_python.utils.config import MAX_MESSAGES_LENGTH, DEFAULT_SYSTEM_PROMPT
from distiller_cm5_python.utils.distiller_exception import UserVisibleError, LogOnlyError


def timestamp_to_time(timestamp):
    dt_object = datetime.fromtimestamp(timestamp)
    formatted_time = dt_object.strftime('%Y-%m-%d %H:%M:%S')
    return formatted_time


class MessageProcessor:
    """Processor for managing conversation history and formatting messages for LLM providers."""
    
    def __init__(self):
        """Initialize the message processor"""
        super().__init__()  # No verbose parameter needed
        
        self.message_history = []
        self.session_start_time = timestamp_to_time(time.time()).replace(":","-")

        # Debug message traffic tracking - only active when logger is in debug mode
        self.is_debug_mode = logger.isEnabledFor(logging.DEBUG)
        self.debug_history_file = f"debug_message_traffic_{self.session_start_time}.json"
        
        logger.debug(f"MessageProcessor.__init__: Initialized with {"DEBUG" if self.is_debug_mode else "INFO"} mode")

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None, tool_calls: List[Dict[str, Any]] = None) -> None:
        """Add a message to the conversation history
        
        Args:
            role: The role of the message sender (user, assistant, system, tool)
            content: The content of the message
            metadata: Optional metadata for the message
        """

        # Control message length
        if len(self.message_history) >= MAX_MESSAGES_LENGTH:
            logger.warning(f"MessageProcessor.add_message: Message history is full. Removing oldest message.")
            # Traverse the list from the beginning, find the first message that is not of the 'system' role
            for i, msg in enumerate(self.message_history):
                if msg["role"] != "system":
                    # Delete the first non-system role message
                    del self.message_history[i]
                    break

        metadata = metadata or {}
        
        message = {
            "role": role,
            "content": content,
            "time": timestamp_to_time(time.time()),
            "metadata": metadata
        }
        if tool_calls:
            message["tool_calls"] = tool_calls

        # Add to normal message history
        self.message_history.append(message)
        
        # If in debug mode, track detailed message traffic with message type
        if self.is_debug_mode:
            self._save_debug_traffic()

        logger.info(f"MessageProcessor.add_message: One {role} message added, now total {len(self.message_history)} messages")
    
    def set_system_message(self, content: str, metadata: Dict[str, Any] = None) -> None:
        """Set or replace the system message in the conversation history
        
        This method removes any existing system messages and adds a new one.
        
        Args:
            content: The content of the system message
            metadata: Optional metadata for the message
        """
        # Remove any existing system messages
        self.message_history = [msg for msg in self.message_history if msg["role"] != "system"]
        
        # Add the new system message
        metadata = metadata or {}
        if self.is_debug_mode:
            metadata["message_type"] = "system_message_set"
        
        self.add_message("system", content, metadata)
        
        logger.debug(f"MessageProcessor.set_system_message: System message set: {content[:50]}...")
    

    def add_tool_call(self, tool_call: Dict[str, Any]) -> None:
        """Add a tool call to the conversation history
        
        Args:
            tool_call: The tool call to add
        """
        tool_name = tool_call.get("function", {}).get("name", "") if "function" in tool_call else tool_call.get("name", "")
        tool_args = tool_call.get("function", {}).get("arguments", {}) if "function" in tool_call else tool_call.get("arguments", {})
        tool_call_id = tool_call.get("id", tool_name)

        assistant_message = self.message_history[-1] # last message is assistant message

        if assistant_message.get("tool_calls", None) is None:
            assistant_message["tool_calls"] = []
        
        assistant_message["tool_calls"].append({
            "id": tool_call_id,
            "type": "function",
            "function": {
                "name": tool_name,
                "arguments": tool_args
            }
        })

        self.message_history[-1] = assistant_message

        logger.info(f"Tool call added: {tool_name}")
        if self.is_debug_mode:
            self._save_debug_traffic()

    def add_tool_result(self, tool_call: Dict[str, Any], result: str) -> None:
        """Add a tool result to the conversation history
        
        Args:
            tool_call: The tool call that produced the result

            result: The result of the tool call
        """
        # Extract tool info
        tool_name = tool_call.get("function", {}).get("name", "") if "function" in tool_call else tool_call.get("name", "")
        tool_args = tool_call.get("function", {}).get("arguments", {}) if "function" in tool_call else tool_call.get("arguments", {})
        tool_call_id = tool_call.get("id", tool_name)

        metadata = {
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "tool_args": tool_args,
            "is_tool_result": True,
            "message_type": "tool_result"
        }

        self.add_message("tool", result, metadata)
        
        # If in debug mode, track detailed message traffic
        if self.is_debug_mode:
            self._save_debug_traffic()

        logger.debug(f"MessageProcessor.add_tool_result: {tool_name} and it's result({result}) are added into message history")

    def get_formatted_messages(self) -> List[Dict[str, Union[str, List[Dict[str, Any]]]]]:
        """Get the message history formatted for LLM API
        
        Returns:
            List of formatted messages
        """

        formatted_messages = []
        
        for message in self.message_history:
            role = message["role"]
            content = message["content"]
            tool_calls = message.get("tool_calls", [])
            metadata = message.get("metadata", {})
            
            # Handle tool results with special formatting
            if role == "tool" and metadata.get("is_tool_result", False):
                tool_name = metadata.get("tool_name", "unknown_tool")
                tool_call_id = metadata.get("tool_call_id", tool_name)
                formatted_messages.append({
                    "role": "tool",
                    "type": "function_call_output",
                    "tool_call_id": tool_call_id,
                    "content": content
                })
                
            elif role in ["user", "system"] or (role == "assistant" and len(tool_calls) == 0):
                formatted_messages.append({
                    "role": role,
                    "content": content
                    })
            elif role == "assistant":
                # Standard message formatting
                formatted_messages.append({
                    "role": role,
                    "content": content,
                    "tool_calls": tool_calls
                })

        logger.debug(f"MessageProcessor.get_formatted_messages: {len(formatted_messages)} messages returned")
        return formatted_messages

    def _save_debug_traffic(self) -> None:
        """Save the debug message traffic to a JSON file"""
        if not self.is_debug_mode:
            return
            
        try:
            with open(self.debug_history_file, "w", encoding="utf-8") as f:
                json.dump({
                    "session_start": self.session_start_time,
                    "debug_traffic": self.get_formatted_messages()
                }, f, indent=2)
                
            logger.debug(f"MessageProcessor._save_debug_traffic: Debug traffic saved to {self.debug_history_file}")
        except Exception as e:
            logger.error(f"MessageProcessor._save_debug_traffic: Failed to save debug traffic: {e}")
    
    def process(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process messages and return formatted messages for LLM API
        Args:
            messages: A list of messages to process
        Returns:
            Formatted messages for LLM API
        """
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            metadata = message.get("metadata", {})
            self.add_message(role, content, metadata)

        return self.get_formatted_messages()


class ToolProcessor:
    """Manages tool execution and formatting for LLM providers"""
    
    def __init__(self, session: Optional[ClientSession] = None):
        """Initialize the tool processor
        
        Args:
            session: MCP client session
        """
        self.session = session
        self.available_tools = []
        
        logger.debug(f"ToolProcessor.__init__: Initialized with session: {session is not None}")

    async def refresh_capabilities(self) -> None:
        """Refresh available tools from the MCP server"""
        if not self.session:
            logger.error("ToolProcessor.refresh_capabilities: No session available")
            raise UserVisibleError("No connected Mcp server session available, please check Mcp server connection")

        logger.debug(f"ToolProcessor.refresh_capabilities: Refreshing tools")
            
        # Get available tools
        try:
            tools_response = await self.session.list_tools()
            self.available_tools = tools_response.tools

            logger.debug(f"ToolProcessor.refresh_capabilities: Got {len(self.available_tools)} tools")
            for tool in self.available_tools:
                logger.debug(f"ToolProcessor.refresh_capabilities: Tool: {tool.name}")
        
        except Exception as e:
            logger.error(f"ToolProcessor.refresh_capabilities: Failed to refresh tools: {e}")
            self.available_tools = []

    def format_tools(self) -> List[Dict[str, Any]]:
        """Format tools for LLM consumption
        
        Returns:
            List of formatted tools
        """

        formatted_tools = []
        
        for tool in self.available_tools:
            formatted_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description
                }
            }
            # To ensure compatibility with Deepseek, when the parameter list is {}, it should be removed
            if tool.inputSchema:
                formatted_tool["function"]["parameters"] = tool.inputSchema
            formatted_tools.append(formatted_tool)

        logger.debug(f"ToolProcessor.format_tools: Return {len(formatted_tools)} Formatted tools")
        return formatted_tools

    async def execute_tool_call_async(self, tool_call: Dict[str, Any]) -> str:
        """Execute a tool call asynchronously
        
        Args:
            tool_call: The tool call to execute
            
        Returns:
            The result of the tool execution
        """
        if not self.session:
            logger.error("ToolProcessor.execute_tool_call_async: No session available to execute tool call")
            raise UserVisibleError("No connected Mcp server session available, please check Mcp server connection")
        
        # Extract the tool name and arguments
        tool_name = tool_call.get("function", {}).get("name") if "function" in tool_call else tool_call.get("name")
        args_json = tool_call.get("function", {}).get("arguments") if "function" in tool_call else tool_call.get("arguments")
        
        if not tool_name:
            error = "Invalid tool call format: missing function name"
            logger.error(f"ToolProcessor.execute_tool_call_async: {error}")
            return error
            
        # Parse arguments
        if isinstance(args_json, str):
            try:
                args = json.loads(args_json)
            except json.JSONDecodeError:
                error = f"Invalid JSON in tool arguments: {args_json}"
                logger.error(f"ToolProcessor.execute_tool_call_async: {error}")
                return error
        else:
            args = args_json or {}
        
        logger.info(f"ToolProcessor.execute_tool_call_async: Executing tool name: {tool_name}")
        logger.info(f"ToolProcessor.execute_tool_call_async: Executing tool with args: {args}")

        # Execute the tool
        try:
            start_time = time.time()
            tool_result = await self.session.call_tool(tool_name, dict(args))
            end_time = time.time()
            result = tool_result.content[0].text

            logger.info(f"ToolProcessor.execute_tool_call_async: Executed tool result: {tool_result}")
            logger.debug(f"ToolProcessor.execute_tool_call_async: Tool executed in {end_time - start_time:.2f}s")
            
            return result

        except Exception as e:
            error = f"Error executing tool {tool_name}: {str(e)}"
            logger.error(f"ToolProcessor.execute_tool_call_async: Error executing tool {tool_name}: {str(e)}")
            return error


class PromptProcessor:
    """Processor for generating system prompts with optional tool information."""
    
    def __init__(self):
        """Initialize the prompt processor"""

        # Default user system prompt
        self.default_user_prompt = (
            DEFAULT_SYSTEM_PROMPT
        )
        
        logger.debug(f"PromptProcessor.__init__: Initialized with default system prompt, {self.default_user_prompt}")

    async def format_prompts(self, session):
        """Format the prompts for the MCP server"""
        prompts = []
        available_prompts = await session.list_prompts()
        logger.debug(f"PromptProcessor.format_prompts: Available prompts: {available_prompts}")
        for prompt in available_prompts.prompts:
            prompt_result = await session.get_prompt(prompt.name, prompt.arguments if prompt.arguments else {})
            formatted_prompt = {
                "name": prompt.name,
                "description": prompt_result.description,
                "messages": [{
                    "role": msg.role,
                    "content": msg.content.text
                } for msg in prompt_result.messages]
            }
            prompts.append(formatted_prompt)
        return prompts

    def generate_system_prompt(self, additional_prompt: Optional[str] = None) -> str:
        """Generate a complete system prompt
        
        Args:
            additional_prompt: Optional custom user prompt to add to the default system prompt
            
        Returns:
            A formatted system prompt
        """
        prompt = self.default_user_prompt
        if additional_prompt: prompt += "\n\n" + additional_prompt
        
        logger.info(f"PromptProcessor.generate_system_prompt: Generated system prompt with {len(prompt)} characters")
        logger.debug(f"PromptProcessor.generate_system_prompt: Generated system prompt: {prompt}")
        return prompt


# Export the classes for easy importing
__all__ = ['MessageProcessor', 'ToolProcessor', 'PromptProcessor'] 