import os
import time
import psutil


class SystemMonitor:
    def __init__(self):
        self.ram_usage = 0.0
        self.cpu_usage = 0.0
        self.temperature = 0.0
        self.llm_model = "Local"  # Default LLM model name
        self.last_update_time = 0
        self.update_interval = 2.0  # Update every 2 seconds to avoid excessive resource usage

    def get_ram_usage(self):
        """Return current RAM usage as a percentage."""
        self._update_if_needed()
        return self.ram_usage

    def get_cpu_usage(self):
        """Return current CPU usage as a percentage."""
        self._update_if_needed()
        return self.cpu_usage

    def get_temperature(self):
        """Return current CPU temperature in Celsius."""
        self._update_if_needed()
        return self.temperature

    def get_llm_model(self):
        """Return the current LLM model name."""
        return self.llm_model

    def set_llm_model(self, model_name):
        """Set the current LLM model name."""
        self.llm_model = model_name

    def get_formatted_stats(self):
        """Return all stats in a formatted dictionary."""
        self._update_if_needed()
        return {
            "cpu": f"{self.cpu_usage:.1f}%",
            "ram": f"{self.ram_usage:.1f}%",
            "temp": f"{self.temperature:.1f}°C",
            "llm": self.llm_model,
        }

    def _update_if_needed(self):
        """Update stats if update interval has passed."""
        current_time = time.time()
        if current_time - self.last_update_time >= self.update_interval:
            self._update_stats()
            self.last_update_time = current_time

    def _update_stats(self):
        """Update all system stats."""
        try:
            # Get RAM usage
            memory = psutil.virtual_memory()
            self.ram_usage = memory.percent

            # Get CPU usage
            self.cpu_usage = psutil.cpu_percent(interval=0.1)

            # Get temperature - try different methods as it depends on the system
            try:
                temps = psutil.sensors_temperatures()
                # Check different temperature sensors based on platform
                if "coretemp" in temps:
                    self.temperature = temps["coretemp"][0].current
                elif "cpu_thermal" in temps:  # Raspberry Pi
                    self.temperature = temps["cpu_thermal"][0].current
                elif "soc_thermal" in temps:  # Some ARM devices
                    self.temperature = temps["soc_thermal"][0].current
                else:
                    # Fallback to reading from thermal zone
                    self._read_temp_from_zone()
            except (AttributeError, IOError):
                # psutil might not have sensors_temperatures on all platforms
                self._read_temp_from_zone()

        except Exception as e:
            print(f"Error updating system stats: {e}")

    def _read_temp_from_zone(self):
        """Read temperature from thermal zone files."""
        try:
            # Try to read from thermal zone 0 (may vary by system)
            temp_file = "/sys/class/thermal/thermal_zone0/temp"
            if os.path.exists(temp_file):
                with open(temp_file, "r") as f:
                    temp_millicelsius = int(f.read().strip())
                    self.temperature = temp_millicelsius / 1000.0
            else:
                self.temperature = 0.0
        except Exception:
            self.temperature = 0.0


# Create a singleton instance
system_monitor = SystemMonitor()
