import re
import subprocess
import sys
from distiller_cm5_python.utils.logger import logger


class NetworkUtils:
    """
    Utility class for network-related functionality.

    Provides methods for obtaining network information such as IP addresses.
    """

    def get_wifi_ip_address(self):
        """Get the WiFi IP address of the system.

        Returns:
            IP address as a string or an error message
        """
        try:
            # Cross-platform method to get IP address
            if sys.platform == "win32":
                return self._get_windows_ip()
            elif sys.platform == "darwin":
                return self._get_macos_ip()
            elif sys.platform.startswith("linux"):
                return self._get_linux_ip()
            else:
                # Unsupported platform
                return f"Unsupported platform: {sys.platform}"
        except Exception as e:
            logger.error(f"Error getting IP address: {e}")
            return "Error getting IP address"

    def _get_windows_ip(self):
        """Get the IP address for Windows systems.

        Returns:
            IP address as a string or an error message
        """
        try:
            result = subprocess.run(
                ["ipconfig"], capture_output=True, text=True, check=True
            )

            # Parse output for WiFi adapter
            output = result.stdout
            wifi_section = False
            ip_address = None

            for line in output.split("\n"):
                if "Wireless LAN adapter" in line or "Wi-Fi" in line:
                    wifi_section = True
                elif wifi_section and ":" in line:
                    if "IPv4 Address" in line:
                        ip_address = line.split(":")[-1].strip()
                        # Remove potential parentheses with IPv6 info
                        if "(" in ip_address:
                            ip_address = ip_address.split("(")[0].strip()
                        break
                elif wifi_section and len(line.strip()) == 0:
                    # End of the WiFi section
                    wifi_section = False

            if ip_address:
                return ip_address
            return "No WiFi IP found"
        except Exception as e:
            logger.error(f"Error getting Windows IP address: {e}")
            return "Error getting IP address"

    def _get_macos_ip(self):
        """Get the IP address for macOS systems.

        Returns:
            IP address as a string or an error message
        """
        try:
            # Get the default interface
            route_result = subprocess.run(
                ["route", "get", "default"],
                capture_output=True,
                text=True,
                check=True,
            )

            # Extract interface from route output
            route_output = route_result.stdout
            interface = None
            for line in route_output.split("\n"):
                if "interface:" in line:
                    interface = line.split(":")[-1].strip()
                    break

            if not interface:
                return "No default network interface found"

            # Get IP for the interface
            ifconfig_result = subprocess.run(
                ["ifconfig", interface],
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse for inet address
            ifconfig_output = ifconfig_result.stdout
            for line in ifconfig_output.split("\n"):
                if "inet " in line and "127.0.0.1" not in line:
                    # Extract IP address
                    ip_parts = line.strip().split()
                    if len(ip_parts) > 1:
                        return ip_parts[1]

            return f"No WiFi IP found for interface {interface}"
        except Exception as e:
            logger.error(f"Error getting macOS IP address: {e}")
            return "Error getting IP address"

    def _get_linux_ip(self):
        """Get the IP address for Linux systems.

        Returns:
            IP address as a string or an error message
        """
        try:
            # Try using ip command first (modern)
            try:
                result = subprocess.run(
                    ["ip", "-4", "addr", "show"],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                # Parse output looking for wifi interface (wlan0, wlp2s0, etc.)
                output = result.stdout
                wifi_regex = r"(wl\w+)"
                wifi_interfaces = re.findall(wifi_regex, output)

                if wifi_interfaces:
                    wifi_interface = wifi_interfaces[0]
                    # Look for inet address on this interface
                    interface_section = False
                    for line in output.split("\n"):
                        if wifi_interface in line:
                            interface_section = True
                        elif interface_section and "inet " in line:
                            # Extract IP
                            ip_match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", line)
                            if ip_match:
                                return ip_match.group(1)
                        elif interface_section and len(line.strip()) == 0:
                            interface_section = False

                # If no WiFi, find any non-loopback IP
                for line in output.split("\n"):
                    if "inet " in line and "127.0.0.1" not in line:
                        ip_match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", line)
                        if ip_match:
                            return ip_match.group(1)

            except FileNotFoundError:
                # Fall back to ifconfig
                result = subprocess.run(
                    ["ifconfig"], capture_output=True, text=True, check=True
                )

                output = result.stdout
                wifi_regex = r"(wl\w+)"
                wifi_interfaces = re.findall(wifi_regex, output)

                if wifi_interfaces:
                    wifi_interface = wifi_interfaces[0]
                    interface_section = False
                    for line in output.split("\n"):
                        if wifi_interface in line:
                            interface_section = True
                        elif interface_section and "inet " in line:
                            ip_match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", line)
                            if ip_match:
                                return ip_match.group(1)
                        elif interface_section and len(line.strip()) == 0:
                            interface_section = False

                # If no WiFi, find any non-loopback IP
                for line in output.split("\n"):
                    if "inet " in line and "127.0.0.1" not in line:
                        ip_match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", line)
                        if ip_match:
                            return ip_match.group(1)

            return "No network IP found"
        except Exception as e:
            logger.error(f"Error getting Linux IP address: {e}")
            return "Error getting IP address"
