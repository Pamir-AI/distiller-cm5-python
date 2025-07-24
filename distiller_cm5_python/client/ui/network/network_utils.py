"""
Network utilities for synchronous network information retrieval
Provides compatibility layer for wifi_info_display.py
"""

import asyncio
import subprocess
import socket
import logging
import os
from typing import Dict, List, Any
from .wifi_manager import WiFiManager

logger = logging.getLogger(__name__)


class NetworkUtils:
    """Synchronous network utilities using WiFiManager backend"""

    def __init__(self):
        self.wifi_manager = WiFiManager()
        self._use_sudo = self._should_use_sudo()

    def _should_use_sudo(self) -> bool:
        """Determine if we should use sudo for privileged commands"""
        # Use sudo if we're running as the 'distiller' user
        current_user = os.getenv('USER') or os.getenv('USERNAME') or 'unknown'
        return current_user == 'distiller'

    def _build_command(self, base_cmd: list[str]) -> list[str]:
        """Build command with sudo prefix if needed for privileged operations"""
        privileged_commands = {'nmcli', 'ip', 'hostname', 'systemctl', 'iwconfig', 'iwgetid'}
        
        if self._use_sudo and base_cmd and base_cmd[0] in privileged_commands:
            return ['sudo'] + base_cmd
        return base_cmd

    def _run_async(self, coro):
        """Run async coroutine synchronously"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an event loop, create a new one
                import threading

                result = None
                exception = None

                def run_in_thread():
                    nonlocal result, exception
                    try:
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        result = new_loop.run_until_complete(coro)
                        new_loop.close()
                    except Exception as e:
                        exception = e

                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()

                if exception:
                    raise exception
                return result
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(coro)

    def get_wifi_name(self) -> str:
        """Get current WiFi network name (SSID)"""
        try:
            status = self._run_async(self.wifi_manager.get_connection_status())
            if status and status.connected and status.ssid:
                return status.ssid
            return "Not Connected"
        except Exception as e:
            logger.error(f"Error getting WiFi name: {e}")
            return "Unknown"

    def get_wifi_ip_address(self) -> str:
        """Get current WiFi IP address"""
        try:
            status = self._run_async(self.wifi_manager.get_connection_status())
            if status and status.connected and status.ip_address:
                return status.ip_address
            return "No IP Address"
        except Exception as e:
            logger.error(f"Error getting WiFi IP: {e}")
            return "Unknown"

    def get_wifi_mac_address(self) -> str:
        """Get WiFi interface MAC address"""
        try:
            status = self._run_async(self.wifi_manager.get_connection_status())
            if status and status.interface:
                # Get MAC address using ip command
                result = subprocess.run(
                    self._build_command(["ip", "link", "show", status.interface]),
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if "link/ether" in line:
                            mac = line.split()[1]
                            return mac.upper()

            # Fallback: try common WiFi interface names
            for interface in ["wlan0", "wlp2s0", "wlp3s0"]:
                try:
                    result = subprocess.run(
                        self._build_command(["ip", "link", "show", interface]),
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split("\n"):
                            if "link/ether" in line:
                                mac = line.split()[1]
                                return mac.upper()
                except:
                    continue

            return "Unknown MAC"
        except Exception as e:
            logger.error(f"Error getting MAC address: {e}")
            return "Unknown"

    def get_wifi_signal_strength(self) -> str:
        """Get WiFi signal strength"""
        try:
            status = self._run_async(self.wifi_manager.get_connection_status())
            if not status or not status.connected or not status.interface:
                return "No Signal"

            # Try to get signal strength using nmcli
            try:
                result = subprocess.run(
                    self._build_command([
                        "nmcli",
                        "-t",
                        "-f",
                        "SIGNAL",
                        "device",
                        "wifi",
                        "list",
                        "--rescan",
                        "no",
                    ]),
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")
                    if lines and lines[0]:
                        signal = lines[0].strip()
                        if signal.isdigit():
                            return f"{signal}%"
            except:
                pass

            # Fallback: try iwconfig
            try:
                result = subprocess.run(
                    self._build_command(["iwconfig", status.interface]),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if "Signal level" in line:
                            # Extract signal level
                            if "dBm" in line:
                                # Format: Signal level=-50 dBm
                                parts = line.split("Signal level=")[1].split()[0]
                                dbm = int(parts.replace("dBm", ""))
                                # Convert dBm to percentage (rough approximation)
                                if dbm >= -30:
                                    percent = 100
                                elif dbm <= -90:
                                    percent = 0
                                else:
                                    percent = int(((dbm + 90) / 60) * 100)
                                return f"{percent}% ({dbm} dBm)"
                            elif "/70" in line:
                                # Format: Signal level=40/70
                                parts = line.split("Signal level=")[1].split("/")[0]
                                level = int(parts)
                                percent = int((level / 70) * 100)
                                return f"{percent}%"
            except:
                pass

            return "Good Signal"
        except Exception as e:
            logger.error(f"Error getting signal strength: {e}")
            return "Unknown"

    def get_network_details(self) -> Dict[str, Any]:
        """Get detailed network information"""
        try:
            status = self._run_async(self.wifi_manager.get_connection_status())

            details = {
                "connected": status.connected if status else False,
                "ssid": status.ssid if status and status.ssid else "Not Connected",
                "ip_address": (
                    status.ip_address if status and status.ip_address else "No IP"
                ),
                "interface": (
                    status.interface if status and status.interface else "Unknown"
                ),
                "hostname": self._get_hostname(),
                "interfaces": self._get_all_interfaces(),
            }

            return details
        except Exception as e:
            logger.error(f"Error getting network details: {e}")
            return {
                "connected": False,
                "ssid": "Unknown",
                "ip_address": "Unknown",
                "interface": "Unknown",
                "hostname": "Unknown",
                "interfaces": [],
            }

    def _get_hostname(self) -> str:
        """Get system hostname"""
        try:
            return socket.gethostname()
        except:
            return "Unknown"

    def _get_all_interfaces(self) -> List[Dict[str, str]]:
        """Get all network interfaces"""
        interfaces = []
        try:
            result = subprocess.run(
                self._build_command(["ip", "addr", "show"]), capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                current_interface = None
                for line in result.stdout.split("\n"):
                    line = line.strip()
                    if line and line[0].isdigit() and ":" in line:
                        # New interface line
                        parts = line.split(":")
                        if len(parts) >= 2:
                            name = parts[1].strip()
                            if name != "lo":  # Skip loopback
                                current_interface = {
                                    "name": name,
                                    "type": (
                                        "ethernet"
                                        if name.startswith("eth")
                                        else (
                                            "wireless"
                                            if name.startswith("wl")
                                            else "other"
                                        )
                                    ),
                                    "ip_address": "no IP",
                                }
                    elif (
                        current_interface
                        and line.startswith("inet ")
                        and not line.startswith("inet 127.")
                    ):
                        # IP address line
                        ip_part = line.split()[1]
                        ip_address = ip_part.split("/")[0]
                        current_interface["ip_address"] = ip_address
                        interfaces.append(current_interface)
                        current_interface = None

                # Add interface without IP if it wasn't added
                if current_interface:
                    interfaces.append(current_interface)
        except Exception as e:
            logger.error(f"Error getting interfaces: {e}")

        return interfaces[:5]  # Limit to 5 interfaces
