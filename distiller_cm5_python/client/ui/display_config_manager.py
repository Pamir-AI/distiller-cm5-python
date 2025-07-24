"""
Display configuration management with integrated defaults.
"""

import logging
from typing import Dict, Any
from dataclasses import dataclass, field
from distiller_cm5_python.utils.config_loader import load_toml_config, get_display_config_path

logger = logging.getLogger(__name__)


@dataclass
class EInkBWConversionConfig:
    """E-ink black/white conversion configuration."""
    use_gamma: bool = True
    gamma_value: float = 0.8


@dataclass
class DisplayHardwareConfig:
    """Display hardware configuration."""
    full_refresh_lut_mode: bool = True


@dataclass
class DisplayDebugConfig:
    """Display debug configuration."""
    eink_save_capture: bool = True


@dataclass
class FontConfig:
    """Font configuration."""
    primary_font: str = "fonts/MartianMonoNerdFont-CondensedBold.ttf"
    size_small: int = 12
    size_normal: int = 14
    size_medium: int = 16
    size_large: int = 18
    size_xlarge: int = 20


@dataclass
class UIConfig:
    """UI configuration."""
    dark_mode: bool = False
    show_system_stats: bool = True
    font: FontConfig = field(default_factory=FontConfig)


@dataclass
class DisplayConfig:
    """Complete display configuration with defaults."""
    # Core E-Ink Settings
    eink_enabled: bool = False
    width: int = 240
    height: int = 416
    
    # Performance Settings
    eink_refresh_interval: int = 1000           # Milliseconds between captures
    eink_adaptive_capture: bool = True          # Automatically adjust refresh rate
    eink_full_refresh_interval: int = 30        # Full refresh every N frames
    eink_timer_based_mode: bool = False         # Use timer-based capture
    
    # Image Processing Settings
    eink_threshold: int = 128                   # Black/white threshold (0-255)
    eink_bw_conversion: EInkBWConversionConfig = field(default_factory=EInkBWConversionConfig)
    
    # Hardware Settings
    hardware: DisplayHardwareConfig = field(default_factory=DisplayHardwareConfig)
    
    # Debug Settings
    debug: DisplayDebugConfig = field(default_factory=DisplayDebugConfig)
    
    # UI Settings
    ui: UIConfig = field(default_factory=UIConfig)

    @classmethod
    def load(cls) -> 'DisplayConfig':
        """
        Load display configuration from TOML file with fallback to defaults.
        
        Returns:
            DisplayConfig instance with loaded or default values
        """
        config_data = load_toml_config(get_display_config_path())
        
        # Start with defaults
        config = cls()
        
        if config_data and "display" in config_data:
            display_data = config_data["display"]
            
            # Load basic display settings
            config.eink_enabled = display_data.get("eink_enabled", config.eink_enabled)
            config.width = display_data.get("width", config.width)
            config.height = display_data.get("height", config.height)
            config.eink_refresh_interval = display_data.get("eink_refresh_interval", config.eink_refresh_interval)
            config.eink_adaptive_capture = display_data.get("eink_adaptive_capture", config.eink_adaptive_capture)
            config.eink_full_refresh_interval = display_data.get("eink_full_refresh_interval", config.eink_full_refresh_interval)
            config.eink_timer_based_mode = display_data.get("eink_timer_based_mode", config.eink_timer_based_mode)
            config.eink_threshold = display_data.get("eink_threshold", config.eink_threshold)
            
            # Load BW conversion settings
            if "eink_bw_conversion" in display_data:
                bw_data = display_data["eink_bw_conversion"]
                config.eink_bw_conversion = EInkBWConversionConfig(
                    use_gamma=bw_data.get("use_gamma", config.eink_bw_conversion.use_gamma),
                    gamma_value=bw_data.get("gamma_value", config.eink_bw_conversion.gamma_value)
                )
            
            # Load hardware settings
            if "hardware" in display_data:
                hardware_data = display_data["hardware"]
                config.hardware = DisplayHardwareConfig(
                    full_refresh_lut_mode=hardware_data.get("full_refresh_lut_mode", config.hardware.full_refresh_lut_mode)
                )
            
            # Load debug settings
            if "debug" in display_data:
                debug_data = display_data["debug"]
                config.debug = DisplayDebugConfig(
                    eink_save_capture=debug_data.get("eink_save_capture", config.debug.eink_save_capture)
                )
            
            # Load UI settings
            if "ui" in display_data:
                ui_data = display_data["ui"]
                
                # Load font settings
                font_config = config.ui.font
                if "font" in ui_data:
                    font_data = ui_data["font"]
                    font_config = FontConfig(
                        primary_font=font_data.get("primary_font", font_config.primary_font),
                        size_small=font_data.get("size_small", font_config.size_small),
                        size_normal=font_data.get("size_normal", font_config.size_normal),
                        size_medium=font_data.get("size_medium", font_config.size_medium),
                        size_large=font_data.get("size_large", font_config.size_large),
                        size_xlarge=font_data.get("size_xlarge", font_config.size_xlarge)
                    )
                
                config.ui = UIConfig(
                    dark_mode=ui_data.get("dark_mode", config.ui.dark_mode),
                    show_system_stats=ui_data.get("show_system_stats", config.ui.show_system_stats),
                    font=font_config
                )
        
        return config

    def to_legacy_dict(self) -> Dict[str, Any]:
        """
        Convert to legacy dictionary format for backwards compatibility.
        
        Returns:
            Dictionary in the format expected by existing code
        """
        return {
            "display": {
                "eink_enabled": self.eink_enabled,
                "width": self.width,
                "height": self.height,
                "eink_refresh_interval": self.eink_refresh_interval,
                "eink_adaptive_capture": self.eink_adaptive_capture,
                "eink_full_refresh_interval": self.eink_full_refresh_interval,
                "eink_timer_based_mode": self.eink_timer_based_mode,
                "eink_threshold": self.eink_threshold,
                "eink_bw_conversion": {
                    "use_gamma": self.eink_bw_conversion.use_gamma,
                    "gamma_value": self.eink_bw_conversion.gamma_value,
                },
                "hardware": {
                    "full_refresh_lut_mode": self.hardware.full_refresh_lut_mode,
                },
                "debug": {
                    "eink_save_capture": self.debug.eink_save_capture,
                },
                "ui": {
                    "dark_mode": self.ui.dark_mode,
                    "show_system_stats": self.ui.show_system_stats,
                    "font": {
                        "primary_font": self.ui.font.primary_font,
                        "size_small": self.ui.font.size_small,
                        "size_normal": self.ui.font.size_normal,
                        "size_medium": self.ui.font.size_medium,
                        "size_large": self.ui.font.size_large,
                        "size_xlarge": self.ui.font.size_xlarge,
                    }
                }
            }
        }