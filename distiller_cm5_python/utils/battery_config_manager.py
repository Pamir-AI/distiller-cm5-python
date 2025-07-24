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
class BatteryColors:
    """Battery UI color configuration."""

    critical: str = "#FF0000"  # Red - critical
    low: str = "#FF8800"  # Orange - low
    warning: str = "#FFAA00"  # Yellow - warning
    good: str = "#00AA00"  # Green - good


@dataclass
class BatteryIcons:
    """Battery icon configuration."""

    charging: Dict[str, str] = field(
        default_factory=lambda: {
            "full": "battery-charging-full",
            "high": "battery-charging-high",
            "medium": "battery-charging-medium",
            "low": "battery-charging-low",
        }
    )
    discharging: Dict[str, str] = field(
        default_factory=lambda: {
            "full": "battery-full",
            "good": "battery-good",
            "medium": "battery-medium",
            "low": "battery-low",
            "critical": "battery-critical",
        }
    )


@dataclass
class BatteryConfig:
    """Complete battery configuration with defaults."""

    thresholds: BatteryThresholds = field(default_factory=BatteryThresholds)
    monitoring: BatteryMonitoringConfig = field(default_factory=BatteryMonitoringConfig)
    hardware: BatteryHardwareConfig = field(default_factory=BatteryHardwareConfig)
    colors: BatteryColors = field(default_factory=BatteryColors)
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
                    critical=thresholds_data.get(
                        "critical", config.thresholds.critical
                    ),
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
                    sysfs_path=hardware_data.get(
                        "sysfs_path", config.hardware.sysfs_path
                    )
                )

            # Load colors
            if "colors" in battery_data:
                colors_data = battery_data["colors"]
                config.colors = BatteryColors(
                    critical=colors_data.get("critical", config.colors.critical),
                    low=colors_data.get("low", config.colors.low),
                    warning=colors_data.get("warning", config.colors.warning),
                    good=colors_data.get("good", config.colors.good),
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

                config.icons = BatteryIcons(
                    charging=charging_icons, discharging=discharging_icons
                )

        return config
