"""
WiFi Manager

Handles single-radio WiFi hardware limitation by properly managing
connection/disconnection sequences and state transitions.
"""

import asyncio
import logging
import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class NetworkInfo:
    """Network information container"""

    ssid: str
    signal: int
    security: str
    frequency: str
    in_use: bool = False


@dataclass
class ConnectionStatus:
    """Connection status container"""

    connected: bool
    ssid: Optional[str] = None
    interface: Optional[str] = None
    ip_address: Optional[str] = None


class WiFiManagerError(Exception):
    """WiFi Manager specific exceptions"""

    pass


class WiFiManager:
    """WiFi Manager with proper state transitions for single-radio devices"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._hotspot_active = False
        self._hotspot_connection_name = "distiller-setup-hotspot"
        self._original_connection = None  # Store original connection for restoration
        self.hotspot_ssid = None
        self.hotspot_password = None
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

    async def get_connection_status(self) -> ConnectionStatus:
        """Get current WiFi connection status"""
        try:
            cmd = self._build_command([
                "nmcli",
                "-t",
                "-f",
                "TYPE,DEVICE,STATE,NAME",
                "connection",
                "show",
                "--active",
            ])

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return ConnectionStatus(connected=False)

            # Parse active connections
            for line in stdout.decode().strip().split("\n"):
                if not line:
                    continue

                parts = line.split(":")
                if len(parts) >= 4 and parts[0] == "802-11-wireless":
                    device = parts[1]
                    state = parts[2]
                    connection = parts[3]

                    if state == "activated":
                        # Get actual SSID and IP address
                        actual_ssid = await self._get_device_ssid(device)
                        ip_address = await self._get_device_ip(device)

                        return ConnectionStatus(
                            connected=True,
                            ssid=actual_ssid if actual_ssid else connection,
                            interface=device,
                            ip_address=ip_address,
                        )

            return ConnectionStatus(connected=False)

        except Exception as e:
            self.logger.error(f"Status check error: {e}")
            return ConnectionStatus(connected=False)

    async def _get_device_ssid(self, device: str) -> Optional[str]:
        """Get SSID of connected device"""
        try:
            # First try to get the connection name
            cmd = self._build_command(["nmcli", "-t", "-f", "GENERAL.CONNECTION", "device", "show", device])
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                connection_name = stdout.decode().strip().split(":")[-1]
                if connection_name and connection_name != "--":
                    return connection_name

            # Fallback: Try to get SSID directly from wireless properties
            cmd = self._build_command([
                "nmcli",
                "-t",
                "-f",
                "GENERAL.WIFI-PROPERTIES.SSID",
                "device",
                "show",
                device,
            ])
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                ssid = stdout.decode().strip().split(":")[-1]
                if ssid and ssid != "--":
                    return ssid

            # Another fallback: Use iwgetid if available
            try:
                cmd = self._build_command(["iwgetid", device, "--raw"])
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()

                if process.returncode == 0:
                    ssid = stdout.decode().strip()
                    if ssid:
                        return ssid
            except FileNotFoundError:
                pass  # iwgetid not available

            return None

        except Exception:
            return None

    async def _get_device_ip(self, device: str) -> Optional[str]:
        """Get IP address of device"""
        try:
            cmd = self._build_command(["ip", "addr", "show", device])
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                output = stdout.decode()
                # Look for inet line
                for line in output.split("\n"):
                    line = line.strip()
                    if line.startswith("inet ") and not line.startswith("inet 127."):
                        # Extract IP address
                        ip_part = line.split()[1]
                        ip_address = ip_part.split("/")[0]
                        return ip_address
            return None

        except Exception:
            return None

    async def get_available_networks(self) -> list[NetworkInfo]:
        """Scan for available WiFi networks"""
        try:
            # Trigger fresh scan
            cmd = self._build_command(["nmcli", "device", "wifi", "rescan"])
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()

            # Allow scan to complete
            await asyncio.sleep(2)

            # Get scan results
            cmd = self._build_command([
                "nmcli",
                "-t",
                "-f",
                "SSID,SIGNAL,SECURITY,FREQ,IN-USE",
                "device",
                "wifi",
                "list",
            ])
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                self.logger.error(f"WiFi scan failed: {stderr.decode()}")
                return []

            networks = []
            seen_ssids = set()

            for line in stdout.decode().strip().split("\n"):
                if not line:
                    continue

                parts = line.split(":")
                if len(parts) >= 4:
                    ssid = parts[0]
                    signal = int(parts[1]) if parts[1].isdigit() else 0
                    security_field = parts[2]
                    frequency = parts[3]
                    in_use = parts[4] == "*" if len(parts) > 4 else False

                    # Better security detection
                    if security_field and security_field.strip():
                        # If security field has content, it's encrypted
                        security = "encrypted"
                    else:
                        # Empty security field means open network
                        security = "open"

                    # Skip empty SSIDs and duplicates (choose strongest signal)
                    if ssid and ssid not in seen_ssids:
                        networks.append(
                            NetworkInfo(
                                ssid=ssid,
                                signal=signal,
                                security=security,
                                frequency=frequency,
                                in_use=in_use,
                            )
                        )
                        seen_ssids.add(ssid)

            # Sort by signal strength
            networks.sort(key=lambda x: x.signal, reverse=True)
            self.logger.info(f"Found {len(networks)} WiFi networks")
            return networks

        except Exception as e:
            self.logger.error(f"Network scan failed: {e}")
            return []

    async def disconnect_current_wifi(self) -> bool:
        """Disconnect from current WiFi connection"""
        try:
            # Get current connection
            status = await self.get_connection_status()
            if not status.connected:
                self.logger.info("No active WiFi connection to disconnect")
                return True

            # Store current connection for potential restoration
            self._original_connection = status.ssid
            self.logger.info(f"Disconnecting from {status.ssid}")

            # Disconnect using device interface
            cmd = self._build_command(["nmcli", "device", "disconnect", status.interface])
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await process.communicate()

            if process.returncode == 0:
                self.logger.info("WiFi disconnected successfully")
                # Wait for disconnection to complete
                await asyncio.sleep(2)
                return True
            else:
                self.logger.error(f"Failed to disconnect WiFi: {stderr.decode()}")
                return False

        except Exception as e:
            self.logger.error(f"Error disconnecting WiFi: {e}")
            return False

    async def get_hotspot_ip(self) -> Optional[str]:
        """Get the actual IP address of the hotspot interface"""
        try:
            if not self._hotspot_active:
                return None

            # Get active connections to find the hotspot interface
            cmd = self._build_command([
                "nmcli",
                "-t",
                "-f",
                "TYPE,DEVICE,STATE,NAME",
                "connection",
                "show",
                "--active",
            ])

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return None

            # Find the hotspot connection and get its device
            for line in stdout.decode().strip().split("\n"):
                if not line:
                    continue

                parts = line.split(":")
                if len(parts) >= 4:
                    conn_type = parts[0]
                    device = parts[1]
                    state = parts[2]
                    name = parts[3]

                    if (
                        conn_type == "802-11-wireless"
                        and state == "activated"
                        and name == self._hotspot_connection_name
                    ):
                        # Found the hotspot connection, get its IP
                        return await self._get_device_ip(device)

            return None

        except Exception as e:
            self.logger.error(f"Error getting hotspot IP: {e}")
            return None

    async def start_hotspot(
        self, ssid: str, password: str
    ) -> tuple[bool, Optional[str]]:
        """Start WiFi hotspot with proper state management

        Returns:
            tuple: (success: bool, ip_address: Optional[str])
        """
        try:
            self.logger.info(f"Starting hotspot: {ssid}")

            # Step 1: Disconnect from current WiFi if connected
            current_status = await self.get_connection_status()
            if current_status.connected:
                self.logger.info(
                    "Disconnecting from current WiFi before starting hotspot"
                )
                if not await self.disconnect_current_wifi():
                    raise WiFiManagerError("Failed to disconnect from current WiFi")

            # Step 2: Clean up any existing hotspot
            await self._cleanup_hotspot_connection()

            # Step 3: Store hotspot configuration
            self.hotspot_ssid = ssid
            self.hotspot_password = password

            # Step 4: Create and configure hotspot connection
            success = await self._create_and_activate_hotspot(ssid, password)

            if success:
                self._hotspot_active = True

                # Get the actual IP address
                ip_address = await self.get_hotspot_ip()
                if ip_address:
                    self.logger.info(
                        f"Hotspot '{ssid}' started successfully at {ip_address}"
                    )
                    return True, ip_address
                else:
                    self.logger.warning(
                        f"Hotspot '{ssid}' started but could not determine IP address"
                    )
                    return True, "localhost"  # Fallback to standard IP
            else:
                await self._cleanup_hotspot_connection()
                raise WiFiManagerError("Failed to activate hotspot")

        except Exception as e:
            self.logger.error(f"Hotspot start error: {e}")
            await self._cleanup_hotspot_connection()
            if isinstance(e, WiFiManagerError):
                raise
            raise WiFiManagerError(f"Failed to start hotspot: {e}")

    async def _create_and_activate_hotspot(self, ssid: str, password: str) -> bool:
        """Create and activate hotspot connection"""
        try:
            # Create hotspot connection
            cmd = self._build_command([
                "nmcli",
                "connection",
                "add",
                "type",
                "wifi",
                "ifname",
                "*",
                "con-name",
                self._hotspot_connection_name,
                "autoconnect",
                "no",
                "ssid",
                ssid,
            ])

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()

            if process.returncode != 0:
                return False

            # Configure hotspot settings
            config_commands = [
                self._build_command([
                    "nmcli",
                    "connection",
                    "modify",
                    self._hotspot_connection_name,
                    "802-11-wireless.mode",
                    "ap",
                ]),
                self._build_command([
                    "nmcli",
                    "connection",
                    "modify",
                    self._hotspot_connection_name,
                    "802-11-wireless.band",
                    "bg",
                ]),
                self._build_command([
                    "nmcli",
                    "connection",
                    "modify",
                    self._hotspot_connection_name,
                    "ipv4.method",
                    "shared",
                ]),
                self._build_command([
                    "nmcli",
                    "connection",
                    "modify",
                    self._hotspot_connection_name,
                    "ipv4.addresses",
                    "192.168.4.1/24",
                ]),
            ]

            # Add security if password provided
            if password:
                config_commands.extend(
                    [
                        self._build_command([
                            "nmcli",
                            "connection",
                            "modify",
                            self._hotspot_connection_name,
                            "802-11-wireless-security.key-mgmt",
                            "wpa-psk",
                        ]),
                        self._build_command([
                            "nmcli",
                            "connection",
                            "modify",
                            self._hotspot_connection_name,
                            "802-11-wireless-security.psk",
                            password,
                        ]),
                    ]
                )

            # Apply all configurations
            for cmd in config_commands:
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()

                if process.returncode != 0:
                    self.logger.error(f"Failed to configure: {' '.join(cmd)}")
                    return False

            # Activate the hotspot
            cmd = self._build_command(["nmcli", "connection", "up", self._hotspot_connection_name])
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await process.communicate()

            if process.returncode == 0:
                # Wait for activation to complete
                await asyncio.sleep(3)
                return True
            else:
                self.logger.error(f"Hotspot activation failed: {stderr.decode()}")
                return False

        except Exception as e:
            self.logger.error(f"Error creating hotspot: {e}")
            return False

    async def stop_hotspot(self) -> bool:
        """Stop WiFi hotspot"""
        try:
            if not self._hotspot_active:
                self.logger.info("No hotspot active to stop")
                return True

            self.logger.info("Stopping hotspot")

            # Deactivate and remove hotspot connection
            cmds = [
                self._build_command(["nmcli", "connection", "down", self._hotspot_connection_name]),
                self._build_command(["nmcli", "connection", "delete", self._hotspot_connection_name]),
            ]

            for cmd in cmds:
                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()

            self._hotspot_active = False
            self.hotspot_ssid = None
            self.hotspot_password = None

            # Wait for interface to be ready for client mode
            await asyncio.sleep(2)

            self.logger.info("Hotspot stopped successfully")
            return True

        except Exception as e:
            self.logger.error(f"Hotspot stop error: {e}")
            return False

    async def connect_to_network(self, ssid: str, password: str = "") -> bool:
        """Connect to a WiFi network with proper hotspot management"""
        try:
            self.logger.info(f"Connecting to network: {ssid}")

            # Step 1: Check if network exists and get its details
            networks = await self.get_available_networks()
            target_network = None
            for net in networks:
                if net.ssid == ssid:
                    target_network = net
                    break

            if target_network:
                self.logger.info(
                    f"Found target network '{ssid}': signal={target_network.signal}%, security={target_network.security}"
                )

                # Check if password is needed
                if target_network.security != "open" and not password:
                    self.logger.error(
                        f"Network '{ssid}' requires a password but none provided"
                    )
                    return False
            else:
                self.logger.warning(f"Network '{ssid}' not found in scan results")
                self.logger.info(
                    f"Available networks: {[net.ssid for net in networks]}"
                )
                # Continue anyway - network might be hidden

            # Step 2: Stop hotspot if active
            if self._hotspot_active:
                self.logger.info("Stopping hotspot before connecting to network")
                if not await self.stop_hotspot():
                    self.logger.warning("Failed to stop hotspot, continuing anyway")

            # Step 3: Remove any existing connection with same SSID
            await self._remove_existing_connection(ssid)

            # Step 4: Connect to network
            success = await self._perform_network_connection(ssid, password)

            if success:
                self.logger.info(f"Successfully connected to {ssid}")
                # Clear original connection since we're now connected to new network
                self._original_connection = None
                return True
            else:
                self.logger.error(f"Failed to connect to {ssid}")
                # Don't restore hotspot here - let the service decide
                return False

        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False

    async def _perform_network_connection(self, ssid: str, password: str = "") -> bool:
        """Perform the actual network connection"""
        try:
            self.logger.info(
                f"Attempting to connect to '{ssid}' with password: {'***' if password else 'None'}"
            )

            if password:
                # Use --ask flag for password authentication
                cmd = self._build_command(["nmcli", "--ask", "device", "wifi", "connect", ssid])
                self.logger.debug(
                    f"Running command: {' '.join(cmd[:-1])} [password hidden]"
                )

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                # Provide password
                password_input = f"{password}\n"
                _, stderr = await process.communicate(input=password_input.encode())
            else:
                # Open network
                cmd = self._build_command(["nmcli", "device", "wifi", "connect", ssid])
                self.logger.debug(f"Running command: {' '.join(cmd)}")

                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                _, stderr = await process.communicate()

            # Log only errors in production
            if process.returncode != 0 and stderr:
                self.logger.warning(f"nmcli error: {stderr.decode().strip()}")

            if process.returncode == 0:
                self.logger.info(
                    "nmcli connect command succeeded, waiting for connection to establish..."
                )

                # Wait longer for connection to establish and check more thoroughly
                max_attempts = 20  # Increased from 15 to 20 seconds
                for attempt in range(max_attempts):
                    await asyncio.sleep(1)
                    status = await self.get_connection_status()

                    # More robust connection verification
                    if status.connected:
                        # Check if we're connected to the target network
                        # Handle cases where NetworkManager appends numbers (e.g., "Network 1", "Network 2")
                        if status.ssid and (status.ssid == ssid or status.ssid.startswith(ssid + " ")):
                            self.logger.info(
                                f"Successfully connected to '{ssid}' (detected as '{status.ssid}') at {status.ip_address} (attempt {attempt + 1})"
                            )
                            return True
                        elif status.ssid:
                            pass  # Connected to different network
                        else:
                            pass  # Connected but SSID not detected
                    else:
                        pass  # Not connected yet

                # Final verification with additional checks
                status = await self.get_connection_status()

                # If we're connected but SSID doesn't match exactly, try flexible matching
                if status.connected and status.ssid and (status.ssid == ssid or status.ssid.startswith(ssid + " ")):
                    self.logger.info(
                        f"Successfully connected to '{ssid}' (detected as '{status.ssid}') at {status.ip_address}"
                    )
                    return True
                elif status.connected and status.ssid != ssid:
                    # Check if the connection profile was created and is active
                    connection_active = await self._verify_connection_by_profile(ssid)
                    if connection_active:
                        self.logger.info(
                            f"Connection verified by profile check - connected to '{ssid}'"
                        )
                        return True

                # Additional verification: Check if a connection profile exists and try to get its status
                profile_active = await self._verify_connection_by_profile(ssid)
                if profile_active:
                    self.logger.info(
                        f"Connection verified by profile check - connected to '{ssid}'"
                    )
                    return True

                # Final check with flexible SSID matching
                if status.connected and status.ssid and (status.ssid == ssid or status.ssid.startswith(ssid + " ")):
                    self.logger.info(
                        f"Successfully connected to '{ssid}' (detected as '{status.ssid}') at {status.ip_address}"
                    )
                    return True
                else:
                    self.logger.warning(
                        f"Connection verification failed after {max_attempts} attempts"
                    )
                    self.logger.warning(
                        f"Final status: connected={status.connected}, ssid={status.ssid}"
                    )

                    # One more check with device-level verification
                    device_connected = await self._verify_device_connection(ssid)
                    if device_connected:
                        self.logger.info(
                            f"Connection verified by device check - connected to '{ssid}'"
                        )
                        return True

                    return False
            else:
                error_msg = stderr.decode().strip()
                self.logger.error(
                    f"nmcli connection failed with exit code {process.returncode}: {error_msg}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Network connection error: {e}")
            return False

    async def _verify_connection_by_profile(self, ssid: str) -> bool:
        """Verify connection by checking if the connection profile is active"""
        try:
            cmd = self._build_command(["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"])
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                for line in stdout.decode().strip().split("\n"):
                    if line:
                        parts = line.split(":")
                        if len(parts) >= 2 and parts[1]:  # Device field is not empty
                            # Check for exact match or SSID with appended number
                            connection_name = parts[0]
                            if connection_name == ssid or connection_name.startswith(ssid + " "):
                                return True

            return False

        except Exception:
            return False

    async def _verify_device_connection(self, ssid: str) -> bool:
        """Verify connection by checking device WiFi properties directly"""
        try:
            # Get WiFi device
            cmd = self._build_command(["nmcli", "-t", "-f", "DEVICE,TYPE", "device", "status"])
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return False

            wifi_device = None
            for line in stdout.decode().strip().split("\n"):
                if line:
                    parts = line.split(":")
                    if len(parts) >= 2 and parts[1] == "wifi":
                        wifi_device = parts[0]
                        break

            if not wifi_device:
                return False

            # Check if device is connected to our target SSID
            cmd = self._build_command(["iwgetid", wifi_device, "--raw"])
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()

            if process.returncode == 0:
                current_ssid = stdout.decode().strip()
                # Check for exact match or SSID with appended number  
                if current_ssid == ssid or current_ssid.startswith(ssid + " "):
                    return True

            return False

        except Exception:
            return False

    async def _remove_existing_connection(self, ssid: str):
        """Remove any existing connection profile for the SSID"""
        try:
            cmd = self._build_command(["nmcli", "connection", "delete", ssid])
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            # Don't check return code - it's OK if connection doesn't exist

        except Exception:
            pass  # Ignore errors - connection might not exist

    async def _cleanup_hotspot_connection(self):
        """Clean up hotspot connection"""
        try:
            cmd = self._build_command(["nmcli", "connection", "delete", self._hotspot_connection_name])
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
        except Exception:
            pass  # Ignore cleanup errors

    async def restore_original_connection(self) -> bool:
        """Restore the original WiFi connection if available"""
        try:
            if not self._original_connection:
                self.logger.info("No original connection to restore")
                return False

            self.logger.info(
                f"Attempting to restore connection to {self._original_connection}"
            )

            # Try to reconnect to original network
            cmd = self._build_command(["nmcli", "connection", "up", self._original_connection])
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await process.communicate()

            if process.returncode == 0:
                self.logger.info(f"Restored connection to {self._original_connection}")
                self._original_connection = None
                return True
            else:
                self.logger.warning(f"Failed to restore connection: {stderr.decode()}")
                return False

        except Exception as e:
            self.logger.error(f"Error restoring connection: {e}")
            return False

    def is_hotspot_active(self) -> bool:
        """Check if hotspot is currently active"""
        return self._hotspot_active

    def get_original_connection(self) -> Optional[str]:
        """Get the original connection name before hotspot was started"""
        return self._original_connection
