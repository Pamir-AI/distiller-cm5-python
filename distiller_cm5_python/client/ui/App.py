from PyQt6.QtCore import QUrl, pyqtSignal, pyqtSlot, QObject, QTimer
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QApplication


from contextlib import AsyncExitStack
from datetime import datetime
from qasync import QEventLoop, asyncSlot
import asyncio
import os
import sys
import importlib.util
import subprocess
import re

from distiller_cm5_python.client.mid_layer.mcp_client import MCPClient
from distiller_cm5_python.client.ui.AppInfoManager import AppInfoManager
from distiller_cm5_python.utils.config import *
from distiller_cm5_python.utils.logger import logger, setup_logging


class MCPClientBridge(QObject):
    conversationChanged = pyqtSignal()  # Signal for conversation changes
    logLevelChanged = pyqtSignal(str)  # Signal for logging level changes
    statusChanged = pyqtSignal(str)  # Signal for status changes
    availableServersChanged = pyqtSignal(list)  # Signal for available servers list
    isConnectedChanged = pyqtSignal(bool)  # Signal for connection status
    responseStopped = pyqtSignal()  # Signal for when response is stopped

    # Status constants
    STATUS_INITIALIZING = "Initializing..."
    STATUS_CONNECTING = "Connecting to server..."
    STATUS_CONNECTED = "Connected to {server_name}"
    STATUS_DISCONNECTED = "Disconnected"
    STATUS_PROCESSING = "Processing query..."
    STATUS_STREAMING = "Streaming response..."
    STATUS_IDLE = "Ready"
    STATUS_ERROR = "Error: {error}"
    STATUS_CONFIG_APPLIED = "Configuration applied successfully"
    STATUS_SHUTTING_DOWN = "Shutting down..."

    def __init__(self, parent=None):
        """MCPClientBridge initializes the MCPClient and manages the conversation state."""
        super().__init__(parent=parent)
        self._conversation = []
        self._status = self.STATUS_INITIALIZING
        self._current_streaming_message = None
        self._is_connected = False
        self._loop = asyncio.get_event_loop()
        self._stop_requested = False  # Add flag to track stop requests
        self.config_path = "./"
        self._current_log_level = (
            config.get("logging", "level").upper()
            if config.get("logging", "level")
            else "DEBUG"
        )
        self._available_servers = []
        self._selected_server_path = None
        self.client = None  # Will be initialized when a server is selected

    @property
    def is_connected(self):
        """Return the connection status"""
        return self._is_connected

    @is_connected.setter
    def is_connected(self, value):
        """Set the connection status and emit the signal"""
        if self._is_connected != value:
            self._is_connected = value
            self.isConnectedChanged.emit(value)

    def _update_status(self, status: str, **kwargs):
        """Update the status and emit the statusChanged signal"""
        self._status = status.format(**kwargs)
        self.statusChanged.emit(self._status)
        logger.info(f"Status updated: {self._status}")

    async def initialize(self):
        """Initialize the client and connect to the server"""
        self._update_status(self.STATUS_INITIALIZING)
        await self.connect_to_server()

    @pyqtSlot(result=str)
    def get_status(self):
        """Return the current status of the client"""
        return self._status

    @pyqtSlot(result=list)
    def get_conversation(self):
        """Return the current conversation as a list of formatted messages"""
        return self._conversation

    @asyncSlot(str)
    async def submit_query(self, query: str):
        """Submit a query to the server and update the conversation"""
        if not query.strip():
            return
        if not self._is_connected:
            message = {
                "timestamp": self.get_timestamp(),
                "content": "ERROR: Not connected",
            }
            self._conversation.append(message)
            self.conversationChanged.emit()
            logger.error("Query submitted before server connection established")
            return

        # Add user message
        user_message = {"timestamp": self.get_timestamp(), "content": f"You: {query}"}
        self._conversation.append(user_message)
        logger.info(f"User query added to conversation: {query}")
        self.conversationChanged.emit()
        await self.process_query(query)

    @pyqtSlot()
    def clear_conversation(self):
        """Clear the conversation history"""
        self._conversation = []
        clear_message = {
            "timestamp": self.get_timestamp(),
            "content": "Conversation cleared.",
        }
        self._conversation.append(clear_message)
        logger.info("Conversation cleared")
        self.conversationChanged.emit()

    @pyqtSlot(bool)
    def toggle_streaming(self, enabled: bool):
        """Enable or disable streaming mode, streaming here refers to the ability to receive partial responses from the server."""
        if self.client is None:
            logger.error("Client is not initialized")
            return
        self.client.streaming = enabled
        self.client.llm_provider.streaming = enabled
        status = "enabled" if enabled else "disabled"
        self._status = f"Streaming {status}"
        self._conversation.append(f"[{self.get_timestamp()}] Streaming {status}")
        logger.info(f"Streaming {status}")
        self.conversationChanged.emit()

    @pyqtSlot(str, str, result="QVariant")
    def getConfigValue(self, section: str, key: str) -> str:
        """Get a configuration value, always returning a string."""
        value = config.get(section, key)
        logger.debug(
            f"Getting config value for {section}.{key}: {value} (type: {type(value)})"
        )
        if value is None:
            logger.debug(f"Value is None, returning empty string")
            return ""
        elif isinstance(value, list):
            if key == "stop":
                # For stop sequences, escape special characters for QML
                return "\n".join(
                    str(v).encode("unicode_escape").decode("utf-8") for v in value
                )
            return ",".join(str(v) for v in value)
        elif section == "logging" and key == "level":
            # Return the current log level in uppercase
            return self._current_log_level
        result = str(value)
        logger.debug(f"Final value: {result}")
        return result

    @pyqtSlot(str, str, "QVariant")
    def setConfigValue(self, section: str, key: str, value):
        """Set a configuration value."""
        if key == "stop" and isinstance(value, str):
            # For stop sequences, escape special characters for QML
            value = [
                v.encode("utf-8").decode("unicode_escape")
                for v in value.split("\n")
                if v
            ]
        elif key in ["timeout", "top_k", "n_ctx", "max_tokens", "streaming_chunk_size"]:
            value = int(value) if value != "" else 0
        elif key in ["temperature", "top_p", "repetition_penalty"]:
            value = float(value) if value != "" else 0.0
        elif key == "streaming" or key == "file_enabled":
            value = bool(value)
        elif section == "logging" and key == "level":
            value = value.upper()
        else:
            config.set(section, key, value)

    @asyncSlot()
    async def applyConfig(self):
        """Apply configuration changes by restarting the client."""
        try:
            self._update_status(self.STATUS_INITIALIZING)
            self._conversation.append(
                f"[{self.get_timestamp()}] Applying configuration changes..."
            )
            self.conversationChanged.emit()

            # Store the current conversation
            current_conversation = self._conversation.copy()

            # Clean up existing client
            if self.client:
                self._conversation.append(
                    f"[{self.get_timestamp()}] Disconnecting from server..."
                )
                self.conversationChanged.emit()

                # First attempt - normal cleanup
                try:
                    cleanup_task = asyncio.create_task(self.client.cleanup())
                    await asyncio.wait_for(cleanup_task, timeout=5.0)
                    await asyncio.sleep(1)
                except asyncio.TimeoutError:
                    self._conversation.append(
                        f"[{self.get_timestamp()}] Cleanup is taking longer than expected, forcing disconnect..."
                    )
                    self.conversationChanged.emit()
                except Exception as cleanup_error:
                    logger.error(
                        f"Error during client cleanup: {cleanup_error}", exc_info=True
                    )
                    self._conversation.append(
                        f"[{self.get_timestamp()}] Cleanup warning: {str(cleanup_error)}"
                    )
                    self.conversationChanged.emit()

                # Ensure client is fully reset regardless of cleanup success
                self.client = None
                self._is_connected = False

            # Extra delay to ensure all resources are released
            await asyncio.sleep(1.0)

            # Reload the configuration from file
            self._conversation.append(
                f"[{self.get_timestamp()}] Reloading configuration..."
            )
            self.conversationChanged.emit()
            config.reload()

            # Add a small delay after config reload
            await asyncio.sleep(0.5)

            # Update global variables after config reload
            global SERVER_URL, MODEL_NAME, PROVIDER_TYPE, API_KEY, TIMEOUT, STREAMING_ENABLED
            SERVER_URL = config.get("llm", "server_url")
            MODEL_NAME = config.get("llm", "model_name")
            PROVIDER_TYPE = config.get("llm", "provider_type")
            API_KEY = config.get("llm", "api_key")
            TIMEOUT = config.get("llm", "timeout")
            STREAMING_ENABLED = config.get("llm", "streaming")

            # Create new client with updated config
            self._conversation.append(
                f"[{self.get_timestamp()}] Creating new client with updated configuration..."
            )
            self.conversationChanged.emit()
            self.client = MCPClient(
                streaming=STREAMING_ENABLED,
                llm_server_url=SERVER_URL,
                model=MODEL_NAME,
                provider_type=PROVIDER_TYPE,
                api_key=API_KEY,
                timeout=TIMEOUT,
            )

            # Restore the conversation
            self._conversation = current_conversation

            # Add a small delay before connecting to server
            await asyncio.sleep(1.0)

            # Initialize and connect to the server
            self._conversation.append(
                f"[{self.get_timestamp()}] Connecting to server with new configuration..."
            )
            self.conversationChanged.emit()

            # Set a longer timeout for connection
            success = False
            for attempt in range(2):  # Try up to 2 times
                try:
                    connect_task = self.connect_to_server()
                    await asyncio.wait_for(connect_task, timeout=10)
                    success = self._is_connected
                    if success:
                        break
                    else:
                        self._conversation.append(
                            f"[{self.get_timestamp()}] Connection attempt {attempt+1} failed, retrying..."
                        )
                        self.conversationChanged.emit()
                        await asyncio.sleep(2)
                except asyncio.TimeoutError:
                    self._conversation.append(
                        f"[{self.get_timestamp()}] Connection attempt {attempt+1} timed out, retrying..."
                    )
                    self.conversationChanged.emit()
                    await asyncio.sleep(2)
                except Exception as e:
                    self._conversation.append(
                        f"[{self.get_timestamp()}] Connection error: {str(e)}"
                    )
                    self.conversationChanged.emit()
                    await asyncio.sleep(2)

            # Only update the status if we successfully connected
            if success:
                self._update_status(self.STATUS_CONFIG_APPLIED)
                self._conversation.append(
                    f"[{self.get_timestamp()}] Client reconnected with new configuration."
                )
                self.conversationChanged.emit()
            else:
                error_msg = "Failed to connect after multiple attempts"
                self._update_status(self.STATUS_ERROR, error=error_msg)
                self._conversation.append(
                    f"[{self.get_timestamp()}] ERROR: {error_msg}"
                )
                self.conversationChanged.emit()

        except Exception as e:
            self._update_status(self.STATUS_ERROR, error=str(e))
            logger.error(f"Error applying configuration: {e}", exc_info=True)
            self._conversation.append(
                f"[{self.get_timestamp()}] ERROR: Failed to apply configuration: {str(e)}"
            )
            self.conversationChanged.emit()

    @pyqtSlot()
    def saveConfigToFile(self):
        """Save the current configuration."""
        config.save_to_file(self.config_path)
        logger.info(f"Configuration saved to {self.config_path}")

    async def connect_to_server(self):
        """Connect to the server and update the conversation"""

        # If we have a selected server path, use that instead of config
        server_script_path = self._selected_server_path

        # Otherwise fall back to config
        if not server_script_path:
            server_script_path = MCP_SERVER_SCRIPT_PATH

        if not server_script_path:
            self._conversation.append(
                f"[{self.get_timestamp()}] ERROR: No server script path provided."
            )
            self.conversationChanged.emit()
            self._update_status(
                self.STATUS_ERROR, error="No server script path provided"
            )
            return

        # Ensure the server script path is absolute
        if not os.path.isabs(server_script_path):
            server_script = os.path.join(
                os.path.dirname(__file__), "../../", server_script_path
            )
        else:
            server_script = server_script_path

        self._update_status(self.STATUS_CONNECTING)
        try:
            success = await self.client.connect_to_server(server_script)
            if success:
                # Always use the actual server name from client.server_name
                actual_server_name = self.client.server_name if hasattr(self.client, 'server_name') else "Unknown"

                self._conversation.append(
                    f"[{self.get_timestamp()}] Connected to server successfully."
                )
                # Use the actual name in the status message
                self._update_status(
                    self.STATUS_CONNECTED, server_name=actual_server_name
                )
                self._is_connected = True
                self.is_connected = True  # Use property setter for signal emission
                logger.info(f"Connected to server: {actual_server_name}")
            else:
                self._conversation.append(
                    f"[{self.get_timestamp()}] Failed to connect to server."
                )
                self._update_status(self.STATUS_ERROR, error="Connection failed")
                self.is_connected = False
        except Exception as e:
            self._conversation.append(
                f"[{self.get_timestamp()}] Failed to connect to server: {str(e)}"
            )
            self._update_status(self.STATUS_ERROR, error=str(e))
            self.is_connected = False
        self.conversationChanged.emit()

    async def process_query(self, query: str):
        """Process the query and update the conversation"""
        if not self._is_connected:
            self._update_status(self.STATUS_ERROR, error="Not connected to server")
            return

        self._update_status(self.STATUS_PROCESSING)
        # Reset stop flag at the beginning of a new query
        self._stop_requested = False

        if self.client is None:
            logger.error("Client is not initialized")
            self._update_status(self.STATUS_ERROR, error="Client is not initialized")
            return

        try:
            # Add user message to conversation
            timestamp = self.get_timestamp()
            self._conversation.append(f"[{timestamp}] You: {query}")
            self.conversationChanged.emit()

            # Create stream handler
            if self.client.streaming:
                # Initialize streaming message
                timestamp = self.get_timestamp()
                stream_index = len(self._conversation)
                self._conversation.append(f"[{timestamp}] Assistant: ")
                self.conversationChanged.emit()
                self._update_status(self.STATUS_STREAMING)

                # Define streaming chunk handler
                def on_stream_chunk(chunk):
                    # Skip updating the UI if stop was requested
                    if self._stop_requested:
                        logger.debug(f"Ignoring streaming chunk after stop: {chunk[:20]}...")
                        return

                    if stream_index < len(self._conversation):
                        # Append chunk to existing message
                        self._conversation[stream_index] += chunk
                        # Signal the model has changed
                        self.conversationChanged.emit()
                        logger.debug(f"Streaming chunk received: {chunk[:20]}...")

                # Process query with streaming
                await self.client.process_query(query, on_stream_chunk)
            else:
                # Define non-streaming handler
                def on_response(response):
                    timestamp = self.get_timestamp()
                    self._conversation.append(f"[{timestamp}] Assistant: {response}")
                    self.conversationChanged.emit()
                    logger.debug(f"Full response received: {response[:50]}...")

                # Process query without streaming
                await self.client.process_query(query, on_response)

            self._update_status(self.STATUS_IDLE)
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            self._update_status(self.STATUS_ERROR, error=str(e))
            self._conversation.append(f"[{self.get_timestamp()}] Error: {str(e)}")
            self.conversationChanged.emit()

    def get_timestamp(self) -> str:
        """Get the current timestamp formatted as a string"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async def cleanup(self):
        """Cleanup the client and close the connection"""
        try:
            self._update_status(self.STATUS_SHUTTING_DOWN)
            if hasattr(self, "bridge") and self.bridge is not None:
                self.conversationChanged.emit()

            if self.client:
                # Ensure cleanup is called in the same task
                # check if there is any running loop
                await self.client.cleanup()
                self.client = None

            logger.debug("Cleanup completed successfully")
        except Exception as e:
            self._update_status(self.STATUS_ERROR, error=str(e))

    @pyqtSlot()
    def reset_status(self):
        """Reset the status to the default idle state"""
        self._update_status(self.STATUS_IDLE)

    @pyqtSlot()
    def shutdown(self):
        """Gracefully shut down the application"""
        logger.info("Application shutdown requested")
        self._update_status(self.STATUS_SHUTTING_DOWN)
        self._conversation.append(f"[{self.get_timestamp()}] Shutting down...")
        self.conversationChanged.emit()

        # Set application state to prevent new operations from starting
        self._is_connected = False

        # Schedule the async cleanup in a separate task - don't wait for the result
        cleanup_task = asyncio.create_task(self._do_shutdown_cleanup())

        # Disconnect any signals that could cause issues during shutdown
        if hasattr(self, "_disconnect_signals"):
            self._disconnect_signals()

        # Give a short delay to allow the cleanup task to start
        # Then quit the application - use a longer timer to give cleanup more time
        QTimer.singleShot(1500, self._force_quit)

    def _force_quit(self):
        """Force quit the application after timeout"""
        logger.info("Forcing application quit")
        QApplication.quit()

    async def _do_shutdown_cleanup(self):
        """Perform the actual cleanup work during shutdown"""
        # Clean up client with timeout
        if self.client:
            try:
                # Don't use a task here to avoid task cancellation issues
                try:
                    # Give slightly longer timeout during final shutdown
                    await asyncio.wait_for(self.client.cleanup(), timeout=4.0)
                    logger.info("Application cleanup complete")
                except asyncio.TimeoutError:
                    logger.warning("Shutdown cleanup timed out, forcing exit")
            except Exception as e:
                logger.error(f"Error during shutdown cleanup: {e}")

        # Clear any references that might prevent proper garbage collection
        self.client = None

    @pyqtSlot()
    def getAvailableServers(self):
        """Get the available MCP servers and emit the availableServersChanged signal"""
        # Get the list of MCP servers
        servers = self._discover_mcp_servers()
        self._available_servers = servers
        self.availableServersChanged.emit(servers)

    def _discover_mcp_servers(self):
        """Discover available MCP servers in the mcp_server directory"""
        # Get the absolute path to the mcp_server directory
        mcp_server_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../mcp_server")
        )

        # Ensure mcp_server directory is in the Python path
        parent_dir = os.path.dirname(mcp_server_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        servers = []

        try:
            for file in os.listdir(mcp_server_dir):
                if file.endswith("_server.py") and not file.startswith("__"):
                    server_path = os.path.join(mcp_server_dir, file)
                    server_name = file.replace("_server.py", "").title()
                    server_description = f"Control your {server_name} devices"

                    # Try reading the file directly to extract metadata without importing
                    try:
                        # Simple direct file read to get variables, safer than importing
                        with open(server_path, 'r') as f:
                            for line in f:
                                line = line.strip()
                                if line.startswith('SERVER_NAME ='):
                                    server_name = line.split('=', 1)[1].strip().strip('"\'')
                                elif line.startswith('SERVER_DESCRIPTION ='):
                                    server_description = line.split('=', 1)[1].strip().strip('"\'')

                        logger.debug(f"Successfully loaded metadata from {file}")
                    except Exception as e:
                        logger.warning(f"Error reading metadata from {file}: {e}")

                    servers.append(
                        {
                            "name": server_name,
                            "path": server_path,
                            "description": server_description,
                        }
                    )

            logger.info(f"Discovered {len(servers)} MCP servers")
            return servers
        except Exception as e:
            logger.error(f"Error discovering MCP servers: {e}")
            return []

    @pyqtSlot(str)
    def setServerPath(self, server_path):
        """Set the selected server path"""
        self._selected_server_path = server_path
        logger.info(f"Selected server: {server_path}")

    @pyqtSlot(result=str)
    def connectToServer(self):
        """Connect to the selected server"""
        if not self._selected_server_path:
            logger.error("No server selected")
            return "Unknown Server"

        # Initialize the client with the selected server
        self._update_status(self.STATUS_INITIALIZING)

        # Extract server name from path
        server_name = (
            os.path.basename(self._selected_server_path)
            .replace("_server.py", "")
            .title()
        )

        # Initialize the client with streaming enabled
        self.client = MCPClient(
            streaming=STREAMING_ENABLED,
            llm_server_url=SERVER_URL,
            model=MODEL_NAME,
            provider_type=PROVIDER_TYPE,
            api_key=API_KEY,
            timeout=TIMEOUT,
        )

        # Schedule connection to happen in the event loop
        asyncio.create_task(self._connect_to_selected_server(server_name))

        return server_name

    async def _connect_to_selected_server(self, server_name):
        """Connect to the selected server in the background"""
        try:
            self._update_status(self.STATUS_CONNECTING)
            self._conversation.append(
                f"[{self.get_timestamp()}] Connecting to server..."
            )
            self.conversationChanged.emit()

            # Set environment variable for server selection
            os.environ["MCP_SERVER_PATH"] = self._selected_server_path

            # Connect to the server
            await self.connect_to_server()

            # The connect_to_server method will have already updated the status
            # with the correct server name, so we don't need to do it again here
            self.conversationChanged.emit()
        except Exception as e:
            logger.error(f"Error connecting to server: {e}")
            self._update_status(self.STATUS_ERROR, error=str(e))
            self._conversation.append(f"[{self.get_timestamp()}] Error: {str(e)}")
            self.conversationChanged.emit()

    @pyqtSlot(result=bool)
    def isConnected(self):
        """Return the connection status of the client"""
        return self._is_connected

    @pyqtSlot()
    def startListening(self):
        """Start listening for voice input"""
        logger.info("Voice listening requested - not implemented")
        self._conversation.append(
            f"[{self.get_timestamp()}] Voice recognition is not yet available. Please use text input."
        )
        self.conversationChanged.emit()
        # Schedule stopping after 3 seconds to indicate not implemented
        QTimer.singleShot(3000, self.stopListening)

    @pyqtSlot()
    def stopListening(self):
        """Stop listening for voice input"""
        logger.info("Voice listening stopped")
        # This will be picked up by the QML interface via the isListening property binding

    @pyqtSlot()
    def disconnectFromServer(self):
        """Disconnect from the current server."""
        if not self._is_connected:
            return

        if self.client:
            self._update_status(self.STATUS_DISCONNECTED)
            # Schedule the cleanup asynchronously
            asyncio.create_task(self.cleanup())
            self.is_connected = False
            logger.info("Disconnected from server")
            return True
        else:
            logger.warning("Not connected to any server")
            return False

    @pyqtSlot()
    def stop_response(self):
        """Stop the current response processing."""
        logger.info("Stopping response")
        # Set the stop flag immediately to prevent further UI updates
        self._stop_requested = True

        if self._is_connected and self.client:
            # Execute the stop operation in the background
            self._loop.create_task(self._stop_response())
            # Add immediate UI feedback
            self._conversation.append(
                f"[{self.get_timestamp()}] Stopping response..."
            )
            self.conversationChanged.emit()

            # Immediately update the UI state to show that response is stopping
            self._update_status(self.STATUS_IDLE)
            # Emit the signal immediately to ensure UI updates right away
            self.responseStopped.emit()

    async def _stop_response(self):
        """Internal method to stop the response processing."""
        if not self.client:
            logger.warning("Client is not initialized, cannot stop response")
            return

        try:
            # Call the client's stop_response method
            success = await self.client.stop_response()

            # Update UI and emit signal regardless of success
            logger.info(f"Response stop {'successful' if success else 'attempted'}")
            self._update_status(self.STATUS_IDLE)

            # Add a message to the conversation
            self._conversation.append(
                f"[{self.get_timestamp()}] Response stopped"
            )
            self.conversationChanged.emit()

            # We've already emitted the signal in stop_response() for immediate UI feedback
            # But emit it again in case the previous emission was missed
            self.responseStopped.emit()
        except Exception as e:
            logger.error(f"Error stopping response: {e}")
            self._update_status(self.STATUS_ERROR, error=str(e))
            self._conversation.append(
                f"[{self.get_timestamp()}] Error stopping response: {str(e)}"
            )
            self.conversationChanged.emit()

    @pyqtSlot(result=str)
    def getWifiIpAddress(self):
        """Get the IP address of the WiFi interface.

        Returns:
            A string with the WiFi IP address or an empty string if not available.
        """
        try:
            # Run ip addr command to get network interfaces
            result = subprocess.run(["ip", "addr"], capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to get network interfaces: {result.stderr}")
                return ""

            # Parse the output to find WiFi interfaces (typically wlan0, wlp2s0, etc.)
            wifi_ip_addresses = []
            current_interface = None

            for line in result.stdout.splitlines():
                # Check for interface line
                if line.startswith(" ") and current_interface:
                    # Look for inet (IPv4) address line for current interface
                    if "inet " in line:
                        # Extract the IP address using regex
                        match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", line)
                        if match:
                            ip_address = match.group(1)
                            # Skip localhost
                            if not ip_address.startswith("127."):
                                wifi_ip_addresses.append(
                                    f"{current_interface}: {ip_address}"
                                )
                else:
                    # New interface - check if it's a WiFi interface
                    current_interface = None
                    # Look for wireless interfaces (wlan0, wlp2s0, etc.)
                    if any(
                        x in line for x in ["wlan", "wlp", "wifi", "wls", "wlx", "wlo"]
                    ):
                        match = re.search(r"\d+: ([^:]+):", line)
                        if match:
                            current_interface = match.group(1)

            # Return the list of WiFi IP addresses, or empty string if none found
            return "\n".join(wifi_ip_addresses) if wifi_ip_addresses else ""

        except Exception as e:
            logger.error(f"Error getting WiFi IP address: {e}")
            return ""


class App:
    def __init__(self):
        """App initializes the QML application and engine."""
        self.app = QApplication(sys.argv)
        self.engine = QQmlApplicationEngine()
        self.bridge = MCPClientBridge()
        self.app_info = AppInfoManager()
        self.loop = None

    async def initialize(self):
        """Initialize the application and set up the QML engine."""
        # Create the QML engine and expose the bridge
        rc = self.engine.rootContext()
        if rc is None:
            logger.error("Failed to get root context from QML engine")
            return False
        rc.setContextProperty("bridge", self.bridge)

        # Register the QML module directory
        ui_dir = os.path.dirname(os.path.abspath(__file__))
        components_dir = os.path.join(ui_dir, "Components")

        # Make sure Components directory exists
        os.makedirs(components_dir, exist_ok=True)

        # Add import paths
        logger.info(f"Adding QML import path: {ui_dir}")
        self.engine.addImportPath(ui_dir)

        # Set up the QML document
        qml_file = os.path.join(ui_dir, "main.qml")
        logger.info(f"Loading QML file: {qml_file}")
        logger.info(f"QML engine import paths: {self.engine.importPathList()}")

        self.engine.load(QUrl.fromLocalFile(qml_file))

        # Ensure the engine loaded successfully
        if not self.engine.rootObjects():
            logger.error("Failed to load QML engine")
            return False
        logger.info("QML engine loaded successfully")

        # Return success
        logger.info(f"Starting {self.app_info.appName} {self.app_info.fullVersion}")
        return True

    async def run(self):
        """Run the application and enter the event loop."""
        # Setup logging
        setup_logging(log_level=LOGGING_LEVEL)
        logger.info("Starting application")

        # Set up event loop
        self.loop = QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)

        # Initialize the application
        success = await self.initialize()
        if not success:
            logger.error("Failed to initialize application")
            return 1

        # Get root object and connect quit handler
        self.root_object = self.engine.rootObjects()[0]
        self.app.aboutToQuit.connect(self.handle_quit)
        
        # Ensure clean engine shutdown by explicitly clearing all objects on quit
        self.app.aboutToQuit.connect(self.engine.clearComponentCache)
        self.app.aboutToQuit.connect(self.engine.collectGarbage)

        # Enter the main event loop
        logger.info("Entering main event loop")
        return self.loop.run_forever()

    def handle_quit(self):
        """Handle application quit signal."""
        logger.info("Application quit signal received")

        # First stop any pending async operations
        if self.bridge:
            asyncio.create_task(self.bridge.cleanup())

        # Explicitly release QML engine references
        for obj in self.engine.rootObjects():
            if obj:
                obj.setParent(None)
                
        # Explicitly clear the engine cache
        self.engine.clearComponentCache()
        self.engine.collectGarbage()

        # Clean up the QML engine
        self.engine.deleteLater()

        # End the event loop if it's running
        if self.loop and self.loop.is_running():
            self.loop.stop()

        logger.info("Application shutdown complete")



if __name__ == "__main__":
    app = App()
    asyncio.run(app.run())