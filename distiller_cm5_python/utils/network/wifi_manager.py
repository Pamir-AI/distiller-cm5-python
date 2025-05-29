#!/usr/bin/env python3
"""
WiFi Manager module for managing WiFi connections and hotspot.
"""

import os
import re
import time
import logging
import subprocess
import shutil
import platform
from typing import Dict, List, Tuple, Optional, Any
import asyncio

logger = logging.getLogger(__name__)


class WiFiManager:
    """
    WiFi Manager class for managing WiFi connections and hotspot.
    Uses nmcli to interact with NetworkManager on Linux.
    Uses airport and networksetup utilities on macOS.
    """

    # Default configuration for the hotspot
    DEFAULT_HOTSPOT_SSID = "DistillerSetup"
    DEFAULT_HOTSPOT_PASSWORD = "distiller123"  # min 8 chars

    def __init__(
        self,
        hotspot_ssid: str = DEFAULT_HOTSPOT_SSID,
        hotspot_password: str = DEFAULT_HOTSPOT_PASSWORD,
    ):
        """
        Initialize WiFi manager.

        Args:
            hotspot_ssid: SSID for the hotspot
            hotspot_password: Password for the hotspot
        """
        self.hotspot_ssid = hotspot_ssid
        self.hotspot_password = hotspot_password
        self.hotspot_connection_name = (
            "Hotspot"  # Use a fixed name for consistent detection
        )
        self.is_macos = platform.system() == "Darwin"
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Check if necessary dependencies are installed."""
        try:
            if self.is_macos:
                # Check for required macOS tools
                airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
                if not os.path.exists(airport_path):
                    logger.error("airport utility not found at expected location")
                    raise RuntimeError("airport utility not found")

                if not shutil.which("networksetup"):
                    logger.error("networksetup command not found")
                    raise RuntimeError("networksetup command not found")
            else:
                # Linux dependencies check
                nm_running = (
                    subprocess.run(
                        "systemctl is-active NetworkManager",
                        shell=True,
                        capture_output=True,
                        text=True,
                    ).stdout.strip()
                    == "active"
                )

                if not nm_running:
                    logger.error("NetworkManager is not running")
                    raise RuntimeError("NetworkManager is not running")

                if not shutil.which("nmcli"):
                    logger.error("nmcli command not found")
                    raise RuntimeError("nmcli command not found")

        except Exception as e:
            logger.error(f"Error checking dependencies: {str(e)}")
            raise

    def _run_command(self, command: str) -> Tuple[bool, str]:
        """
        Run a shell command and return success status and output.

        Args:
            command: Command to run

        Returns:
            Tuple of (success, output)
        """
        try:
            process = subprocess.run(
                command, shell=True, capture_output=True, text=True
            )
            if process.returncode == 0:
                return True, process.stdout.strip()
            else:
                logger.error(f"Command failed: {command}")
                logger.error(f"Error: {process.stderr.strip()}")
                return False, process.stderr.strip()
        except Exception as e:
            logger.error(f"Exception running command {command}: {str(e)}")
            return False, str(e)

    async def _run_command_async(self, command: str) -> Tuple[bool, str]:
        """
        Run a shell command asynchronously.

        Args:
            command: Command to run

        Returns:
            Tuple of (success, output)
        """
        try:
            process = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                return True, stdout.decode().strip()
            else:
                error_msg = stderr.decode().strip()
                logger.error(f"Command failed: {command}")
                logger.error(f"Error: {error_msg}")
                return False, error_msg
        except Exception as e:
            logger.error(f"Exception running command {command}: {str(e)}")
            return False, str(e)

    def get_wifi_interface(self) -> Optional[str]:
        """
        Get the WiFi interface name.

        Returns:
            WiFi interface name or None if not found
        """
        if self.is_macos:
            # On macOS, get the WiFi interface using networksetup
            success, output = self._run_command(
                "networksetup -listallhardwareports | grep -A 1 'Wi-Fi' | grep 'Device:' | awk '{print $2}'"
            )
            if success and output:
                logger.info(f"Found WiFi interface: {output}")
                return output
        else:
            # Linux approach
            # Get wireless interfaces using nmcli
            success, output = self._run_command(
                "nmcli -t -f DEVICE,TYPE device | grep ':wifi$' | cut -d: -f1"
            )
            if success and output:
                # Get the first WiFi interface found that is not a virtual interface
                for iface in output.split("\n"):
                    iface = iface.strip()
                    if (
                        iface
                        and not iface.startswith("docker")
                        and not iface.startswith("veth")
                        and not iface.startswith("br-")
                    ):
                        logger.info(f"Found WiFi interface: {iface}")
                        return iface

            # Try with ip link as a fallback
            success, output = self._run_command(
                "ip link show | grep -i 'wlan\\|wifi' | cut -d: -f2 | awk '{print $1}'"
            )
            if success and output:
                for iface in output.split("\n"):
                    iface = iface.strip()
                    if iface:
                        logger.info(f"Found WiFi interface with ip link: {iface}")
                        return iface

        logger.error("No WiFi interface found")
        return None

    def create_hotspot(self) -> bool:
        """
        Create a WiFi hotspot.

        Returns:
            True if hotspot was created successfully
        """
        try:
            # Get WiFi interface
            wifi_interface = self.get_wifi_interface()
            if not wifi_interface:
                logger.error("No WiFi interface found")
                return False

            logger.info(f"Creating hotspot on interface {wifi_interface}")

            if self.is_macos:
                # macOS implementation uses built-in Internet Sharing
                # Note: Full implementation requires user interaction in System Preferences
                # This is a limited implementation
                logger.error(
                    "Hotspot creation on macOS requires manual setup in System Preferences > Sharing > Internet Sharing"
                )
                return False
            else:
                # Linux implementation
                # Check if connection already exists and delete it
                self._run_command(
                    f"nmcli connection delete '{self.hotspot_connection_name}' 2>/dev/null || true"
                )

                # Use the built-in hotspot command
                command = (
                    f"nmcli device wifi hotspot ifname {wifi_interface} "
                    f"con-name '{self.hotspot_connection_name}' "
                    f"ssid '{self.hotspot_ssid}' "
                    f"password '{self.hotspot_password}'"
                )

                success, output = self._run_command(command)
                if not success:
                    logger.error(f"Failed to create hotspot: {output}")
                    return False

                logger.info(f"Hotspot '{self.hotspot_ssid}' started successfully")
                return True
        except Exception as e:
            logger.error(f"Error creating hotspot: {str(e)}")
            return False

    def stop_hotspot(self) -> bool:
        """
        Stop the WiFi hotspot.

        Returns:
            True if hotspot was stopped successfully
        """
        try:
            if self.is_macos:
                # macOS implementation - stopping Internet Sharing
                # This requires user interaction in System Preferences
                logger.error(
                    "Stopping hotspot on macOS requires manual deactivation in System Preferences > Sharing > Internet Sharing"
                )
                return False
            else:
                # Linux implementation
                # Check if the connection exists
                success, _ = self._run_command(
                    f"nmcli connection show | grep '{self.hotspot_connection_name}'"
                )
                if not success:
                    logger.info("No active hotspot connection found")
                    return True

                # Down the connection
                success, output = self._run_command(
                    f"nmcli connection down '{self.hotspot_connection_name}'"
                )
                if not success:
                    logger.error(f"Failed to stop hotspot: {output}")
                    return False

                # Delete the connection
                success, output = self._run_command(
                    f"nmcli connection delete '{self.hotspot_connection_name}'"
                )
                if not success:
                    logger.error(f"Failed to delete hotspot connection: {output}")
                    # Continue anyway, as the connection is already down

                logger.info("Hotspot stopped successfully")
                return True
        except Exception as e:
            logger.error(f"Error stopping hotspot: {str(e)}")
            return False

    def is_hotspot_active(self) -> bool:
        """
        Check if the hotspot is active.

        Returns:
            True if hotspot is active
        """
        try:
            if self.is_macos:
                # Check if Internet Sharing is enabled on macOS
                # This is a simplified check and may not be reliable
                result = subprocess.run(
                    "defaults read /Library/Preferences/SystemConfiguration/com.apple.nat | grep -i 'Enabled' | grep -i 'yes'",
                    shell=True,
                    capture_output=True,
                    text=True,
                )
                return result.returncode == 0
            else:
                # Linux implementation
                # Check if any hotspot connection is active - note: grep may return non-zero if nothing found
                result = subprocess.run(
                    "nmcli -t -f ACTIVE,NAME connection show | grep -i 'yes:.*hotspot'",
                    shell=True,
                    capture_output=True,
                    text=True,
                )
                # Success if grep found a match OR just no matches were found (grep returns 1)
                return result.returncode == 0 and "yes:" in result.stdout.lower()
        except Exception as e:
            logger.error(f"Error checking hotspot status: {str(e)}")
            return False

    def scan_networks(self) -> List[Dict[str, Any]]:
        """
        Scan for available WiFi networks.

        Returns:
            List of dictionaries with network information
        """
        # Get WiFi interface
        wifi_interface = self.get_wifi_interface()
        if not wifi_interface:
            logger.error("No WiFi interface found")
            return []

        if self.is_macos:
            # macOS implementation
            airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"

            # Trigger a scan
            self._run_command(f"{airport_path} --scan")

            # Get scan results
            success, output = self._run_command(f"{airport_path} --scan")
            if not success or not output:
                logger.error(f"Failed to scan networks")
                return []

            networks = []
            lines = output.strip().split("\n")
            if len(lines) > 1:  # Skip header line
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 5:
                        ssid = parts[0]
                        # Some SSIDs might be shown as <hidden network>
                        if ssid == "<hidden>" or ssid == "<hidden network>":
                            continue

                        try:
                            signal = int(parts[2])
                        except ValueError:
                            signal = 0

                        security = "none" if parts[6] == "NONE" else parts[6]

                        networks.append(
                            {"ssid": ssid, "signal": signal, "security": security}
                        )
        else:
            # Linux implementation
            # Trigger a scan
            self._run_command(f"nmcli device wifi rescan ifname {wifi_interface}")

            # Wait a bit for scan to complete
            time.sleep(2)

            # Get scan results
            success, output = self._run_command(
                f"nmcli -t -f SSID,SIGNAL,SECURITY device wifi list ifname {wifi_interface}"
            )
            if not success or not output:
                logger.error(f"Failed to scan networks: {output}")
                return []

            networks = []
            for line in output.strip().split("\n"):
                if not line:
                    continue

                parts = line.split(":")
                if len(parts) >= 3:
                    ssid = parts[0]
                    # Skip empty SSIDs or the current hotspot
                    if not ssid or ssid == self.hotspot_ssid:
                        continue

                    try:
                        signal = int(parts[1])
                    except ValueError:
                        signal = 0

                    security = "none" if not parts[2] else parts[2]

                    networks.append(
                        {"ssid": ssid, "signal": signal, "security": security}
                    )

        # Sort by signal strength
        networks.sort(key=lambda x: x["signal"], reverse=True)

        return networks

    def connect_to_network(
        self, ssid: str, password: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Connect to a WiFi network.

        Args:
            ssid: SSID of the network to connect to
            password: Password for the network (optional for open networks)

        Returns:
            Tuple of (success, error_message)
        """
        # Get WiFi interface
        wifi_interface = self.get_wifi_interface()
        if not wifi_interface:
            error_message = "No WiFi interface found"
            logger.error(error_message)
            return False, error_message

        logger.info(f"Using WiFi interface {wifi_interface} for connection")

        # Stop hotspot if active
        if self.is_hotspot_active():
            logger.info("Stopping hotspot before connecting to network")
            if not self.stop_hotspot():
                error_message = "Failed to stop hotspot before connecting to network"
                logger.error(error_message)
                return False, error_message

            # Wait for interface to become available
            time.sleep(2)

        # Forget existing connections with this SSID to avoid conflicts
        self.forget_network(ssid)

        if self.is_macos:
            # macOS implementation
            command = f"networksetup -setairportnetwork {wifi_interface} '{ssid}'"
            if password:
                command += f" '{password}'"

            logger.info(f"Connecting to network '{ssid}'")
            success, output = self._run_command(command)
        else:
            # Linux implementation
            # Standard connection approach
            command = f"nmcli device wifi connect '{ssid}'"
            if password:
                command += f" password '{password}'"
            command += f" ifname {wifi_interface}"

            logger.info(f"Connecting to network '{ssid}'")
            success, output = self._run_command(command)

        if success:
            logger.info(f"Successfully connected to '{ssid}'")
            return True, None
        else:
            error_message = f"Connection failed: {output}"
            logger.error(f"Failed to connect to '{ssid}': {output}")
            return False, error_message

    async def connect_to_network_async(
        self, ssid: str, password: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Connect to a WiFi network asynchronously.

        Args:
            ssid: SSID of the network to connect to
            password: Password for the network (optional for open networks)

        Returns:
            Tuple of (success, error_message)
        """
        # Get WiFi interface
        wifi_interface = self.get_wifi_interface()
        if not wifi_interface:
            error_message = "No WiFi interface found"
            logger.error(error_message)
            return False, error_message

        logger.info(f"Using WiFi interface {wifi_interface} for connection")

        # Stop hotspot if active
        if self.is_hotspot_active():
            logger.info("Stopping hotspot before connecting to network")
            if not self.stop_hotspot():
                error_message = "Failed to stop hotspot before connecting to network"
                logger.error(error_message)
                return False, error_message

            # Wait for interface to become available
            await asyncio.sleep(2)

        # Forget existing connections with this SSID to avoid conflicts
        self.forget_network(ssid)

        if self.is_macos:
            # macOS implementation
            command = f"networksetup -setairportnetwork {wifi_interface} '{ssid}'"
            if password:
                command += f" '{password}'"

            logger.info(f"Connecting to network '{ssid}'")
            success, output = await self._run_command_async(command)
        else:
            # Linux implementation
            # Standard connection approach
            command = f"nmcli device wifi connect '{ssid}'"
            if password:
                command += f" password '{password}'"
            command += f" ifname {wifi_interface}"

            logger.info(f"Connecting to network '{ssid}'")
            success, output = await self._run_command_async(command)

        if success:
            logger.info(f"Successfully connected to '{ssid}'")
            return True, None
        else:
            error_message = f"Connection failed: {output}"
            logger.error(f"Failed to connect to '{ssid}': {output}")
            return False, error_message

    def forget_network(self, ssid: str) -> bool:
        """
        Forget a saved WiFi network.

        Args:
            ssid: SSID of the network to forget

        Returns:
            True if the network was forgotten
        """
        if self.is_macos:
            # macOS implementation - remove preferred network
            command = f"networksetup -removepreferredwirelessnetwork {self.get_wifi_interface()} '{ssid}'"
            success, output = self._run_command(command)

            if success:
                logger.info(f"Network '{ssid}' forgotten successfully")
                return True
            else:
                logger.error(f"Failed to forget network '{ssid}': {output}")
                return False
        else:
            # Linux implementation
            # Get list of all connection names
            success, output = self._run_command(f"nmcli -t -f NAME connection show")
            if not success or not output:
                logger.error(f"Failed to get connection list")
                return False

            # Find and delete matching connections
            connections_deleted = False
            for connection_name in output.strip().split("\n"):
                if not connection_name:
                    continue

                # For each connection, check if it matches our SSID
                ssid_check, ssid_output = self._run_command(
                    f"nmcli -p connection show '{connection_name}' | grep '802-11-wireless.ssid' | awk '{{print $2}}'"
                )

                if ssid_check and ssid_output.strip() == ssid:
                    logger.info(
                        f"Deleting connection '{connection_name}' for SSID '{ssid}'"
                    )
                    self._run_command(f"nmcli connection delete '{connection_name}'")
                    connections_deleted = True

            if connections_deleted:
                logger.info(f"Network '{ssid}' forgotten successfully")
                return True
            else:
                logger.error(f"No saved connection found for '{ssid}'")
                return False

    def get_current_connection(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current WiFi connection.

        Returns:
            Dictionary with connection information or None if not connected
        """
        # Get WiFi interface
        wifi_interface = self.get_wifi_interface()
        if not wifi_interface:
            logger.error("No WiFi interface found")
            return None

        if self.is_macos:
            # macOS implementation
            airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"

            # Check if interface is connected
            success, output = self._run_command(f"{airport_path} -I")
            if (
                not success
                or "state: init" in output.lower()
                or "AirPort: Off" in output
            ):
                return None

            # Parse connection details
            ssid = None
            signal = 0

            for line in output.strip().split("\n"):
                if "SSID:" in line and not "BSSID:" in line:
                    ssid = line.split(":")[1].strip() if ":" in line else "Unknown"
                elif "agrCtlRSSI:" in line:
                    try:
                        signal = int(line.split(":")[1].strip())
                    except (ValueError, IndexError):
                        signal = 0

            # Get IP address
            success, output = self._run_command(f"ipconfig getifaddr {wifi_interface}")
            ip_address = output.strip() if success and output else "Unknown"

            if ssid:
                return {
                    "ssid": ssid,
                    "signal": signal,
                    "ip_address": ip_address,
                    "is_hotspot": False,  # No reliable way to detect if it's a hotspot on macOS
                }
            return None
        else:
            # Linux implementation
            # Check if interface is connected
            success, output = self._run_command(
                f"nmcli -t -f GENERAL.STATE device show {wifi_interface}"
            )
            if not success or "connected" not in output.lower():
                return None

            # Get connection details
            success, output = self._run_command(
                f"nmcli -t -f GENERAL.CONNECTION device show {wifi_interface}"
            )
            if not success or not output:
                return None

            connection_name = output.split(":")[1] if ":" in output else None

            # Skip if it's our hotspot
            if connection_name == self.hotspot_connection_name:
                return {"ssid": self.hotspot_ssid, "is_hotspot": True}

            # Get SSID using the connection's detailed information
            success, output = self._run_command(
                f"nmcli -p connection show '{connection_name}' | grep '802-11-wireless.ssid' | awk '{{print $2}}'"
            )
            ssid = output.strip() if success and output else "Unknown"

            # Get signal strength
            success, output = self._run_command(
                f"nmcli -f IN-USE,SIGNAL device wifi list | grep '*' | awk '{{print $2}}'"
            )
            signal = int(output) if success and output.isdigit() else 0

            # Get IP address
            success, output = self._run_command(
                f"nmcli -t -f IP4.ADDRESS device show {wifi_interface}"
            )
            ip_address = (
                output.split(":")[1] if success and ":" in output else "Unknown"
            )
            if ip_address != "Unknown":
                # Clean up CIDR notation
                ip_address = (
                    ip_address.split("/")[0] if "/" in ip_address else ip_address
                )

            return {
                "ssid": ssid,
                "signal": signal,
                "ip_address": ip_address,
                "is_hotspot": False,
            }

    def restart_networking(self) -> bool:
        """
        Restart networking services.

        Returns:
            True if restart was successful
        """
        logger.info("Restarting networking services")

        if self.is_macos:
            # macOS implementation
            # Toggle WiFi off and on
            wifi_interface = self.get_wifi_interface()
            if not wifi_interface:
                logger.error("No WiFi interface found")
                return False

            # Turn WiFi off
            success, output = self._run_command(
                f"networksetup -setairportpower {wifi_interface} off"
            )
            if not success:
                logger.error(f"Failed to turn off WiFi: {output}")
                return False

            # Wait a bit
            time.sleep(2)

            # Turn WiFi on
            success, output = self._run_command(
                f"networksetup -setairportpower {wifi_interface} on"
            )
            if not success:
                logger.error(f"Failed to turn on WiFi: {output}")
                return False

            logger.info("WiFi restarted successfully")
            return True
        else:
            # Linux implementation
            # Restart NetworkManager
            success, output = self._run_command("systemctl restart NetworkManager")
            if not success:
                logger.error(f"Failed to restart NetworkManager: {output}")
                return False

            # Wait for service to restart
            time.sleep(5)

            logger.info("Networking services restarted successfully")
            return True
