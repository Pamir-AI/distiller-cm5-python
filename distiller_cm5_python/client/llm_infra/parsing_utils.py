"""
Utility functions for parsing LLM responses and related strings.
"""

import re
import json
import logging
from typing import Optional, List, Dict, Any

# Assuming utils is accessible from the project root
# Removed direct logger import: from distiller_cm5_python.utils.logger import logger

# Get logger instance for this module
logger = logging.getLogger(__name__)


def normalize_tool_call_json(tool_call_str: str) -> str:
    """Attempt to fix common JSON issues in tool call strings."""
    if not isinstance(tool_call_str, str):
        return tool_call_str  # Should not happen

    logger.debug(f"Original tool call string: '{tool_call_str}'")

    # First strip all surrounding whitespace including newlines
    tool_call_str = tool_call_str.strip()
    logger.debug(f"After initial strip: '{tool_call_str}'")

    # Remove markdown ```json ... ``` tags
    tool_call_str = re.sub(r"^```json\s*", "", tool_call_str, flags=re.IGNORECASE)
    tool_call_str = re.sub(r"\s*```$", "", tool_call_str)
    tool_call_str = tool_call_str.strip()  # Strip again after removing markdown
    logger.debug(f"After markdown removal: '{tool_call_str}'")

    # Fix unbalanced braces
    open_braces = tool_call_str.count("{")
    close_braces = tool_call_str.count("}")
    if open_braces > close_braces:
        tool_call_str += "}" * (open_braces - close_braces)
    logger.debug(f"After fixing unbalanced braces: '{tool_call_str}'")

    # Handle double curly braces {{...}} -> {...}
    if tool_call_str.startswith("{{") and tool_call_str.endswith("}}"):
        # Be careful not to strip braces from nested valid JSON
        try:
            # Try parsing the inner part
            inner_content = tool_call_str[
                1:-1
            ].strip()  # Strip any whitespace after removing braces
            logger.debug(f"Attempting to parse inner content: '{inner_content}'")
            logger.debug(f"Attempting to parse inner content (repr): {repr(inner_content)}")
            json.loads(inner_content)
            # If inner parse succeeds, assume the outer braces were extra
            tool_call_str = inner_content
            logger.debug(
                f"Successfully normalized double curly braces: '{tool_call_str}'"
            )
        except json.JSONDecodeError as e:
            logger.warning(f"JSONDecodeError for inner_content: {e}. Inner content was (repr): {repr(inner_content)}")
            # If inner parse fails, try removing both sets of braces
            if tool_call_str.count("{") == 2 and tool_call_str.count("}") == 2:
                inner_content = tool_call_str[
                    2:-2
                ].strip()  # Remove both sets of braces
                try:
                    json.loads(inner_content)
                    tool_call_str = inner_content
                    logger.debug(
                        f"Successfully removed both sets of braces: '{tool_call_str}'"
                    )
                except json.JSONDecodeError:
                    logger.debug(
                        f"Failed to parse after removing both sets of braces, leaving as is: '{tool_call_str}'"
                    )
            else:
                logger.debug(
                    f"Found double curly braces, but content is not valid JSON: '{tool_call_str}'"
                )

    logger.debug(f"Final normalized string: '{tool_call_str}'")
    return tool_call_str


def parse_tool_calls(text: str) -> List[Dict[str, Any]]:
    """Parses <tool_call>...</tool_call> blocks from model response text.

    Args:
        text: Raw response text from the model.

    Returns:
        List of parsed tool calls in OpenAI-compatible format, or empty list if none found/parsed.
    """
    tool_calls = []
    if not text or "<tool_call>" not in text:
        return tool_calls

    # Regex to find content within <tool_call>...</tool_call>
    pattern = r"<tool_call>(.*?)</tool_call>"
    matches = re.findall(pattern, text, re.DOTALL)

    logger.debug(f"Found {len(matches)} potential tool call blocks in text.")

    for i, tool_call_content in enumerate(matches):
        original_content_for_log = tool_call_content[:200]  # Log snippet
        try:
            # Normalize the extracted content (remove ```json, fix common issues)
            normalized_content = normalize_tool_call_json(tool_call_content)

            # Attempt to parse the normalized JSON
            tool_call_data = json.loads(normalized_content)

            # Validate the basic structure (needs 'name' and 'arguments')
            if (
                not isinstance(tool_call_data, dict)
                or "name" not in tool_call_data
                or "arguments" not in tool_call_data
            ):
                raise ValueError(
                    "Parsed JSON missing required 'name' or 'arguments' fields."
                )

            # Ensure arguments are dumped back to a string for the final format,
            # even if they were parsed from a string initially.
            arguments_value = tool_call_data["arguments"]
            if isinstance(arguments_value, dict):
                arguments_str = json.dumps(arguments_value)
            elif isinstance(arguments_value, str):
                # If it's already a string, try to validate if it's JSON, but keep as string
                try:
                    json.loads(arguments_value)
                    arguments_str = arguments_value  # Keep valid JSON string
                except json.JSONDecodeError:
                    # Truncate potentially sensitive argument value in log
                    log_arg_snippet = arguments_value[:100] + (
                        "..." if len(arguments_value) > 100 else ""
                    )
                    logger.warning(
                        f"Tool call arguments for '{tool_call_data['name']}' is a string but not valid JSON: '{log_arg_snippet}'. Keeping as string."
                    )
                    arguments_str = (
                        arguments_value  # Keep non-JSON string as is? Or error?
                    )
            else:
                # Handle other types (int, list etc.) by converting to string representation?
                logger.warning(
                    f"Tool call arguments for '{tool_call_data['name']}' is of unexpected type {type(arguments_value)}. Converting to string."
                )
                arguments_str = str(arguments_value)

            # Format into OpenAI-compatible structure
            # Generate a unique-ish ID based on index or content hash? For now, use name + index.
            tool_call_id = f"call_{tool_call_data['name']}_{i}"

            formatted_tool_call = {
                "id": tool_call_id,
                "type": "function",  # Assuming all are function calls
                "function": {
                    "name": tool_call_data["name"],
                    "arguments": arguments_str,
                },
            }
            tool_calls.append(formatted_tool_call)
            logger.debug(
                f"parse_tool_calls: Successfully parsed tool call {i}: {formatted_tool_call}"
            )

        except json.JSONDecodeError as e:
            logger.error(
                f"parse_tool_calls: Failed JSON parsing for tool call {i}. Error: {e}. Content snippet: '{original_content_for_log}...'",
                exc_info=True,
            )
            # Continue to next match
        except ValueError as e:
            logger.error(
                f"parse_tool_calls: Invalid structure for tool call {i}. Error: {e}. Content snippet: '{original_content_for_log}...'",
                exc_info=True,
            )
            # Continue to next match
        except Exception as e:
            logger.error(
                f"parse_tool_calls: Unexpected error processing tool call {i}: {e}. Content snippet: '{original_content_for_log}...'",
                exc_info=True,
            )
            # Continue to next match

    if tool_calls:
        logger.info(
            f"Successfully parsed {len(tool_calls)} tool calls from response text."
        )
    return tool_calls


def check_is_c_ntx_too_long(error_text: str) -> Optional[tuple[int, int]]:
    """Parse llama-cpp specific context window error."""
    if not isinstance(error_text, str):
        return None
    # Original regex: r'Error creating chat completion: Requested tokens \((\d+)\) exceed context window of (\d+)'
    # Make it slightly more general if needed
    pattern = r"Requested tokens? \((\d+)\) exceed(?:s)? context window of (\d+)"
    match = re.search(pattern, error_text)  # Use search instead of fullmatch
    if match:
        requested_tokens = int(match.group(1))
        context_window = int(match.group(2))
        logger.warning(
            f"Detected context length error: Requested={requested_tokens}, Max={context_window}"
        )
        return requested_tokens, context_window
    return None
