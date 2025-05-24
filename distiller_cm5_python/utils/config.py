"""Configuration management for the MCP client application."""

import os
import json
from typing import Dict, Any

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "default_config.json"
)


class Config:
    """Centralized configuration management with environment and file overrides."""

    _instance = None

    def __new__(cls):
        """Singleton pattern to ensure single config instance."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the configuration with defaults and overrides."""
        self.config = self._load_default_config()
        self._load_from_file()
        self._load_from_env()

    def _load_default_config(self):
        """Load the default configuration from the default_config.json file."""
        default_config_path = DEFAULT_CONFIG_PATH
        try:
            with open(default_config_path, "r") as f:
                return json.load(f)

        except FileNotFoundError:
            print(
                f"Warning: Default configuration file not found at {default_config_path}"
            )
            # Provide a minimal fallback configuration
            return {
                "llm": {
                    "model_name": "pamir_3B_q4k_m.gguf",
                    "provider_type": "llama-cpp",
                    "api_key": "",
                    "timeout": 30,
                },
                "processing": {"streaming": True},
                "logging": {"level": "debug"},
            }
        except json.JSONDecodeError as e:
            print(f"Error parsing default configuration file: {e}")
            raise

    def _load_from_file(self):
        """Load configuration from a user config file if available."""
        # Determine config file path (MCP_CONFIG_FILE env var or default)
        default_user_config_path = "mcp_config.json"
        config_file = os.getenv("MCP_CONFIG_FILE", default_user_config_path)

        # Check if the file exists, but only print message if it's not the default path
        # or if the user explicitly set MCP_CONFIG_FILE
        file_exists = os.path.exists(config_file)
        if file_exists:
            try:
                with open(config_file, "r") as f:
                    file_config = json.load(f)
                self._merge_configs(self.config, file_config)
                print(f"Loaded configuration from {config_file}")
            except Exception as e:
                print(f"Error loading config file '{config_file}': {e}")
        elif os.getenv("MCP_CONFIG_FILE"):
            # User specified a file but it wasn't found
            print(f"Warning: Specified configuration file '{config_file}' not found.")

    def _load_from_env(self):
        """Override configuration with environment variables.

        Environment variables primarily override settings for the *active* LLM provider.
        """
        active_provider = self.get("active_llm_provider", default="<missing>")
        if active_provider == "<missing>" or not self.get(
            "llm_providers", active_provider
        ):
            print(
                f"Warning: Cannot apply environment overrides. Active provider '{active_provider}' not found or defined in llm_providers."
            )
            # Process only non-provider-specific settings like logging level
            log_level = os.environ.get("LOG_LEVEL")
            if log_level:
                self._set_nested_config(
                    self.config, ["logging", "level"], log_level.upper()
                )
            return

        # Define environment variable mappings to the *active* provider's settings
        # Format: ENV_VAR_NAME: [path_within_active_provider_config]
        env_provider_mappings = {
            "LLM_SERVER_URL": ["server_url"],
            "LLM_MODEL_NAME": ["model_name"],  # Renamed from LLM_MODEL for clarity
            "LLM_PROVIDER_TYPE": [
                "provider_type"
            ],  # Overrides the type derived from the key? Maybe not needed.
            "LLM_API_KEY": ["api_key"],
            "LLM_TIMEOUT": ["timeout"],
            "LLM_TEMPERATURE": ["temperature"],
            "LLM_TOP_P": ["top_p"],
            "LLM_TOP_K": ["top_k"],
            "LLM_REPETITION_PENALTY": ["repetition_penalty"],
            "LLM_N_CTX": ["n_ctx"],
            "LLM_MAX_TOKENS": ["max_tokens"],
            "LLM_STOP": ["stop"],  # Needs careful handling for list conversion
            "STREAMING_ENABLED": ["streaming"],
            "STREAMING_CHUNK_SIZE": ["streaming_chunk_size"],
            "MAX_MESSAGES_LENGTH": ["max_messages_length"],
        }

        # Process provider-specific environment variables
        for env_var, provider_config_path in env_provider_mappings.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                full_config_path = [
                    "llm_providers",
                    active_provider,
                ] + provider_config_path

                # Special handling for STOP sequences (expect comma-separated string)
                if env_var == "LLM_STOP":
                    value = [item.strip() for item in value.split(",")]
                else:
                    # Convert type based on the existing value in the config
                    value = self._convert_env_value(value, full_config_path)

                self._set_nested_config(self.config, full_config_path, value)

        # Non-provider specific settings
        log_level = os.environ.get("LOG_LEVEL")
        if log_level:
            self._set_nested_config(
                self.config, ["logging", "level"], log_level.upper()
            )

        mcp_server_script = os.environ.get("MCP_SERVER_SCRIPT_PATH")
        if mcp_server_script:
            self._set_nested_config(
                self.config, ["mcp_server", "server_script_path"], mcp_server_script
            )

    def _process_env_mappings(self, mappings):
        """Deprecated: Logic moved into _load_from_env."""
        pass  # Keep method signature for potential future use? Or remove? Removing for now.
        # for env_var, config_path in mappings.items():
        #     if env_var in os.environ:
        #         value = os.environ[env_var]
        #         # Convert types
        #         value = self._convert_env_value(value, config_path)
        #         self._set_nested_config(self.config, config_path, value)

    def _convert_env_value(self, value: str, config_path: list) -> Any:
        """Convert environment value string to the appropriate type
        based on the default/current value at the config path."""
        # Get the current value (which might be the default) to infer type
        curr_value = self._get_nested_config(self.config, config_path)

        if curr_value is None:
            # If no existing value/default, return as string
            return value

        target_type = type(curr_value)

        try:
            if target_type is bool:
                return value.lower() in ("true", "1", "yes")
            elif target_type is int:
                return int(value)
            elif target_type is float:
                return float(value)
            elif target_type is list:
                # Assume comma-separated for lists, unless it's already handled (like LLM_STOP)
                # This might need refinement based on expected list formats
                if isinstance(curr_value, list) and len(curr_value) > 0:
                    # Try to convert elements to the type of the first element in the default list
                    element_type = type(curr_value[0])
                    try:
                        return [element_type(item.strip()) for item in value.split(",")]
                    except ValueError:
                        print(
                            f"Warning: Could not convert env var list items '{value}' to type {element_type} for {config_path}. Keeping as string list."
                        )
                        return [
                            item.strip() for item in value.split(",")
                        ]  # Fallback to string list
                else:  # Default is empty list or not a list? Treat as string list.
                    return [item.strip() for item in value.split(",")]
            else:  # Default to string if type is unknown or str
                return value
        except ValueError:
            print(
                f"Warning: Could not convert env var value '{value}' to type {target_type} for config path {config_path}. Using string value."
            )
            return value  # Fallback to string on conversion error

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Recursively merge override config into base config."""
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._merge_configs(base[k], v)
            else:
                base[k] = v

    def _get_nested_config(self, config: Dict[str, Any], path: list) -> Any:
        """Get a value from nested config using a path list."""
        curr = config
        for key in path:
            if key in curr:
                curr = curr[key]
            else:
                return None
            if not isinstance(curr, dict):
                return curr
        return curr

    def _set_nested_config(
        self, config: Dict[str, Any], path: list, value: Any
    ) -> None:
        """Set a value in nested config using a path list."""
        curr = config
        for i, key in enumerate(path):
            if i == len(path) - 1:
                curr[key] = value
            else:
                if key not in curr:
                    curr[key] = {}
                curr = curr[key]

    def get(self, *path, default=None) -> Any:
        """Get a configuration value using dot notation.

        Example: config.get("llm", "model")
        """
        value = self._get_nested_config(self.config, path)
        return default if value is None else value

    def set(self, *path_and_value) -> None:
        """Set a configuration value using dot notation.

        Example: config.set("llm", "model", "llama3")
        """
        if len(path_and_value) < 2:
            raise ValueError("Need at least a path and a value")

        path = path_and_value[:-1]
        value = path_and_value[-1]
        self._set_nested_config(self.config, path, value)

    def as_dict(self) -> Dict[str, Any]:
        """Return the full configuration as a dictionary."""
        return self.config.copy()

    def save_to_file(self, filepath: str) -> None:
        """Save the current configuration to a file.

        Args:
            filepath: Path to save the configuration to
        """
        with open(filepath, "w") as f:
            json.dump(self.config, f, indent=2)
        print(f"Configuration saved to {filepath}")

    def reload(self) -> None:
        """Reload the configuration from the default file and environment."""
        self._initialize()
        print("Configuration reloaded from defaults and environment.")


# Create global configuration instance
config = Config()


# --- Global Configuration Instance ---
config = Config()

# --- Derive Active Configuration Settings ---

# 1. Get the active provider name
active_provider_name = config.get("active_llm_provider")
if not active_provider_name:
    raise ValueError("Configuration error: 'active_llm_provider' is not defined.")

# 2. Get the configuration dictionary for the active provider
active_provider_config = config.get("llm_providers", active_provider_name)
if not active_provider_config or not isinstance(active_provider_config, dict):
    raise ValueError(
        f"Configuration error: No configuration found for active provider '{active_provider_name}' under 'llm_providers'."
    )


# 3. Helper function to get values from the active provider config with fallbacks
def get_active_config(key: str, default: Any = None) -> Any:
    return active_provider_config.get(key, default)


# --- Expose Commonly Used Configuration Values (from Active Provider) ---

# Core LLM settings from the active provider
SERVER_URL = get_active_config("server_url")
MODEL_NAME = get_active_config("model_name")
PROVIDER_TYPE = get_active_config(
    "provider_type", active_provider_name
)  # Default to the key name if not specified
API_KEY = get_active_config("api_key", "")  # Default to empty string if missing
TIMEOUT = get_active_config("timeout", 120)  # Provide a sensible default
STREAMING_ENABLED = get_active_config("streaming", True)  # Default to True
STREAMING_CHUNK_SIZE = get_active_config(
    "streaming_chunk_size", 4
)  # Default based on old config

# Other parameters from the active provider (with defaults)
TEMPERATURE = get_active_config("temperature", 0.7)
TOP_P = get_active_config("top_p", 0.8)
TOP_K = get_active_config("top_k", 20)
MIN_P = get_active_config("min_p", 0.0)
REPETITION_PENALTY = get_active_config("repetition_penalty", 1.0)
N_CTX = get_active_config("n_ctx", 32768)  # Context window size
MAX_TOKENS = get_active_config("max_tokens", 4096)  # Max generation tokens
STOP = get_active_config("stop", ["\n\n"])  # Stop sequences
MAX_MESSAGES_LENGTH = get_active_config("max_messages_length", 100)  # History length
LLAMA_CPP_START_WAIT_TIME = get_active_config("timeout", 30)  # Default 3 seconds

# Non-LLM specific configurations (remain as before)
DEFAULT_SYSTEM_PROMPT = config.get(
    "prompts", "default_system_prompt", "You are a helpful assistant."
)
MCP_SERVER_SCRIPT_PATH = config.get(
    "mcp_server", "server_script_path", "mcp_server/wifi_mac_server.py"
)  # Provide default
LOGGING_LEVEL = config.get(
    "logging", "level", "INFO"
).upper()  # Default to INFO, ensure uppercase
