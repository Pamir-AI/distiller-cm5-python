"""
Processing layer for MCP client.
This file combines message, tool and prompt processors into a single module.
"""

import time
import json
import logging
from mcp import ClientSession
from datetime import datetime
from typing import List, Dict, Any, Union, Optional, Coroutine, Literal, Tuple

from pydantic import BaseModel, field_validator, model_validator

from distiller_cm5_python.utils.config import (
    MAX_MESSAGES_LENGTH,
    DEFAULT_SYSTEM_PROMPT,
    LOGGING_LEVEL,
)
from distiller_cm5_python.utils.distiller_exception import (
    UserVisibleError,
    LogOnlyError,
)

# Get logger instance for this module
logger = logging.getLogger(__name__)


def timestamp_to_time(timestamp):
    dt_object = datetime.fromtimestamp(timestamp)
    formatted_time = dt_object.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time


# --- Pydantic Models for Message Structure ---

DEFAULT_SYSTEM_MESSAGE = ''

ROLE = 'role'
CONTENT = 'content'
REASONING_CONTENT = 'reasoning_content'
NAME = 'name'

SYSTEM = 'system'
USER = 'user'
ASSISTANT = 'assistant'
TOOL = 'tool' # API role for tool results

# Content Types (for potential future multi-modal use)
TEXT = 'text'
FILE = 'file'
IMAGE = 'image'
AUDIO = 'audio'
VIDEO = 'video'


class BaseModelCompatibleDict(BaseModel):
    """ Base model providing dictionary-like access and serialization control. """
    def __getitem__(self, item):
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def model_dump(self, **kwargs):
        if 'exclude_none' not in kwargs:
            kwargs['exclude_none'] = True
        dumped_data = super().model_dump(**kwargs)
        return dumped_data

    def model_dump_json(self, **kwargs):
        if 'exclude_none' not in kwargs:
            kwargs['exclude_none'] = True
        # Use the custom model_dump logic
        dict_repr = self.model_dump(**kwargs)
        return json.dumps(dict_repr, **kwargs)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __str__(self):
        # Exclude 'extra' from string representation for brevity if empty
        dump = self.model_dump()
        # Clean up extra field for printing
        if 'extra' in dump:
            if not dump['extra']:
                del dump['extra']
            # Avoid printing potentially large args in tool_calls within extra
            elif 'tool_calls' in dump['extra']:
                 dump['extra'] = {**dump['extra'], 'tool_calls': '[present]'}

        return f'{self.__class__.__name__}({dump})'

    def __repr__(self):
        return self.__str__()

    class Config:
        # Allow extra fields to be stored but not validated (useful for 'extra')
        extra = 'allow'


class Message(BaseModelCompatibleDict):
    """ Represents a single message in the conversation history using Pydantic. """
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None # Flexible field for additional metadata

    def __init__(self,
                 role: str,
                 content: str,
                 name: Optional[str] = None,
                 tool_calls: Optional[List[Dict[str, Any]]] = None,
                 tool_call_id: Optional[str] = None,
                 extra: Optional[Dict[str, Any]] = None,
                 **kwargs): # Allow capturing other potential fields into extra

        # Consolidate extra fields passed via kwargs
        if kwargs:
            if extra is None:
                extra = {}
            extra.update(kwargs)

        super().__init__(role=role,
                         content=content,
                         name=name,
                         tool_calls=tool_calls,
                         tool_call_id=tool_call_id,
                         extra=extra)

    @field_validator('role')
    def role_checker(cls, value: str) -> str:
        # Allow 'tool' initially for easier transition from old format, map later if needed
        allowed_roles = [USER, ASSISTANT, SYSTEM, TOOL]
        if value not in allowed_roles:
            raise ValueError(f"Role '{value}' must be one of {', '.join(allowed_roles)}")
        return value

    
    @model_validator(mode='after')
    def check_role_specific_fields(self):
        # Tool calls should only exist for assistant messages
        if self.role != ASSISTANT and self.tool_calls is not None:
            raise ValueError(f"'tool_calls' field is only applicable for role '{ASSISTANT}'. Role is '{self.role}'.")

        # Tool call ID should only exist for function/tool messages
        if self.role != TOOL and self.tool_call_id is not None:
             raise ValueError(f"'tool_call_id' field is only applicable for role '{TOOL}'.")

        # Function/tool messages must have a tool_call_id
        if self.role == TOOL and self.tool_call_id is None:
            raise ValueError(f"Messages with role '{TOOL}' must have a 'tool_call_id'.")

        # Assistant messages with tool_calls might have None or empty string content
        if self.role == ASSISTANT and self.tool_calls:
            if self.content is not None and not isinstance(self.content, (str, list)):
                 # This case should ideally be caught by content_validator, but double-checking
                 raise ValueError("Assistant message content must be string, list, or None.")
        elif self.content is None and self.role != ASSISTANT: # Only assistant can have None content (with tool calls)
             raise ValueError(f"Message content cannot be None for role '{self.role}'.")

        return self

# --- End Pydantic Models ---


class MessageProcessor:
    """Processor for managing conversation history and formatting messages for LLM providers."""

    def __init__(self):
        """Initialize the message processor"""
        super().__init__()  # No verbose parameter needed

        self.message_history: List[Message] = [] # Use Pydantic Message model
        self.session_start_time = timestamp_to_time(time.time()).replace(":", "-")

        # Check config for enabling debug message traffic dump
        self.save_debug_traffic = LOGGING_LEVEL == "DEBUG"
        self.debug_history_file = (
            f"debug_message_traffic_{self.session_start_time}.json"
        )

        logger.debug(
            f"MessageProcessor.__init__: Initialized with {'Enabled' if self.save_debug_traffic else 'Disabled'} mode"
        )

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None, # Raw tool calls for assistant
        tool_call_id: Optional[str] = None, # ID for tool results
    ) -> None:
        """Add a message to the conversation history using the Message model.

        Args:
            role: The role of the message sender (user, assistant, system, tool)
            content: The content of the message (string, list of ContentItems, or None)
            metadata: Optional metadata for the message (stored in 'extra')
            tool_calls: Raw tool call dictionaries (for assistant role only)
            tool_call_id: ID corresponding to the tool call (for tool role only)
        """

        # Control message length
        if len(self.message_history) >= MAX_MESSAGES_LENGTH:
            logger.warning(
                f"MessageProcessor.add_message: Message history is full. Removing oldest message."
            )
            # Traverse the list from the beginning, find the first message that is not of the 'system' role
            for i, msg in enumerate(self.message_history):
                if msg.role != SYSTEM:
                    # Delete the first non-system role message
                    del self.message_history[i]
                    break

        try:
            # Create and append the Pydantic Message object.
            # Pydantic validators within the Message model will handle role-specific field checks
            # (e.g., tool_calls for ASSISTANT, tool_call_id for TOOL).
            new_message = Message(
                role=role,
                content=content if content else "",
                tool_calls=tool_calls,
                tool_call_id=tool_call_id,
                extra=metadata # Pass metadata dict (or None) as extra
            )
            self.message_history.append(new_message)
        except (ValueError, TypeError) as e: # Catch Pydantic validation errors or TypeErrors
            logger.error(f"MessageProcessor.add_message: Failed to create Message object. Role: '{role}', Content snippet: '{str(content)[:50]}...', Error: {e}")
            # Encapsulate as a LogOnlyError to prevent verbose user-facing errors for internal validation issues
            raise LogOnlyError(f"Internal error processing message for role '{role}': {e}")
        
        finally:
            # This will be executed even if an early return happens (e.g., for TOOL role)
            # or if LogOnlyError is raised from the Message creation.
            if self.save_debug_traffic:
                self._save_debug_traffic()

    def set_system_message(self, content: str, metadata: Dict[str, Any] = None) -> None:
        """Set or replace the system message in the conversation history

        This method removes any existing system messages and adds a new one.

        Args:
            content: The content of the system message
            metadata: Optional metadata for the message
        """
        # Remove any existing system messages
        self.message_history = [
            msg for msg in self.message_history if msg.role != SYSTEM
        ]

        # Add the new system message
        metadata = metadata or {}
        if self.save_debug_traffic:
            metadata["message_type"] = "system_message_set"

        self.add_message(SYSTEM, content, metadata)

        logger.debug(
            f"MessageProcessor.set_system_message: System message set: {str(content)[:50]}..."
        )

    def add_tool_call(self, tool_call_input: Dict[str, Any]) -> None:
        """Add an assistant message representing a tool call to the history.

        Args:
            tool_call_input: The raw tool call dictionary.
        """
        try:
            tool_name = (
                tool_call_input.get("function", {}).get("name", "")
                if "function" in tool_call_input
                else tool_call_input.get("name", "")
            )
            tool_args_raw = (
                tool_call_input.get("function", {}).get("arguments", {})
                if "function" in tool_call_input
                else tool_call_input.get("arguments", {})
            )
            # Use 'id' from input; fallback to tool_name if 'id' is not present.
            # The LLM response should provide an 'id' for each tool_call.
            tool_call_id = tool_call_input.get("id", tool_name)

            # Ensure the last message is an ASSISTANT message suitable for appending tool calls.
            # If not, or if it already has content, add a new ASSISTANT message.
            if not self.message_history or self.message_history[-1].role != ASSISTANT or (self.message_history[-1].role == ASSISTANT and self.message_history[-1].content != ""):
                # The Message model initializes tool_calls to None if not provided.
                self.add_message(role=ASSISTANT, content="", tool_calls=[]) # Initialize with empty list
            
            assistant_message = self.message_history[-1] # Get the (potentially new) last message

            # Ensure tool_calls list exists on the assistant_message Pydantic model
            if assistant_message.tool_calls is None:
                assistant_message.tool_calls = []

            # Append the new tool call (as a dictionary) to the assistant_message's tool_calls list.
            # The structure here matches what the OpenAI API expects.
            assistant_message.tool_calls.append(
                {
                    "id": tool_call_id,
                    "type": "function", # Standard type for tool calls
                    "function": {"name": tool_name, "arguments": tool_args_raw},
                }
            )

        finally:
            if self.save_debug_traffic:
                self._save_debug_traffic()

    def add_tool_result(self, tool_call: Dict[str, Any], result: str) -> None:
        """Add a tool result message to the history. Returns None."""

        tool_name = (
            tool_call.get("function", {}).get("name", "")
            if "function" in tool_call
            else tool_call.get("name", "")
        )
        tool_args = (
            tool_call.get("function", {}).get("arguments", {})
            if "function" in tool_call
            else tool_call.get("arguments", {})
        )
        tool_call_id = tool_call.get("id", tool_name)

        metadata = {
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "tool_args": tool_args,
            "is_tool_result": True,
            "message_type": "tool_result",
        }

        self.add_message(role=TOOL, content=result, tool_call_id=tool_call_id, metadata=metadata)

        # If debug traffic dump is enabled, track detailed message traffic
        if self.save_debug_traffic:
            self._save_debug_traffic()

        logger.debug(
            f"MessageProcessor.add_tool_result: Added result for '{tool_name}'. Content: '{result}'"
        )

        # Return None as the event is not used by the caller
        return None

    def add_failed_tool_gen(
        self, original_snippet: str, tool_call_dict: Dict[str, Any], error_details_str: str
    ) -> None:
        """Add a message indicating a failure during LLM tool call generation/parsing."""
        tool_call_id = tool_call_dict.get("id", "unknown_gen_failure_id")
        tool_name = tool_call_dict.get("function", {}).get(
            "name", "__llm_tool_parse_error__"
        ) # Default to the special name

        metadata = {
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "is_tool_result": True, # Still a result, albeit an error one
            "is_generation_failure": True,
            "message_type": "tool_generation_failure",
        }

        # Add the failed assistant message
        self.add_message(
            role=ASSISTANT,
            content=f"<tool_call>{original_snippet}</tool_call>",
            tool_calls=[]
        )

        # add error output message
        self.add_message(
            role=TOOL,
            content=error_details_str,
            tool_call_id=tool_call_id,
        )
        logger.warning(
            f"MessageProcessor.add_failed_tool_gen: Added generation failure for tool_id '{tool_call_id}'. Error: '{error_details_str}'"
        )
        # No return needed, similar to add_tool_result

    def add_failed_tool_execute(
        self, attempted_tool_call_dict: Dict[str, Any], execution_error_str: str
    ) -> None:
        """Add a message indicating a failure during tool execution."""
        tool_call_id = attempted_tool_call_dict.get("id", "unknown_exec_failure_id")
        tool_name = attempted_tool_call_dict.get("function", {}).get(
            "name", "unknown_tool"
        )
        tool_args = attempted_tool_call_dict.get("function", {}).get("arguments", {})

        metadata = {
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "tool_args": tool_args, # Include args for execution failures
            "is_tool_result": True,
            "is_execution_failure": True,
            "message_type": "tool_execution_failure",
        }

        self.add_message(
            role=TOOL,
            content=execution_error_str,
            tool_call_id=tool_call_id,
            metadata=metadata,
        )
        logger.warning(
            f"MessageProcessor.add_failed_tool_execute: Added execution failure for tool '{tool_name}' (id: '{tool_call_id}'). Error: '{execution_error_str}'"
        )
        # No return needed

    def get_formatted_messages(
        self,
    ) -> List[Dict[str, Union[str, List[Dict[str, Any]]]]]:
        """Get the message history formatted for LLM API, using Pydantic model_dump.

        Returns:
            List of formatted messages suitable for the API.
        """

        formatted_messages = []

        for message in self.message_history:
            # Ensure that message is a Pydantic Message object
            if not isinstance(message, Message):
                logger.warning(f"Skipping non-Message object in history: {type(message)}")
                continue

            role = message.role

            if role == TOOL:
                # Tool messages have a specific format required by APIs.
                # The tool_call_id should be directly on the Message object.
                if message.tool_call_id:
                    formatted_messages.append(
                        {
                            "role": TOOL,
                            "tool_call_id": message.tool_call_id,
                            "content": message.content, # Content is the string result
                        }
                    )
                else:
                    # This case should ideally not happen if add_tool_result ensures tool_call_id
                    logger.warning(
                        f"Tool message found without a tool_call_id. Content: {str(message.content)[:50]}... This message will be skipped in formatted output."
                    )
            elif role == ASSISTANT:
                # Assistant messages can have content, tool_calls, or both (content can be None).
                # We use model_dump to get the relevant fields.
                # exclude_none=True is important if content is None but tool_calls are present.
                if message.tool_calls:
                    msg_dict = message.model_dump(
                        include={'role', 'content', 'tool_calls'},
                        exclude_none=True
                    )
                else:
                    msg_dict = message.model_dump(include={'role', 'content'})
                formatted_messages.append(msg_dict)

            elif role in [USER, SYSTEM]:
                # User and System messages typically only have role and content.
                msg_dict = message.model_dump(include={'role', 'content'})
                formatted_messages.append(msg_dict)
            else:
                logger.warning(f"Unhandled message role '{role}' during formatting. Skipping message.")
        
        logger.debug(
            f"MessageProcessor.get_formatted_messages: {len(formatted_messages)} messages returned"
        )
        return formatted_messages

    def _save_debug_traffic(self) -> None:
        """Save the debug message traffic to a JSON file"""
        # This method is now only called if self.save_debug_traffic is True
        if not self.save_debug_traffic:
            # This warning should not occur due to the finally blocks
            logger.warning("_save_debug_traffic called unexpectedly when disabled.")
            return

        try:
            # Get the messages formatted exactly as they would be sent to the API
            api_formatted_messages = self.get_formatted_messages()

            debug_data = {
                "session_start": self.session_start_time,
                "debug_traffic_api_format": api_formatted_messages, # Just save the API format
            }

            with open(self.debug_history_file, "w", encoding="utf-8") as f:
                # Dump the API-formatted data
                json.dump(debug_data, f, indent=2, default=str) # default=str for safety

            logger.debug(
                f"MessageProcessor._save_debug_traffic: Debug traffic saved to {self.debug_history_file}"
            )
        except Exception as e:
            # Catch any general exception during formatting or dumping
            logger.error(f"MessageProcessor._save_debug_traffic: Failed to save debug traffic: {e}")
            # Log the data we attempted to dump if possible
            if 'api_formatted_messages' in locals():
                try:
                    import pprint
                    logger.error(f"Data attempted to dump:\n{pprint.pformat(api_formatted_messages)}")
                except Exception as log_e:
                     logger.error(f"Could not log the data structure due to: {log_e}")

    def process(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process messages and return formatted messages for LLM API
        Args:
            messages: A list of messages to process
        Returns:
            Formatted messages for LLM API
        """
        # This method takes raw input messages (dicts), processes them into internal
        # Pydantic Message objects, and returns the API-ready formatted list.
        for message_dict in messages:
            # Extract data from the input dictionary
            role = message_dict.get("role", USER) # Default to USER if role missing
            content = message_dict.get("content", None) # Allow None content for input
            metadata = message_dict.get("metadata", {})
            # Potentially extract tool_calls or tool_call_id if they can appear in raw input
            raw_tool_calls = message_dict.get("tool_calls")
            tool_call_id = message_dict.get("tool_call_id") # Relevant if input can contain tool results

            # Use add_message to convert dict to internal Pydantic Message object and add to history
            try:
                self.add_message(
                    role=role,\
                    content=content,\
                    metadata=metadata,\
                    tool_calls=raw_tool_calls, # Pass raw tool calls if present
                    tool_call_id=tool_call_id  # Pass tool_call_id if present
                )
            except Exception as e:
                 logger.error(f"Error processing input message dict: {message_dict}. Error: {e}")
                 # Decide whether to skip this message or raise error
                 continue

        # Return the messages formatted for the API call
        return self.get_formatted_messages()


class ToolProcessor:
    """Manages tool execution and formatting for LLM providers"""

    def __init__(self, session: Optional[ClientSession] = None):
        """Initialize the tool processor

        Args:
            session: MCP client session
        """
        self.session = session
        self.tools = []

        logger.debug(
            f"ToolProcessor.__init__: Initialized with session: {session is not None}"
        )

    async def refresh_capabilities(self) -> None:
        """Refresh available tools from the MCP server"""
        if not self.session:
            logger.error("ToolProcessor.refresh_capabilities: No session available")
            raise UserVisibleError(
                "No connected Mcp server session available, please check Mcp server connection"
            )

        logger.debug(f"ToolProcessor.refresh_capabilities: Refreshing tools")

        # Get available tools
        try:
            tools_response = await self.session.list_tools()
            self.tools = tools_response.tools

            logger.debug(
                f"ToolProcessor.refresh_capabilities: Got {len(self.tools)} tools"
            )
            for tool in self.tools:
                logger.debug(f"ToolProcessor.refresh_capabilities: Tool: {tool.name}")

        except Exception as e:
            logger.error(
                f"ToolProcessor.refresh_capabilities: Failed to refresh tools: {e}"
            )
            self.tools = []

    def format_tools(self) -> List[Dict[str, Any]]:
        """Format all available tools from server into the shape expected by LLM models"""
        if not self.session or not hasattr(self, "tools") or not self.tools:
            return []

        formatted_tools = []

        for tool in self.tools:
            # Check if tool is a dictionary or an object with attributes
            if isinstance(tool, dict):
                name = tool.get("name", "")
                description = tool.get("description", "")
                parameters = tool.get("inputSchema", {})
            else:
                # Assume it's an object with attributes
                name = getattr(tool, "name", "")
                description = getattr(tool, "description", "")
                parameters = getattr(tool, "inputSchema", {})

            formatted_tool = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters,
                },
            }
            formatted_tools.append(formatted_tool)

        logger.debug(
            f"ToolProcessor.format_tools: Return {len(formatted_tools)} formatted tools"
        )
        return formatted_tools

    async def execute_tool_call_async(self, tool_call: Dict[str, Any]) -> str:
        """Execute the tool call asynchronously

        Args:
            tool_call: The tool call to execute

        Returns:
            The result of the tool execution
        """
        if not self.session:
            logger.error(
                "ToolProcessor.execute_tool_call_async: No MCP session available"
            )
            return json.dumps({"error": "MCP session not available"})

        tool_name = tool_call.get("function", {}).get("name", "")
        args = tool_call.get("function", {}).get("arguments", {})

        logger.debug(
            f"ToolProcessor.execute_tool_call_async: Executing {tool_name} with args: {args}"
        )

        try:
            # Call the tool via the MCP session
            result = (
                await self.session.call_tool(tool_name, args)
                if args
                else await self.session.call_tool(tool_name, None)
            )

            # Format the result for display
            formatted_result = self._format_tool_result(result)
            return formatted_result

        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {e}"
            logger.error(error_msg)
            return json.dumps({"error": f"Tool execution failed: {str(e)}"})

    def _format_tool_result(self, result) -> str:
        """Format a tool result into a string representation.

        Args:
            result: The result object returned from the MCP server

        Returns:
            A string representation of the result
        """
        # Check if result has a 'content' attribute that is a list (common MCP format)
        if hasattr(result, "content") and isinstance(result.content, list):
            result_text = []
            for item in result.content:
                # Handle TextContent objects or dicts with 'text' key
                if hasattr(item, "text"):
                    result_text.append(item.text)
                elif isinstance(item, dict) and "text" in item:
                    result_text.append(item["text"])
                else:
                    # Fallback for other item types within the content list
                    result_text.append(str(item))
            return "\n".join(result_text)

        # Handle if the result itself is a list
        elif isinstance(result, list):
            result_text = []
            for item in result:
                if isinstance(item, dict):
                    # Handle content object
                    content_type = item.get("type", "unknown")

                    if content_type == "text":
                        # Extract text content
                        text = item.get("text", "")
                        result_text.append(text)
                    elif "content" in item:
                        # Extract generic content
                        result_text.append(str(item["content"]))
                    else:
                        # Just extract whole item as string
                        result_text.append(str(item))
                else:
                    # Just add as string
                    result_text.append(str(item))

            # Join text items with newlines
            return "\n".join(result_text)
        elif isinstance(result, dict):
            # Try to extract content from dict
            if "text" in result:
                return result["text"]
            elif "content" in result:
                return str(result["content"])
            else:
                # Format as JSON
                import json

                try:
                    return json.dumps(result, indent=2)
                except:
                    return str(result)
        else:
            # Return as string
            return str(result)


class PromptProcessor:
    """Processor for generating system prompts with optional tool information."""

    def __init__(self):
        """Initialize the prompt processor"""

        # Default user system prompt
        self.default_user_prompt = DEFAULT_SYSTEM_PROMPT

        logger.debug(
            f"PromptProcessor.__init__: Initialized with default system prompt, {self.default_user_prompt}"
        )

    async def format_prompts(self, session):
        """Format the prompts for the MCP server"""
        prompts = []
        available_prompts = await session.list_prompts()
        logger.debug(
            f"PromptProcessor.format_prompts: Available prompts: {available_prompts}"
        )
        for prompt in available_prompts.prompts:
            prompt_result = await session.get_prompt(
                prompt.name, prompt.arguments if prompt.arguments else {}
            )
            formatted_prompt = {
                "name": prompt.name,
                "description": prompt_result.description,
                "messages": [
                    {"role": msg.role, "content": msg.content.text}
                    for msg in prompt_result.messages
                ],
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
        if additional_prompt:
            prompt += "\n\n" + additional_prompt

        logger.debug(
            f"PromptProcessor.generate_system_prompt: Generated system prompt: {prompt}"
        )
        return prompt


# Export the classes for easy importing
__all__ = ["MessageProcessor", "ToolProcessor", "PromptProcessor"]
