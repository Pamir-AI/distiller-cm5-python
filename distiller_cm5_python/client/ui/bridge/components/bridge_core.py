"""
Core bridge module that integrates all components.
This is the central module that brings together all the bridge components.
"""

import logging
import asyncio
import os

from qasync import asyncSlot
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, pyqtProperty

from distiller_cm5_python.client.ui.bridge.StatusManager import StatusManager
from distiller_cm5_python.client.ui.bridge.ConversationManager import (
    ConversationManager,
)
from distiller_cm5_python.client.ui.bridge.ServerDiscovery import ServerDiscovery
from distiller_cm5_python.client.ui.utils.NetworkUtils import NetworkUtils
from distiller_cm5_python.client.mid_layer.mcp_client import MCPClient
from distiller_cm5_python.client.ui.events.event_dispatcher import EventDispatcher
from distiller_cm5_python.utils.config import DEFAULT_CONFIG_PATH, API_KEY

from .event_handler import BridgeEventHandler
from .connection_manager import ConnectionManager
from .error_handler import ErrorHandler
from .lifecycle_manager import LifecycleManager

logger = logging.getLogger(__name__)


class BridgeCore(QObject):
    """
    Core bridge class that integrates all components.
    This class provides the main interface for the UI and coordinates
    between the various specialized components.
    """

    # Signal definitions
    conversationChanged = pyqtSignal()  # Signal for conversation changes
    statusChanged = pyqtSignal(str)  # Signal for status changes
    availableServersChanged = pyqtSignal(list)  # Signal for available servers list
    isConnectedChanged = pyqtSignal(bool)  # Signal for connection status
    messageReceived = pyqtSignal(
        str, str, str, str
    )  # Signal for new messages (content, event_id, timestamp, status)
    listeningStarted = pyqtSignal()  # Signal for when listening starts
    listeningStopped = pyqtSignal()  # Signal for when listening stops
    errorOccurred = pyqtSignal(str)  # Signal for errors
    bridgeReady = pyqtSignal()  # Signal for when the bridge is fully initialized
    recordingStateChanged = pyqtSignal(bool)  # Signal for recording state changes
    recordingError = pyqtSignal(
        str
    )  # Signal specifically for recording/transcription errors
    actionReceived = pyqtSignal(str, str, str)  # Signal for actions
    infoReceived = pyqtSignal(str, str, str)  # Signal for info messages
    warningReceived = pyqtSignal(str, str, str)  # Signal for warnings
    errorReceived = pyqtSignal(str, str, str)  # Signal for errors
    transcriptionUpdate = pyqtSignal(
        str, arguments=["transcription"]
    )  # Signal for transcription updates
    transcriptionComplete = pyqtSignal(
        str, arguments=["full_text"]
    )  # Signal for completed transcription
    functionReceived = pyqtSignal(str, str, str)  # Signal for function events
    observationReceived = pyqtSignal(str, str, str)  # Signal for observation events
    planReceived = pyqtSignal(str, str, str)  # Signal for plan events
    messageSchemaReceived = pyqtSignal(
        "QVariantMap"
    )  # Signal for raw message schema objects

    def __init__(self, parent=None):
        """
        Initialize the bridge core and all its components.

        Args:
            parent: Optional parent object
        """
        super().__init__(parent=parent)

        # Initialize basic state
        self._is_connected = False
        self._is_ready = False
        self._loop = asyncio.get_event_loop()
        self._app_instance = None

        # Initialize basic components
        self.status_manager = StatusManager(self)
        self.conversation_manager = ConversationManager(self)
        self.server_discovery = ServerDiscovery(self)
        self.network_utils = NetworkUtils()
        self.dispatcher = EventDispatcher()

        # Initialize the MCP client with dispatcher and API Key
        self.mcp_client = MCPClient(dispatcher=self.dispatcher, api_key=API_KEY)

        # Initialize specialized components
        self.event_handler = BridgeEventHandler(
            self.dispatcher, self.status_manager, self, type(self).is_connected
        )
        # Give the event handler direct access to the conversation manager
        self.event_handler.signals.conversation_manager = self.conversation_manager

        self.error_handler = ErrorHandler(
            self.status_manager,
            self.conversation_manager,
            self.dispatcher,
            self.errorOccurred.emit,
        )

        self.connection_manager = ConnectionManager(
            self.status_manager,
            self.conversation_manager,
            self.server_discovery,
            type(self).is_connected,
            self.error_handler,
        )

        self.lifecycle_manager = LifecycleManager(
            self.status_manager, self.conversation_manager
        )

        # Initialize state
        self.conversation_manager.reset_streaming_message()

        # Sync the connection manager's MCP client with ours
        self.connection_manager.mcp_client = self.mcp_client

    def set_app_instance(self, app_instance):
        """Set the reference to the App instance."""
        self._app_instance = app_instance
        logger.info("App instance reference set in bridge")

    @pyqtProperty(bool, notify=bridgeReady)
    def ready(self):
        """Return whether the bridge is fully initialized and ready for use."""
        return self._is_ready

    @pyqtSlot(bool)
    def setReady(self, value):
        """Set the ready state of the bridge and emit the bridgeReady signal."""
        if self._is_ready != value:
            self._is_ready = value
            if self._is_ready:
                self.bridgeReady.emit()
            logger.info(f"Bridge ready state set to: {self._is_ready}")

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

    async def initialize(self):
        """Initialize the client and connect to the server"""
        return await self.lifecycle_manager.initialize_bridge(
            self.server_discovery.discover_mcp_servers
        )

    @pyqtSlot(result=str)
    def get_status(self):
        """Return the current status of the client"""
        return self.status_manager.status

    @pyqtSlot(result=list)
    def get_conversation(self):
        """Return the current conversation as a list of formatted messages"""
        return self.conversation_manager.get_formatted_messages()

    @pyqtSlot()
    def clear_conversation(self):
        """Clear the conversation history"""
        self.conversation_manager.clear()
        logger.info("Conversation cleared")

    @asyncSlot(str)
    async def submit_query(self, query: str):
        """Submit a query to the server and update the conversation"""
        try:
            if not query.strip():
                return

            if not self._is_connected:
                raise ConnectionError(
                    "Not connected to any server. Please connect first."
                )

            # Add user message
            user_message = {
                "timestamp": self.conversation_manager.get_timestamp(),
                "content": f"You: {query}",
            }
            self.conversation_manager.add_message(user_message)
            logger.info(f"User query added to conversation: {query}")

            # Process the query in a separate task to avoid blocking the UI
            asyncio.create_task(self.process_query(query))

        except Exception as e:
            self.error_handler.handle_error(
                e,
                "Query submission",
                user_friendly_msg="Failed to submit query. Please check your connection and try again.",
            )

    async def process_query(self, query: str):
        """Process a user query through the MCP client."""
        try:
            await self.connection_manager.process_query(query)
        except Exception as e:
            self.error_handler.handle_error(
                e,
                "Query processing",
                user_friendly_msg="Failed to process query. Please try again.",
            )

    async def connect_to_server(self):
        """Ask the user to select a server from the list of available servers."""
        success = await self.connection_manager.connect_to_server()
        if success:
            self.availableServersChanged.emit(self.server_discovery.available_servers)
        return success

    @pyqtSlot(bool)
    def shutdownApplication(self, restart=False):
        """
        Handle application shutdown gracefully.
        Args:
            restart: Whether to restart after shutdown (currently unused)
        """
        logger.info(f"Shutdown requested from QML with restart={restart}")
        asyncio.create_task(self.lifecycle_manager.shutdown_process(self.mcp_client))
        return True

    @pyqtSlot()
    def reset_status(self):
        """Reset the status to idle."""
        if self._is_connected:
            self.status_manager.update_status(StatusManager.STATUS_IDLE)
        else:
            self.status_manager.update_status(StatusManager.STATUS_DISCONNECTED)

    @pyqtSlot()
    def getAvailableServers(self):
        """Get the list of available MCP servers."""
        servers = self.connection_manager.get_available_servers()
        self.availableServersChanged.emit(servers)
        return servers

    @pyqtSlot(str)
    def setServerPath(self, server_path):
        """Set the path to the MCP server script."""
        self.connection_manager.set_server_path(server_path)

    @pyqtSlot(result=str)
    def connectToServer(self):
        """Connect to the selected MCP server."""
        try:
            if not self.connection_manager.selected_server_path:
                raise ValueError(
                    "No server selected. Please choose a server before connecting."
                )

            # Use utility to extract server name for status messages
            from distiller_cm5_python.utils.server_utils import extract_server_name

            server_name = extract_server_name(
                self.connection_manager.selected_server_path
            )

            if not os.path.exists(self.connection_manager.selected_server_path):
                raise FileNotFoundError(
                    f"Server script not found: {self.connection_manager.selected_server_path}"
                )

            # Update UI immediately to show connecting status
            self.status_manager.update_status(StatusManager.STATUS_CONNECTING)

            # Create task to connect in the background
            asyncio.create_task(
                self.connection_manager.connect_to_selected_server(server_name)
            )
            return ""  # Empty string indicates success (no error)

        except Exception as e:
            error_msg = self.error_handler.handle_error(
                e,
                "Server connection",
                user_friendly_msg=f"Failed to connect to server: {str(e)}",
            )
            return error_msg  # Return error message string

    @pyqtSlot(result=bool)
    def isConnected(self):
        """Check if the client is connected to a server."""
        return self._is_connected

    @pyqtSlot()
    def startListening(self):
        """Start voice listening."""
        try:
            logger.info("Voice activation requested")

            # Check if client is connected
            if not self._is_connected:
                raise ConnectionError(
                    "Cannot activate voice: not connected to any server."
                )

            # Emit signal for UI update
            self.listeningStarted.emit()

            # Call startRecording
            self.startRecording()
        except Exception as e:
            self.error_handler.handle_error(
                e,
                "Voice activation",
                user_friendly_msg="Voice activation failed. Please check your microphone settings.",
            )
            # Update UI appropriately
            self.listeningStopped.emit()

    @pyqtSlot()
    def stopListening(self):
        """Stop voice listening."""
        try:
            logger.info("Voice deactivation requested")
            # Emit signal for UI update
            self.listeningStopped.emit()
            self.status_manager.update_status(StatusManager.STATUS_IDLE)

            # Call stopAndTranscribe
            self.stopAndTranscribe()
        except Exception as e:
            self.error_handler.handle_error(e, "Voice deactivation")

    @pyqtSlot()
    def startRecording(self):
        """Start recording audio with Whisper."""
        try:
            logger.info("Starting Whisper recording")

            # Use direct app instance reference
            if self._app_instance:
                self._app_instance.startRecording()
            else:
                raise RuntimeError("No App instance reference available")
        except Exception as e:
            self.error_handler.handle_error(
                e,
                "Voice recording",
                user_friendly_msg="Failed to start recording. Please check your microphone settings.",
            )

    @pyqtSlot()
    def stopAndTranscribe(self):
        """Stop recording and transcribe the audio with Whisper."""
        try:
            logger.info("Stopping recording and starting transcription")

            # Use direct app instance reference
            if self._app_instance:
                self._app_instance.stopAndTranscribe()
            else:
                raise RuntimeError("No App instance reference available")
        except Exception as e:
            self.error_handler.handle_error(
                e,
                "Voice transcription",
                user_friendly_msg="Failed to transcribe audio.",
            )
            # Update UI appropriately
            self.listeningStopped.emit()

    @pyqtSlot()
    def disconnectFromServer(self):
        """Disconnect from the MCP server."""
        logger.info("Disconnecting from server")
        asyncio.create_task(self.connection_manager.disconnect_from_server())

    @pyqtSlot(result=str)
    def getWifiIpAddress(self):
        """Get the WiFi IP address of the system."""
        return self.network_utils.get_wifi_ip_address()

    @pyqtSlot(result=str)
    def getWifiName(self):
        """Get the WiFi SSID name."""
        return self.network_utils.get_wifi_name()

    async def cleanup(self):
        """
        Compatibility method for the App class.
        Delegates cleanup to the components.
        """
        logger.info("cleanup() called - delegating to components")
        try:
            # Clean up client if exists
            if self.mcp_client:
                try:
                    await self.mcp_client.cleanup()
                    logger.info("Completed MCP client cleanup")
                except Exception as e:
                    logger.error(f"Error during client cleanup: {e}", exc_info=True)

            # Terminate dangling processes
            self.lifecycle_manager._terminate_dangling_processes()

            logger.info("Bridge cleanup completed")
        except Exception as e:
            logger.error(f"Error during bridge cleanup: {e}", exc_info=True)

    def shutdown(self, restart=False):
        """
        Synchronous shutdown method for App.py compatibility.
        Creates an async task to perform the actual shutdown.

        Args:
            restart: Parameter for backward compatibility (unused)
        """
        logger.info(f"shutdown() called with restart={restart}")
        # Create a task to run the async shutdown process
        asyncio.create_task(self.lifecycle_manager.shutdown_process(self.mcp_client))

    @pyqtSlot()
    def restartApplication(self):
        """Restart the application without completely shutting down."""
        logger.info("Application restart requested")
        self.status_manager.update_status(StatusManager.STATUS_RESTARTING)
        asyncio.create_task(self._do_restart())

    async def _do_restart(self):
        """Perform application restart by resetting state and reconnecting."""
        await self.lifecycle_manager.restart_application(
            type(self).is_connected,
            self.mcp_client,
            self.connection_manager.disconnect_from_server,
            self.connection_manager.connect_to_selected_server,
        )

        # Emit bridge ready signal to refresh UI components
        logger.info("Emitting bridgeReady signal to reinitialize UI")
        self.bridgeReady.emit()
