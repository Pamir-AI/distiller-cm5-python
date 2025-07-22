"""
Battery monitoring utilities for Pamir AI devices.

This module provides battery status monitoring via /sys/class/power_supply/pamir_battery/.
"""

import os
import logging
from typing import Dict, Optional, NamedTuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Battery sysfs path on Raspberry Pi
BATTERY_SYSFS_PATH = "/sys/class/power_supply/pamir_battery"

# Battery thresholds
CRITICAL_BATTERY_THRESHOLD = 1  # 1% - trigger shutdown
LOW_BATTERY_THRESHOLD = 15      # 15% - show warning
WARNING_BATTERY_THRESHOLD = 25  # 25% - show low battery notice


class BatteryStatus(NamedTuple):
    """Battery status information."""
    capacity: int           # Battery percentage (0-100)
    status: str            # Charging status: "Charging", "Discharging", "Full", "Unknown"
    present: bool          # Battery present
    voltage_now: float     # Current voltage in volts
    current_now: float     # Current draw in amps (negative = discharging)
    technology: str        # Battery technology (e.g., "Li-ion")
    temperature: float     # Battery temperature in Celsius


class BatteryMonitor:
    """Battery monitoring class for hardware interface."""
    
    def __init__(self):
        self.battery_path = Path(BATTERY_SYSFS_PATH)
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
                temperature=temperature
            )
            
        except Exception as e:
            logger.error(f"Error reading hardware battery status: {e}")
            return None
    
    
    def get_battery_level(self) -> int:
        """Get battery percentage (0-100)."""
        status = self.get_battery_status()
        return status.capacity if status else 100
    
    def is_charging(self) -> bool:
        """Check if battery is charging."""
        status = self.get_battery_status()
        if not status:
            return False
        return status.status.lower() in ["charging", "full"]
    
    def is_low_battery(self) -> bool:
        """Check if battery is low (below warning threshold)."""
        return self.get_battery_level() <= LOW_BATTERY_THRESHOLD
    
    def is_critical_battery(self) -> bool:
        """Check if battery is critically low (needs shutdown)."""
        return self.get_battery_level() <= CRITICAL_BATTERY_THRESHOLD
    
    def get_battery_icon_name(self) -> str:
        """Get appropriate battery icon name based on level and charging status."""
        level = self.get_battery_level()
        is_charging = self.is_charging()
        
        if is_charging:
            if level >= 90:
                return "battery-charging-full"
            elif level >= 60:
                return "battery-charging-high"
            elif level >= 30:
                return "battery-charging-medium"
            else:
                return "battery-charging-low"
        else:
            if level >= 90:
                return "battery-full"
            elif level >= 60:
                return "battery-good"
            elif level >= 30:
                return "battery-medium"
            elif level >= 15:
                return "battery-low"
            else:
                return "battery-critical"
    
    def get_battery_color(self) -> str:
        """Get appropriate color for battery indicator."""
        level = self.get_battery_level()
        
        if level <= CRITICAL_BATTERY_THRESHOLD:
            return "#FF0000"  # Red - critical
        elif level <= LOW_BATTERY_THRESHOLD:
            return "#FF8800"  # Orange - low
        elif level <= WARNING_BATTERY_THRESHOLD:
            return "#FFAA00"  # Yellow - warning
        else:
            return "#00AA00"  # Green - good
    
    def should_show_warning(self) -> bool:
        """Check if low battery warning should be shown."""
        return self.is_low_battery() and not self.is_charging()
    
    def should_shutdown(self) -> bool:
        """Check if system should shutdown due to critical battery."""
        return self.is_critical_battery() and not self.is_charging()


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
            "capacity": 100,
            "status": "Unknown",
            "isCharging": False,
            "isLow": False,
            "isCritical": False,
            "iconName": "battery-full",
            "color": "#00AA00",
            "voltage": 0.0,
            "current": 0.0,
            "temperature": 0.0,
            "present": False,
            "technology": "Unknown",
            "shouldShowWarning": False,
            "shouldShutdown": False
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
        "temperature": status.temperature,
        "present": status.present,
        "technology": status.technology,
        "shouldShowWarning": monitor.should_show_warning(),
        "shouldShutdown": monitor.should_shutdown()
    }


if __name__ == "__main__":
    # Test battery monitoring
    logging.basicConfig(level=logging.INFO)
    
    monitor = BatteryMonitor()
    status = monitor.get_battery_status()
    
    print(f"Battery Status:")
    print(f"  Capacity: {status.capacity}%")
    print(f"  Status: {status.status}")
    print(f"  Voltage: {status.voltage_now:.2f}V")
    print(f"  Current: {status.current_now:.2f}A")
    print(f"  Temperature: {status.temperature:.1f}°C")
    print(f"  Technology: {status.technology}")
    print(f"  Icon: {monitor.get_battery_icon_name()}")
    print(f"  Color: {monitor.get_battery_color()}")
    print(f"  Low Battery: {monitor.is_low_battery()}")
    print(f"  Critical: {monitor.is_critical_battery()}")
