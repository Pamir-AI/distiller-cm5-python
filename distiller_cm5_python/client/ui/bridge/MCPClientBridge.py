"""
Main bridge module that connects the UI to the backend.
This is a facade class that delegates to the modular components.
"""

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, pyqtProperty
from PyQt6.QtWidgets import QApplication
from distiller_cm5_python.client.mid_layer.mcp_client import MCPClient
from qasync import asyncSlot
from distiller_cm5_python.utils.config import *
from distiller_cm5_python.client.ui.events.event_dispatcher import EventDispatcher
from distiller_cm5_python.client.ui.bridge.ConversationManager import (
    ConversationManager,
)
from distiller_cm5_python.client.ui.bridge.StatusManager import StatusManager
from distiller_cm5_python.client.ui.bridge.ServerDiscovery import ServerDiscovery
from distiller_cm5_python.client.ui.bridge.WiFiSetupBridge import WiFiSetupBridge
from distiller_cm5_python.client.ui.network.network_utils import NetworkUtils
from distiller_cm5_python.utils.distiller_exception import (
    UserVisibleError,
    LogOnlyError,
)
import asyncio
import os
import sys
import time
import psutil
import threading
from typing import Union, Optional
import uuid
import logging

from distiller_cm5_python.client.ui.bridge.components.bridge_core import BridgeCore

logger = logging.getLogger(__name__)

# Exit delay constant
EXIT_DELAY_MS = 500  # Reduced delay from 1000ms to 500ms


class MCPClientBridge(BridgeCore):
    """
    Bridge between the UI and the MCPClient.

    This class is a facade that implements the same interface as the original
    MCPClientBridge, but delegates all functionality to the modular components.
    This approach allows for a gradual refactoring while maintaining compatibility
    with existing code.
    """

    # Redefine the signal in this class for the property to work
    bridgeReady = pyqtSignal()

    # Signal for receiving MessageSchema events - defined here to maintain compatibility
    messageSchemaReceived = pyqtSignal("QVariantMap")

    # New signal for cache events
    cacheEventReceived = pyqtSignal(
        str, str, str, arguments=["content", "event_id", "timestamp"]
    )

    # Audio/Transcription signals - these will be connected to App's signals
    transcriptionUpdate = pyqtSignal(str, arguments=["transcription"])
    transcriptionComplete = pyqtSignal(str, arguments=["full_text"])
    recordingStateChanged = pyqtSignal(bool, arguments=["is_recording"])
    recordingError = pyqtSignal(str, arguments=["error_message"])

    def __init__(self, parent=None):
        """
        Initialize the bridge.

        Args:
            parent: Optional parent object
        """
        super().__init__(parent=parent)
        logger.info("MCPClientBridge initialized using modular architecture")

        # Initialize sub-components that differ from BridgeCore
        # (Different initialization than BridgeCore, so we keep it)
        self.status_manager = StatusManager(self)
        self.conversation_manager = ConversationManager(self)
        self.conversation_manager.reset_streaming_message()
        self.server_discovery = ServerDiscovery(self)
        self.network_utils = NetworkUtils()
        self.wifi_setup_bridge = WiFiSetupBridge(self)

        # Initialize event dispatcher with debug mode
        self.dispatcher = EventDispatcher(
            debug=logger.getEffectiveLevel() == logging.DEBUG
        )

        # Initialize MCP client with dispatcher first
        self.mcp_client = MCPClient(dispatcher=self.dispatcher, api_key=API_KEY)

        # Initialize the error handler first since the ConnectionManager now needs it
        from distiller_cm5_python.client.ui.bridge.components.error_handler import (
            ErrorHandler,
        )

        self.error_handler = ErrorHandler(
            self.status_manager,
            self.conversation_manager,
            self.dispatcher,
            self.errorOccurred.emit,
        )

        # Initialize connection manager after MCP client
        # Import the ConnectionManager class here to avoid circular imports
        from distiller_cm5_python.client.ui.bridge.components.connection_manager import (
            ConnectionManager,
        )

        self.connection_manager = ConnectionManager(
            self.status_manager,
            self.conversation_manager,
            self.server_discovery,
            self.is_connected.__class__,  # Pass the property class
            self.error_handler,  # Pass the error handler
        )
        # Set up connection callback
        self.connection_manager.set_connection_callback(self._on_connection_changed)
        # Set the mcp_client in the connection manager
        self.connection_manager.mcp_client = self.mcp_client

        # Connect dispatcher signals to bridge slots
        self.dispatcher.message_dispatched.connect(self._handle_event)

        # MCPClientBridge-specific initialization
        self._current_log_level = config.get(
            "logging", "level", default="DEBUG"
        ).upper()
        self._selected_server_path = None

        # Initialize client-related properties from parent
        self._is_connected = False
        self._is_ready = False
        self._loop = asyncio.get_event_loop()
        self.config_path = DEFAULT_CONFIG_PATH
        self._app_instance = None

        # MCPClientBridge-specific caches
        self._last_server_discovery_time = 0
        self._server_discovery_cache_timeout = 5  # seconds
        self._config_cache = {}
        self._config_dirty = False
        
        # EInk renderer reference for text streaming optimization
        self._eink_renderer = None

    # Audio recording and transcription methods override the base class
    # to provide App instance-specific functionality
    @pyqtSlot()
    def startRecording(self):
        """Start recording audio with Whisper."""
        if self._app_instance:
            self._app_instance.startRecording()
        else:
            logger.error("Cannot start recording: No App instance reference available")

    @pyqtSlot()
    def stopAndTranscribe(self):
        """Stop recording and transcribe the audio with Whisper."""
        if self._app_instance:
            self._app_instance.stopAndTranscribe()
        else:
            logger.error("Cannot stop recording: No App instance reference available")

    def set_app_instance(self, app_instance):
        """Set the reference to the App instance."""
        self._app_instance = app_instance
        logger.info("App instance reference set in bridge")

    def set_eink_renderer(self, eink_renderer):
        """Set the reference to the EInk renderer for text streaming optimization."""
        self._eink_renderer = eink_renderer
        logger.info("EInk renderer reference set in bridge")

    def _handle_event(self, event: Union[dict, object]) -> None:
        """
        Legacy method for backward compatibility.
        Events are now handled by the event handler component.
        """
        # Add debug logging
        logger.debug(
            f"MCPClientBridge received event: type={getattr(event, 'type', None)}, status={getattr(event, 'status', None)}"
        )
        
        # Handle EInk renderer text streaming mode based on event type
        if self._eink_renderer:
            event_type = getattr(event, 'type', None)
            event_status = getattr(event, 'status', None)
            
            # Enable text streaming mode for message events
            if event_type == 'message' and event_status in ['in_progress', 'streaming']:
                self._eink_renderer.set_text_streaming_mode(True)
                self._eink_renderer.request_update()
            elif event_type == 'message' and event_status in ['success', 'complete']:
                self._eink_renderer.set_text_streaming_mode(False)
            elif event_type in ['tool_call_started', 'tool_call_complete', 'conversation_updated']:
                self._eink_renderer.request_update()
        
        # Just delegate to the event handler
        self.event_handler.handle_event(event)

    # MCPClientBridge-specific methods not present in BridgeCore
    @pyqtSlot(result=str)
    def getWifiMacAddress(self):
        """Get the WiFi MAC address of the system."""
        try:
            return self.network_utils.get_wifi_mac_address()
        except Exception as e:
            logger.error(f"Error getting WiFi MAC address: {e}")
            return "Error getting MAC address"

    @pyqtSlot(result=str)
    def getWifiSignalStrength(self):
        """Get the WiFi signal strength."""
        try:
            return self.network_utils.get_wifi_signal_strength()
        except Exception as e:
            logger.error(f"Error getting WiFi signal strength: {e}")
            return "Error getting signal strength"

    @pyqtSlot(result="QVariant")
    def getNetworkDetails(self):
        """Get detailed information about the network."""
        try:
            return self.network_utils.get_network_details()
        except Exception as e:
            logger.error(f"Error getting network details: {e}")
            return {"error": "Failed to get network details"}

    def _on_connection_changed(self, value):
        """Handle connection state changes from the connection manager"""
        self.is_connected = value  # This will emit the signal

    @pyqtSlot(result=str)
    def getPrimaryFontPath(self):
        """Get the primary font path directly from display_config.py."""
        try:
            # Import here to avoid circular imports
            from distiller_cm5_python.client.ui.display_config import (
                config as display_config,
            )

            if "display" in display_config and "font" in display_config["display"]:
                font_config = display_config["display"]["font"]

                if "primary_font" in font_config:
                    return font_config["primary_font"]

            # Default fallback if anything is missing
            return "fonts/MonoramaNerdFont-Medium.ttf"
        except Exception as e:
            logger.error(f"Error getting primary font path: {e}")
            return "fonts/MonoramaNerdFont-Medium.ttf"  # Default fallback

    @pyqtSlot(result=bool)
    def getShowSystemStats(self):
        """Check if system stats display is enabled in config."""
        try:
            # Import here to avoid circular imports
            from distiller_cm5_python.client.ui.display_config import (
                config as display_config,
            )

            if (
                "display" in display_config
                and "show_system_stats" in display_config["display"]
            ):
                return display_config["display"]["show_system_stats"]

            return True  # Default to enabled if missing
        except Exception as e:
            logger.error(f"Error checking system stats flag: {e}")
            return True  # Default to enabled if error

    @pyqtSlot(result="QVariantMap")
    def getSystemStats(self):
        """Get system statistics (CPU, RAM, temperature, LLM)."""
        try:
            # Lazy import to avoid circular imports
            from distiller_cm5_python.client.ui.system_monitor import system_monitor

            # Return formatted stats dictionary
            return system_monitor.get_formatted_stats()
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {"cpu": "N/A", "ram": "N/A", "temp": "N/A", "llm": "Local"}

    @pyqtSlot(result="QVariantMap")
    def getBatteryInfo(self):
        """Get battery information for UI display."""
        try:
            # Lazy import to avoid circular imports
            from distiller_cm5_python.utils.battery_monitor import get_battery_info

            # Return battery info dictionary
            return get_battery_info()
        except Exception as e:
            logger.error(f"Error getting battery info: {e}")
            return {
                "capacity": 100,
                "status": "Unknown",
                "isCharging": False,
                "isLow": False,
                "isCritical": False,
                "iconName": "battery-unknown",
                "statusPattern": "empty",  # Default pattern
                "statusText": "UNK",  # Default status text
                "voltage": 0.0,
                "current": 0.0,
                "temperature": 0.0,
                "present": False,
                "technology": "Unknown",
                "shouldShowWarning": False,
                "shouldShutdown": False
            }

    @pyqtSlot(result=bool)
    def sendPowerShutdownSignal(self):
        """Send BTN_POWER packet via UART for coordinated system shutdown."""
        try:
            # Execute pre-shutdown command if configured
            self._execute_pre_shutdown_command()
            
            # Lazy import to avoid circular imports
            from distiller_cm5_python.utils.uart_utils import send_btn_power_packet
            
            logger.info("Sending BTN_POWER packet for coordinated shutdown")
            success = send_btn_power_packet()
            
            if success:
                logger.info("BTN_POWER packet sent successfully")
            else:
                logger.error("Failed to send BTN_POWER packet")
                
            return success
        except Exception as e:
            logger.error(f"Error sending power shutdown signal: {e}")
            return False
    
    def _execute_pre_shutdown_command(self):
        """Execute the pre-shutdown command if configured."""
        try:
            # Import here to avoid circular imports
            from distiller_cm5_python.utils.config import config
            import subprocess
            import time
            
            pre_shutdown_cmd = config.get("system", "pre_shutdown_command", default="").strip()
            timeout = config.get("system", "pre_shutdown_timeout", default=5)
            
            if not pre_shutdown_cmd:
                return
            
            # Stop and cleanup e-ink renderer if it exists
            if hasattr(self, '_eink_renderer') and self._eink_renderer:
                try:
                    logger.info("Stopping and cleaning up e-ink renderer before pre-shutdown command")
                    self._eink_renderer.stop()
                    self._eink_renderer.cleanup()
                    # Give hardware time to fully release
                    time.sleep(0.5)
                    logger.info("E-ink renderer cleaned up successfully")
                except Exception as e:
                    logger.error(f"Error cleaning up e-ink renderer: {e}")
                    # Continue with pre-shutdown command even if cleanup fails
            
            logger.info(f"Executing pre-shutdown command: {pre_shutdown_cmd}")
            
            # Execute with timeout - use shell=True for complex commands
            try:
                result = subprocess.run(
                    pre_shutdown_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                if result.returncode == 0:
                    logger.info(f"Pre-shutdown command completed successfully: {result.stdout}")
                else:
                    logger.error(f"Pre-shutdown command failed with code {result.returncode}: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                logger.error(f"Pre-shutdown command timed out after {timeout} seconds")
            except Exception as e:
                logger.error(f"Pre-shutdown command execution failed: {e}")
                
        except Exception as e:
            logger.error(f"Error executing pre-shutdown command: {e}")
            # Don't prevent shutdown if pre-shutdown command fails

    @pyqtSlot()
    def closeApplication(self):
        """
        Close the application gracefully.
        This method will perform any necessary cleanup and then exit the application.
        """
        logger.info("Closing application from QML bridge call")
        try:
            # Signal application power down via UART
            from distiller_cm5_python.utils.uart_utils import signal_app_shutdown
            signal_app_shutdown()
            logger.info("Sent shutdown signal to UART device")
            
            # Perform cleanup first
            if hasattr(self, 'cleanup') and callable(self.cleanup):
                try:
                    # Run cleanup synchronously
                    asyncio.run_coroutine_threadsafe(
                        self.cleanup(), self._loop
                    ).result(timeout=2.0)  # 2-second timeout for cleanup
                    logger.info("Cleanup completed successfully")
                except Exception as e:
                    logger.error(f"Error during cleanup: {e}")
            
            # Schedule application exit with a short delay to allow cleanup to complete
            QApplication.instance().quit()
            logger.info("Application exit scheduled")
            
        except Exception as e:
            logger.error(f"Error during application close: {e}")
            # Force quit if normal exit fails
            try:
                QApplication.instance().exit(1)
            except:
                # Last resort: terminate process
                os._exit(1)
                
    @pyqtSlot(str)
    def executeSystemCommand(self, command: str):
        """
        Execute a system command with proper security checks.
        
        Args:
            command: The system command to execute
        """
        # Only allow specific system commands
        allowed_commands = {
            "shutdown now": "sudo shutdown now",
            "poweroff": "sudo poweroff"
        }
        
        logger.info(f"Received system command request: {command}")
        
        if command not in allowed_commands:
            logger.error(f"Unauthorized system command attempt: {command}")
            return
            
        try:
            # Signal application power down via UART first
            from distiller_cm5_python.utils.uart_utils import signal_app_shutdown
            signal_app_shutdown()
            logger.info(f"Sent shutdown signal to UART device before system {command}")
            
            # Execute the allowed command
            import subprocess
            logger.info(f"Executing system command: {allowed_commands[command]}")
            
            # Run the command in a separate process
            subprocess.Popen(allowed_commands[command], shell=True)
            
            # Return immediately to allow the command to complete
            return
            
        except Exception as e:
            logger.error(f"Error executing system command: {e}")
    
    @pyqtSlot(str)
    def setLlmModel(self, model_name):
        """Set the current LLM model name."""
        try:
            from distiller_cm5_python.client.ui.system_monitor import system_monitor

            system_monitor.set_llm_model(model_name)
        except Exception as e:
            logger.error(f"Error setting LLM model: {e}")
    
    @pyqtSlot()
    def reconnectToServer(self):
        """Reconnect to the currently selected server."""
        try:
            if hasattr(self, 'connection_manager') and self.connection_manager.selected_server_path:
                # Run the reconnection asynchronously
                if self._loop and not self._loop.is_closed():
                    asyncio.ensure_future(
                        self.connection_manager.connect_to_selected_server(),
                        loop=self._loop
                    )
                    logger.info("Reconnection attempt initiated")
                else:
                    logger.error("Event loop not available for reconnection")
            else:
                logger.warning("No server path available for reconnection")
        except Exception as e:
            logger.error(f"Error during reconnection: {e}")
    
    @pyqtProperty(QObject, constant=True)
    def wifiSetupBridge(self):
        """Expose WiFi setup bridge to QML."""
        return self.wifi_setup_bridge
    
    async def cleanup(self):
        """Override cleanup to include WiFi setup cleanup."""
        try:
            # Cleanup WiFi setup bridge first
            if hasattr(self, 'wifi_setup_bridge') and self.wifi_setup_bridge:
                self.wifi_setup_bridge.cleanup()
                logger.info("WiFi setup bridge cleanup completed")
        except Exception as e:
            logger.error(f"Error during WiFi setup cleanup: {e}")
        
        # Call parent cleanup
        await super().cleanup()
