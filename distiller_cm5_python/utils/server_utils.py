import os
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def extract_server_name(server_script_path: str) -> str:
    """
    Extract a meaningful server name from a server script path.

    This function uses multiple strategies to extract the best possible name:
    1. Try to extract SERVER_NAME constant from the script
    2. Fall back to extracting from the filename using naming conventions
    3. Return a default if all else fails

    Args:
        server_script_path: Path to the server script file

    Returns:
        A human-friendly server name
    """
    if not server_script_path or not os.path.exists(server_script_path):
        logger.warning(f"Invalid server script path: {server_script_path}")
        return "Unknown Server"

    # Strategy 1: Extract SERVER_NAME constant from the script
    try:
        with open(server_script_path, "r") as f:
            content = f.read(2000)  # Read only first 2000 chars to avoid large files
            # Use regex to find SERVER_NAME variable with proper string assignment
            match = re.search(r'SERVER_NAME\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                extracted_name = match.group(1).strip()
                if extracted_name:
                    logger.debug(f"Extracted server name from script constant: {extracted_name}")
                    return extracted_name
    except Exception as e:
        logger.warning(f"Failed to read server script for name extraction: {e}")

    # Strategy 2: Extract from filename
    try:
        # Get the base filename
        filename = os.path.basename(server_script_path)

        # Remove extension
        if filename.endswith(".py"):
            filename = filename[:-3]

        # Handle common naming patterns
        if filename.endswith("_server"):
            filename = filename[:-7]
        elif filename.startswith("server_"):
            filename = filename[7:]

        # Convert to title case with spaces
        name = filename.replace("_", " ").title()

        if name:
            logger.debug(f"Extracted server name from filename: {name}")
            return name
    except Exception as e:
        logger.warning(f"Failed to extract server name from filename: {e}")

    # Strategy 3: Default fallback
    return "MCP Server"
