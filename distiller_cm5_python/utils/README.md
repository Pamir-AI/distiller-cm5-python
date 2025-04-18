# Utilities (`utils`)

This directory contains shared utility modules and configuration files used across different components of the MCP project (e.g., client, servers).

## Modules

- **`config.py`**:
    - Provides a centralized `Config` class (singleton) for managing application settings.
    - Loads configuration in the following order of precedence (lowest to highest):
        1. Defaults from `default_config.json`.
        2. User-defined configuration file (path specified by `MCP_CONFIG_FILE` env var, defaults to `mcp_config.json` in the runtime directory).
        3. Environment variables (e.g., `LLM_MODEL`, `LOG_LEVEL`).
    - Exports commonly used configuration parameters directly (e.g., `SERVER_URL`, `MODEL_NAME`, `LOGGING_LEVEL`).
- **`logger.py`**:
    - Sets up a standardized console logger instance named `mcp`.
    - Configures log formatting and level (defaulting to INFO, controllable via `LOG_LEVEL` in config or `setup_logging` function).
    - Quiets excessive logging from libraries like `httpx` and `asyncio`.

## Configuration Files

- **`default_config.json`**: Contains the base default configuration values for the application, particularly for the client and LLM interactions.
- **`speak_config.json`**: Likely contains specific configuration settings related to a 'speak' tool or functionality, potentially used by one of the MCP servers (e.g., `speaker_server.py`).

## Usage

Modules in this directory are typically imported by other components:

```python
# Example importing config values and logger
from utils.config import MODEL_NAME, TIMEOUT
from utils.logger import logger

logger.info(f"Using model: {MODEL_NAME}")
# ... use TIMEOUT ...
``` 