"""
Configuration loader utilities for TOML files.
"""

import tomllib
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def load_toml_config(config_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load configuration from a TOML file.
    
    Args:
        config_path: Path to the TOML configuration file
        
    Returns:
        Loaded configuration dictionary or None if file doesn't exist/error
    """
    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        logger.debug(f"Config file not found: {config_path}")
        return None
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        return None


def get_config_path(relative_path: str) -> Path:
    """
    Get absolute path to a configuration file relative to the utils directory.
    
    Args:
        relative_path: Path relative to the utils directory
        
    Returns:
        Absolute path to the configuration file
    """
    return Path(__file__).parent / relative_path


def get_display_config_path() -> Path:
    """Get path to display configuration file."""
    return Path(__file__).parent.parent / "client" / "ui" / "display_config.toml"


def get_battery_config_path() -> Path:
    """Get path to battery configuration file."""
    return get_config_path("battery_config.toml")


def get_main_config_path() -> Path:
    """Get path to main configuration file."""
    return get_config_path("default_config.toml")
