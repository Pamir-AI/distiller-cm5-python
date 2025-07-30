"""
Battery configuration management with integrated defaults.
"""

import logging
from typing import Dict
from dataclasses import dataclass, field
from .config_loader import load_toml_config, get_battery_config_path

logger = logging.getLogger(__name__)


@dataclass
class BatteryThresholds:
    """Battery threshold configuration."""

    critical: int = 1  # 1% - trigger shutdown
    low: int = 15  # 15% - show warning
    warning: int = 25  # 25% - show low battery notice
    temperature_warning: float = 55.0  # 55°C - show temperature warning
    charging_current: float = 0.01  # 0.01A - minimum current to consider charging
    current_threshold: float = 10.0  # 10A - fallback threshold for charging detection via current magnitude


@dataclass
class BatteryMonitoringConfig:
    """Battery monitoring interval configuration."""

    update_interval: int = 5000  # 5 seconds - battery indicator update
    monitor_interval: int = 10000  # 10 seconds - main battery monitoring


@dataclass
class BatteryHardwareConfig:
    """Battery hardware configuration."""

    sysfs_path: str = "/sys/class/power_supply/pamir_battery"


@dataclass
class BatteryStatusPatterns:
    """Battery status patterns for 1-bit monochrome display."""

    critical: str = "solid_black"  # Solid black fill - critical
    low: str = "diagonal_stripes"  # Diagonal stripes - low
    warning: str = "cross_hatch"  # Cross-hatch pattern - warning
    good: str = "solid_fill"  # Normal solid fill - good
    unknown: str = "empty"  # Empty pattern - unknown status


@dataclass
class BatteryStatusText:
    """Battery status text indicators for 1-bit display."""

    critical: str = "CRIT"  # Critical battery text
    low: str = "LOW"  # Low battery text
    warning: str = "WARN"  # Warning battery text
    good: str = "OK"  # Good battery text
    unknown: str = "UNK"  # Unknown battery status text


@dataclass
class BatteryIcons:
    """Battery icon configuration."""

    charging: Dict[str, str] = field(
        default_factory=lambda: {
            "full": "battery-charging-full",
            "high": "battery-charging-high",
            "medium": "battery-charging-medium",
            "low": "battery-charging-low",
            "unknown": "battery-charging-unknown",
        }
    )
    discharging: Dict[str, str] = field(
        default_factory=lambda: {
            "full": "battery-full",
            "good": "battery-good",
            "medium": "battery-medium",
            "low": "battery-low",
            "critical": "battery-critical",
            "unknown": "battery-unknown",
        }
    )


@dataclass
class BatteryConfig:
    """Complete battery configuration with defaults."""

    thresholds: BatteryThresholds = field(default_factory=BatteryThresholds)
    monitoring: BatteryMonitoringConfig = field(default_factory=BatteryMonitoringConfig)
    hardware: BatteryHardwareConfig = field(default_factory=BatteryHardwareConfig)
    status_patterns: BatteryStatusPatterns = field(default_factory=BatteryStatusPatterns)
    status_text: BatteryStatusText = field(default_factory=BatteryStatusText)
    icons: BatteryIcons = field(default_factory=BatteryIcons)

    @classmethod
    def load(cls) -> "BatteryConfig":
        """
        Load battery configuration from TOML file with fallback to defaults.

        Returns:
            BatteryConfig instance with loaded or default values
        """
        config_data = load_toml_config(get_battery_config_path())

        # Start with defaults
        config = cls()

        if config_data and "battery" in config_data:
            battery_data = config_data["battery"]

            # Load thresholds
            if "thresholds" in battery_data:
                thresholds_data = battery_data["thresholds"]
                config.thresholds = BatteryThresholds(
                    critical=thresholds_data.get("critical", config.thresholds.critical),
                    low=thresholds_data.get("low", config.thresholds.low),
                    warning=thresholds_data.get("warning", config.thresholds.warning),
                    temperature_warning=thresholds_data.get(
                        "temperature_warning", config.thresholds.temperature_warning
                    ),
                    charging_current=thresholds_data.get(
                        "charging_current", config.thresholds.charging_current
                    ),
                )

            # Load monitoring config
            if "monitoring" in battery_data:
                monitoring_data = battery_data["monitoring"]
                config.monitoring = BatteryMonitoringConfig(
                    update_interval=monitoring_data.get(
                        "update_interval", config.monitoring.update_interval
                    ),
                    monitor_interval=monitoring_data.get(
                        "monitor_interval", config.monitoring.monitor_interval
                    ),
                )

            # Load hardware config
            if "hardware" in battery_data:
                hardware_data = battery_data["hardware"]
                config.hardware = BatteryHardwareConfig(
                    sysfs_path=hardware_data.get("sysfs_path", config.hardware.sysfs_path)
                )

            # Load status patterns
            if "status_patterns" in battery_data:
                patterns_data = battery_data["status_patterns"]
                config.status_patterns = BatteryStatusPatterns(
                    critical=patterns_data.get("critical", config.status_patterns.critical),
                    low=patterns_data.get("low", config.status_patterns.low),
                    warning=patterns_data.get("warning", config.status_patterns.warning),
                    good=patterns_data.get("good", config.status_patterns.good),
                    unknown=patterns_data.get("unknown", config.status_patterns.unknown),
                )

            # Load status text
            if "status_text" in battery_data:
                text_data = battery_data["status_text"]
                config.status_text = BatteryStatusText(
                    critical=text_data.get("critical", config.status_text.critical),
                    low=text_data.get("low", config.status_text.low),
                    warning=text_data.get("warning", config.status_text.warning),
                    good=text_data.get("good", config.status_text.good),
                    unknown=text_data.get("unknown", config.status_text.unknown),
                )

            # Load icons
            if "icons" in battery_data:
                icons_data = battery_data["icons"]
                charging_icons = config.icons.charging.copy()
                discharging_icons = config.icons.discharging.copy()

                if "charging" in icons_data:
                    charging_icons.update(icons_data["charging"])
                if "discharging" in icons_data:
                    discharging_icons.update(icons_data["discharging"])

                config.icons = BatteryIcons(charging=charging_icons, discharging=discharging_icons)

        return config
