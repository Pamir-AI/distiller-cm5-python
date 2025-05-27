import os
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def extract_server_name(active_server_name: str) -> str:
    """
    Derives a user-friendly server name from a given internal server identifier.

    This function applies a series of heuristics to convert a raw server name
    (typically a script filename or identifier) into a readable label:

    1. Removes common prefixes/suffixes such as 'server_' or '_server'.
    2. Converts underscores to spaces and capitalizes each word.
    3. Falls back to a default name if processing fails.

    Args:
        active_server_name: The raw server name, usually derived from a script or config.

    Returns:
        A cleaned and human-readable server name string.
    """


    # Strategy 2: Extract from filename
    try:

        # Handle common naming patterns
        if active_server_name.endswith("_server"):
            active_server_name = active_server_name[:-7]
        elif active_server_name.startswith("server_"):
            active_server_name = active_server_name[7:]

        # Convert to title case with spaces
        name = active_server_name.replace("_", " ").title()

        if name:
            logger.debug(f"Extracted server name from active mcp server: {name}")
            return name
    except Exception as e:
        logger.warning(f"Failed to extract server name from filename: {e}")

    # Strategy 3: Default fallback
    return "MCP Server"
