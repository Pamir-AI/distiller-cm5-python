"""
Battery monitoring utilities for Pamir AI devices.

This module provides battery status monitoring via /sys/class/power_supply/pamir_battery/.
"""

import logging
from typing import Dict, Optional, NamedTuple
from pathlib import Path
from .battery_config_manager import BatteryConfig

logger = logging.getLogger(__name__)


class BatteryStatus(NamedTuple):
    """Battery status information."""

    capacity: int  # Battery percentage (0-100)
    status: str  # Charging status: "Charging", "Discharging", "Full", "Unknown"
    present: bool  # Battery present
    voltage_now: float  # Current voltage in volts
    current_now: (
        float  # Current draw in amps (negative = discharging, positive = charging)
    )
    technology: str  # Battery technology (e.g., "Li-ion")
    temperature: float  # Battery temperature in Celsius


class BatteryMonitor:
    """Battery monitoring class for hardware interface."""

    def __init__(self, config: Optional[BatteryConfig] = None):
        self.config = config or BatteryConfig.load()
        self.battery_path = Path(self.config.hardware.sysfs_path)
        logger.info("Hardware battery monitoring initialized")

    def _check_hardware_availability(self) -> bool:
        """Check if battery hardware is available."""
        return self.battery_path.exists() and (self.battery_path / "capacity").exists()

    def _read_sysfs_file(self, filename: str) -> Optional[str]:
        """Read a value from battery sysfs file."""
        try:
            file_path = self.battery_path / filename
            if file_path.exists():
                return file_path.read_text().strip()
        except Exception as e:
            logger.error(f"Error reading battery sysfs file {filename}: {e}")
        return None

    def get_battery_status(self) -> Optional[BatteryStatus]:
        """Get current battery status from hardware."""
        try:
            # Read capacity
            capacity_str = self._read_sysfs_file("capacity")
            if capacity_str is None:
                return None
            capacity = int(capacity_str)

            # Read status
            status = self._read_sysfs_file("status") or "Unknown"

            # Read present
            present_str = self._read_sysfs_file("present")
            present = present_str == "1" if present_str else True

            # Read voltage (microvolts to volts)
            voltage_str = self._read_sysfs_file("voltage_now")
            voltage_now = float(voltage_str) / 1_000_000 if voltage_str else 0.0

            # Read current (microamps to amps)
            current_str = self._read_sysfs_file("current_now")
            current_now = float(current_str) / 1_000_000 if current_str else 0.0

            # Read technology
            technology = self._read_sysfs_file("technology") or "Unknown"

            # Read temperature (decidegrees to celsius)
            temp_str = self._read_sysfs_file("temp")
            temperature = float(temp_str) / 10 if temp_str else 0.0

            return BatteryStatus(
                capacity=capacity,
                status=status,
                present=present,
                voltage_now=voltage_now,
                current_now=current_now,
                technology=technology,
                temperature=temperature,
            )

        except Exception as e:
            logger.error(f"Error reading hardware battery status: {e}")
            return None

    def get_battery_level(self) -> int:
        """Get battery percentage (0-100)."""
        status = self.get_battery_status()
        return status.capacity if status else 0

    def is_charging(self) -> bool:
        """Check if battery is charging based on current and status."""
        status = self.get_battery_status()
        if not status:
            return False
        # Check both status and current for more accurate charging detection
        status_charging = status.status.lower() in ["charging", "full"]
        current_charging = status.current_now > self.config.thresholds.charging_current
        return status_charging or current_charging

    def is_low_battery(self) -> bool:
        """Check if battery is low (below warning threshold)."""
        return self.get_battery_level() <= self.config.thresholds.low

    def is_critical_battery(self) -> bool:
        """Check if battery is critically low (needs shutdown)."""
        return self.get_battery_level() <= self.config.thresholds.critical

    def is_temperature_warning(self) -> bool:
        """Check if battery temperature exceeds warning threshold."""
        status = self.get_battery_status()
        if not status:
            return False
        return status.temperature > self.config.thresholds.temperature_warning

    def get_battery_icon_name(self) -> str:
        """Get appropriate battery icon name based on level and charging status."""
        level = self.get_battery_level()
        is_charging = self.is_charging()

        if is_charging:
            if level >= 90:
                return self.config.icons.charging["full"]
            elif level >= 60:
                return self.config.icons.charging["high"]
            elif level >= 30:
                return self.config.icons.charging["medium"]
            else:
                return self.config.icons.charging["low"]
        else:
            if level >= 90:
                return self.config.icons.discharging["full"]
            elif level >= 60:
                return self.config.icons.discharging["good"]
            elif level >= 30:
                return self.config.icons.discharging["medium"]
            elif level >= 15:
                return self.config.icons.discharging["low"]
            else:
                return self.config.icons.discharging["critical"]

    def get_battery_color(self) -> str:
        """Get appropriate color for battery indicator."""
        level = self.get_battery_level()

        if level <= self.config.thresholds.critical:
            return self.config.colors.critical
        elif level <= self.config.thresholds.low:
            return self.config.colors.low
        elif level <= self.config.thresholds.warning:
            return self.config.colors.warning
        else:
            return self.config.colors.good

    def should_show_warning(self) -> bool:
        """Check if low battery warning should be shown."""
        return self.is_low_battery() and not self.is_charging()

    def should_shutdown(self) -> bool:
        """Check if system should shutdown due to critical battery."""
        return self.is_critical_battery() and not self.is_charging()

    def get_current_ma(self) -> float:
        """Get current in milliamps for UI display."""
        status = self.get_battery_status()
        if not status:
            return 0.0
        return status.current_now * 1000  # Convert from amps to milliamps


# Global battery monitor instance
_battery_monitor = None


def get_battery_monitor() -> BatteryMonitor:
    """Get the global battery monitor instance."""
    global _battery_monitor
    if _battery_monitor is None:
        _battery_monitor = BatteryMonitor()
    return _battery_monitor


def get_battery_info() -> Dict[str, any]:
    """Get battery information as a dictionary (for QML binding)."""
    monitor = get_battery_monitor()
    status = monitor.get_battery_status()

    if not status:
        # Return default values if battery hardware is not available
        return {
            "capacity": 1,
            "status": "Unknown",
            "isCharging": False,
            "isLow": False,
            "isCritical": True,
            "iconName": "battery-unknown",
            "color": "#808080",  # Grey color for unknown
            "voltage": 0.0,
            "current": 0.0,
            "current_ma": 0.0,
            "temperature": 0.0,
            "present": False,
            "technology": "Unknown",
            "shouldShowWarning": True,
            "shouldShutdown": False,
            "isTemperatureWarning": True,
        }

    return {
        "capacity": status.capacity,
        "status": status.status,
        "isCharging": monitor.is_charging(),
        "isLow": monitor.is_low_battery(),
        "isCritical": monitor.is_critical_battery(),
        "iconName": monitor.get_battery_icon_name(),
        "color": monitor.get_battery_color(),
        "voltage": status.voltage_now,
        "current": status.current_now,
        "current_ma": monitor.get_current_ma(),
        "temperature": status.temperature,
        "present": status.present,
        "technology": status.technology,
        "shouldShowWarning": monitor.should_show_warning(),
        "shouldShutdown": monitor.should_shutdown(),
        "isTemperatureWarning": monitor.is_temperature_warning(),
    }


if __name__ == "__main__":
    # Test battery monitoring
    logging.basicConfig(level=logging.INFO)

    monitor = BatteryMonitor()
    status = monitor.get_battery_status()

    print(f"Battery Status:")
    if status:
        print(f"  Capacity: {status.capacity}%")
        print(f"  Status: {status.status}")
        print(f"  Voltage: {status.voltage_now:.2f}V")
        print(
            f"  Current: {status.current_now:.2f}A ({monitor.get_current_ma():.1f}mA)"
        )
        print(f"  Temperature: {status.temperature:.1f}°C")
        print(f"  Technology: {status.technology}")
        print(f"  Icon: {monitor.get_battery_icon_name()}")
        print(f"  Color: {monitor.get_battery_color()}")
        print(f"  Charging: {monitor.is_charging()}")
        print(f"  Low Battery: {monitor.is_low_battery()}")
        print(f"  Critical: {monitor.is_critical_battery()}")
        print(f"  Temperature Warning: {monitor.is_temperature_warning()}")
    else:
        print("  Battery hardware not available - using get_battery_info() instead:")
        info = get_battery_info()
        for key, value in info.items():
            print(f"  {key}: {value}")
