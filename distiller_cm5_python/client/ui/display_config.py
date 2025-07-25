"""
E-Ink display configuration for Raspberry Pi.
This module loads configuration from TOML file with integrated defaults.
"""

from .display_config_manager import DisplayConfig

# Load configuration and convert to legacy format for backwards compatibility
_display_config = DisplayConfig.load()
config = _display_config.to_legacy_dict()
