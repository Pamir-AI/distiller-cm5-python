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
from distiller_cm5_python.client.ui.utils.NetworkUtils import NetworkUtils
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

    def _handle_event(self, event: Union[dict, object]) -> None:
        """
        Legacy method for backward compatibility.
        Events are now handled by the event handler component.
        """
        # Add debug logging
        logger.debug(
            f"MCPClientBridge received event: type={getattr(event, 'type', None)}, status={getattr(event, 'status', None)}"
        )
        # Just delegate to the event handler
        self.event_handler.handle_event(event)

    # MCPClientBridge-specific methods not present in BridgeCore
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

    @pyqtSlot(result="QVariantMap")
    def getSystemStats(self):
        """Get system statistics (CPU, RAM, temperature, LLM)."""
        try:
            # Lazy import to avoid circular imports
            from distiller_cm5_python.client.ui.system_monitor import SystemMonitor

            # Return formatted stats dictionary
            return SystemMonitor(
                self.mcp_client.llm_provider.provider_type
            ).get_formatted_stats()
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {"cpu": "N/A", "ram": "N/A", "temp": "N/A", "llm": "Local"}

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
            if hasattr(self, "cleanup") and callable(self.cleanup):
                try:
                    # Run cleanup synchronously
                    asyncio.run_coroutine_threadsafe(self.cleanup(), self._loop).result(
                        timeout=2.0
                    )  # 2-second timeout for cleanup
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
