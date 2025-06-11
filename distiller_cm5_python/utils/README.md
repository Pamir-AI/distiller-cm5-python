# Utilities (`utils`)

This directory contains shared utility modules and configuration files used across different components of the project (e.g., client, servers).

## Modules

### `config.py`
Provides a **multi-provider configuration system** with centralized settings management and environment variable overrides.

#### Key Features:
- **Multi-Provider Support**: Configure multiple LLM backends (llama-cpp, OpenRouter, etc.)
- **Active Provider Selection**: Use `active_llm_provider` to switch between configured providers
- **Configuration Hierarchy**: Environment variables > user config file > defaults
- **Singleton Pattern**: Ensures consistent configuration across the application
- **Type Conversion**: Automatically converts environment variables to appropriate types

#### Configuration Priority (highest to lowest):
1. **Environment Variables**: `LLM_SERVER_URL`, `LLM_MODEL_NAME`, `LOG_LEVEL`, etc.
2. **User Config File**: `mcp_config.json` (path configurable via `MCP_CONFIG_FILE` env var)
3. **Default Config**: `utils/default_config.json`

#### Provider Configuration Structure:
```json
{
  "llm_providers": {
    "llama-cpp": {
      "server_url": "http://127.0.0.1:8000",
      "model_name": "qwen2.5-3b-instruct-q4_k_m.gguf",
      "provider_type": "llama-cpp",
      "timeout": 150,
      "temperature": 0.7,
      "streaming": true
    },
    "openrouter": {
      "server_url": "https://openrouter.ai/api/v1",
      "model_name": "*",
      "provider_type": "openrouter", 
      "api_key": "sk-or-v1-*",
      "timeout": 60
    }
  },
  "active_llm_provider": "llama-cpp"
}
```

#### Environment Variable Overrides:
Environment variables automatically override the active provider's settings:
- `LLM_SERVER_URL`: Override server endpoint
- `LLM_MODEL_NAME`: Override model identifier
- `LLM_API_KEY`: Override authentication key
- `LLM_TEMPERATURE`: Override generation temperature
- `LLM_TOP_P`, `LLM_TOP_K`: Override sampling parameters
- `LLM_MAX_TOKENS`: Override maximum generation tokens
- `LLM_TIMEOUT`: Override request timeout
- `LOG_LEVEL`: Override logging level
- `MCP_CONFIG_FILE`: Custom config file path

### `logger.py`
Provides standardized logging setup with configurable formatting and levels.

#### Key Features:
- **Centralized Logging**: Single `setup_logging()` function for consistent configuration
- **Configurable Levels**: Controlled via `LOGGING_LEVEL` from config or function arguments
- **Library Quieting**: Automatically reduces verbosity of noisy libraries (`httpx`, `asyncio`, etc.)
- **Module-Specific Levels**: Special handling for server modules
- **Handler Management**: Prevents duplicate handlers when called multiple times

#### Standard Log Format:
```
%(asctime)s - %(name)s - %(module)s.%(funcName)s - %(levelname)s - %(message)s
```

#### Usage:
```python
from distiller_cm5_python.utils.logger import setup_logging
import logging

# Configure logging (typically done once at application start)
setup_logging()

# Get logger for your module
logger = logging.getLogger(__name__)
logger.info("Application started")
```

### `distiller_exception.py`
Defines custom exception classes for standardized error handling throughout the project.

#### Exception Classes:
- **`LogOnlyError`**: For exceptions that should be logged but might not require immediate user visibility
- **`UserVisibleError`**: For exceptions representing errors that should be directly reported to the user (e.g., configuration errors, critical failures)

## Configuration Files

### `default_config.json`
Contains the base default configuration values with multiple provider definitions. This file serves as the fallback configuration and documents all available settings.

#### Key Sections:
- **`llm_providers`**: Definitions for different LLM backends
- **`active_llm_provider`**: Currently selected provider
- **`mcp_server`**: MCP server configuration 
- **`logging`**: Logging preferences
- **`prompts`**: Default system prompts
- **`display`**: UI configuration

## Usage Examples

### Basic Configuration Access
```python
from distiller_cm5_python.utils.config import config, SERVER_URL, MODEL_NAME

# Access via global config instance
provider_name = config.get("active_llm_provider")
server_url = config.get("llm_providers", provider_name, "server_url")

# Access via convenience constants (from active provider)
print(f"Using server: {SERVER_URL}")
print(f"Using model: {MODEL_NAME}")
```

### Environment Variable Configuration
```bash
# Override active provider settings
export LLM_SERVER_URL="http://localhost:8001"
export LLM_MODEL_NAME="custom_model.gguf"
export LLM_TEMPERATURE="0.9"
export LOG_LEVEL="DEBUG"

# Use custom config file
export MCP_CONFIG_FILE="/path/to/custom_config.json"
```

### Complete Setup Example
```python
from distiller_cm5_python.utils.config import config, MODEL_NAME, TIMEOUT
from distiller_cm5_python.utils.logger import setup_logging
from distiller_cm5_python.utils.distiller_exception import UserVisibleError

# Configure logging based on settings
setup_logging()

# Get logger for this module
import logging
logger = logging.getLogger(__name__)

try:
    logger.info(f"Using model: {MODEL_NAME}")
    logger.info(f"Request timeout: {TIMEOUT}s")
    
    # Check configuration
    if not config.get("llm_providers", config.get("active_llm_provider")):
        raise UserVisibleError("Invalid LLM provider configuration")
        
except UserVisibleError as e:
    print(f"Configuration Error: {e}")
except Exception as e:
    logger.exception("Unexpected error during setup")
```

### Dynamic Configuration Changes
```python
# Change active provider at runtime
config.set("active_llm_provider", "openrouter")

# Save current configuration to file
config.save_to_file("current_config.json")

# Reload configuration from files and environment
config.reload()
```

## Migration from Legacy Configuration

If upgrading from the previous flat configuration system:

1. **Update config file structure**: Convert flat settings to the new provider-based structure
2. **Update environment variables**: Use new `LLM_*` prefixed variables instead of old names
3. **Use new imports**: Import from `config` module instead of individual constants
4. **Test provider switching**: Verify that changing `active_llm_provider` works correctly 