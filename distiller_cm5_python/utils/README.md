# Utilities (`utils`)

This directory contains shared utility modules and configuration files used across different components of the project (e.g., client, servers).

## Modules

- **`config.py`**:
    - Provides a centralized mechanism for managing application settings.
    - Loads configuration in the following order of precedence (lowest to highest):
        1. Defaults from `utils/default_config.toml`.
        2. User-defined configuration file (path specified by `MCP_CONFIG_FILE` env var, defaults to `mcp_config.toml` in the runtime directory).
        3. Environment variables (e.g., `LLM_MODEL`, `LOG_LEVEL`).
    - Exports commonly used configuration parameters directly (e.g., `SERVER_URL`, `MODEL_NAME`, `LOGGING_LEVEL`). Check the file for available constants.
- **`logger.py`**:
    - Provides a `setup_logging()` function to configure project-wide logging.
    - Sets up a standardized console logger with configurable formatting and level (controlled via `LOGGING_LEVEL` in config or function arguments).
    - Quiets excessive logging from libraries like `httpx` and `asyncio` by default.
- **`distiller_exception.py`**:
    - Defines custom exception classes for standardized error handling:
        - `LogOnlyError`: For exceptions that should be logged but might not require immediate user visibility.
        - `UserVisibleError`: For exceptions representing errors that should be directly reported to the user (e.g., configuration errors, critical failures).

## Configuration Files

- **`default_config.toml`**: Contains the base default configuration values used by `config.py` if no overrides are found in user config files or environment variables.

## Usage

Modules in this directory are typically imported by other components using their full path from the project root:

```python
# Example importing config values, logger setup, and custom exception
from distiller_cm5_python.utils.config import MODEL_NAME, TIMEOUT
from distiller_cm5_python.utils.logger import setup_logging, logger
from distiller_cm5_python.utils.distiller_exception import UserVisibleError

setup_logging() # Configure logging based on settings

try:
    logger.info(f"Using model: {MODEL_NAME}")
    # ... some operation that might fail ...
    if critical_error:
        raise UserVisibleError("Something went wrong that the user must know!")
except UserVisibleError as e:
    print(f"Error: {e}") # Show error to user
except Exception as e:
    logger.exception("An unexpected error occurred.") # Log other errors
``` 