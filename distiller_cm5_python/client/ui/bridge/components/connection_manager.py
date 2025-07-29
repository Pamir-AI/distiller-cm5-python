"""
Connection manager component for the MCPClientBridge.
Handles connecting to, disconnecting from, and managing MCP servers.
"""

from typing import Optional, Any, Dict, List
import logging
import asyncio
import os
import time

from distiller_cm5_python.client.mid_layer.mcp_client import MCPClient
from distiller_cm5_python.client.ui.bridge.StatusManager import StatusManager
from distiller_cm5_python.client.ui.bridge.ConversationManager import (
    ConversationManager,
)
from distiller_cm5_python.client.ui.bridge.ServerDiscovery import ServerDiscovery
from distiller_cm5_python.client.ui.bridge.components.error_handler import ErrorHandler
from distiller_cm5_python.utils.config import (
    STREAMING_ENABLED,
    SERVER_URL,
    PROVIDER_TYPE,
    MODEL_NAME,
    API_KEY,
    TIMEOUT,
)
from distiller_cm5_python.utils.distiller_exception import LogOnlyError

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages connections to MCP servers.
    Handles discovery, connection, and disconnection.
    """

    def __init__(
        self,
        status_manager: StatusManager,
        conversation_manager: ConversationManager,
        server_discovery: ServerDiscovery,
        is_connected_property: "property",
        error_handler: ErrorHandler,
    ):
        """
        Initialize the connection manager.

        Args:
            status_manager: The status manager to update based on connection changes
            conversation_manager: The conversation manager to add messages about connections
            server_discovery: The server discovery component to find available servers
            is_connected_property: A property that indicates if the bridge is connected
            error_handler: The error handler for unified error handling
        """
        self.status_manager = status_manager
        self.conversation_manager = conversation_manager
        self.server_discovery = server_discovery
        self.is_connected_property = is_connected_property
        self.error_handler = error_handler
        self._on_connection_changed = lambda value: None  # Default no-op callback

        # Server discovery cache
        self._last_server_discovery_time = 0
        self._server_discovery_cache_timeout = 5  # seconds

        # Connection state
        self._selected_server_path: Optional[str] = None
        self._mcp_client: Optional[MCPClient] = None
        self._is_connected: bool = False  # Initialize the connection state attribute

    @property
    def mcp_client(self) -> Optional[MCPClient]:
        """Get the current MCP client instance"""
        return self._mcp_client

    @mcp_client.setter
    def mcp_client(self, client: Optional[MCPClient]) -> None:
        """Set the MCP client instance"""
        self._mcp_client = client

    @property
    def selected_server_path(self) -> Optional[str]:
        """Get the selected server path"""
        return self._selected_server_path

    async def connect_to_server(self) -> bool:
        """
        Ask the user to select a server from the list of available servers.

        Returns:
            True if servers are available, False otherwise
        """
        self.status_manager.update_status(StatusManager.STATUS_INITIALIZING)

        if not self.server_discovery.available_servers:
            self.server_discovery.discover_mcp_servers()

        if not self.server_discovery.available_servers:
            self.error_handler.handle_error(
                Exception("No MCP servers found"),
                error_context="Server discovery",
                user_friendly_msg="No MCP servers found",
            )
            return False

        # Wait for user to select a server in UI before proceeding
        logger.info("Available servers discovered. Waiting for user selection.")
        self.status_manager.update_status(StatusManager.STATUS_DISCONNECTED)
        return True

    def set_server_path(self, server_path: str) -> None:
        """
        Set the path to the MCP server script.

        Args:
            server_path: The path to the MCP server script
        """
        logger.info(f"Setting server path: {server_path}")
        self._selected_server_path = server_path

    async def connect_to_selected_server(self, server_name: Optional[str] = None) -> bool:
        """
        Connect to the selected server asynchronously.

        Args:
            server_name: Optional server name for display purposes

        Returns:
            True if connection was successful, False otherwise
        """
        if not self._selected_server_path:
            logger.error("No server selected")
            return False

        if not server_name:
            # Use utility to extract server name from path if not provided
            from distiller_cm5_python.utils.server_utils import extract_server_name

            server_name = extract_server_name(self._selected_server_path)

        try:
            self.conversation_manager.add_message(
                {
                    "timestamp": self.conversation_manager.get_timestamp(),
                    "content": f"Connecting to server: {server_name}...",
                }
            )

            # Use existing client or wait for it to be set
            if not self._mcp_client:
                error = RuntimeError("MCPClient not initialized. This is likely a setup issue.")
                self.error_handler.handle_error(
                    error,
                    error_context="Server connection",
                    user_friendly_msg="Failed to initialize connection client. Please restart the application.",
                )
                return False

            # Connect to server with explicit timeout
            try:
                connect_task = self._mcp_client.connect_to_server(self._selected_server_path)
                connected = await asyncio.wait_for(connect_task, timeout=TIMEOUT)
            except asyncio.TimeoutError as e:
                error_msg = f"Connection to {server_name} timed out after {TIMEOUT} seconds. Server may be busy or unavailable."
                self.error_handler.handle_error(
                    e, error_context="Server connection", user_friendly_msg=error_msg
                )

                # Clean up after connection failure
                await self._cleanup_after_connection_failure()
                return False

            if not connected:
                error = ConnectionError(
                    f"Failed to establish connection with {server_name} server. Check server status and configuration."
                )
                self.error_handler.handle_error(error, error_context="Server connection")

                # Clean up after connection failure
                await self._cleanup_after_connection_failure()
                return False

            self._update_connection_state(True)
            server_display_name = getattr(self._mcp_client, "server_name", None) or server_name
            self.status_manager.update_status(
                StatusManager.STATUS_CONNECTED, server_name=server_display_name
            )
            self.conversation_manager.add_message(
                {
                    "timestamp": self.conversation_manager.get_timestamp(),
                    "content": f"Connected to {server_display_name}",
                }
            )
            return True

        except Exception as e:
            self.error_handler.handle_error(
                e,
                error_context="Server connection",
                user_friendly_msg=f"Failed to connect to server: {server_name}",
            )

            # Clean up after connection failure
            await self._cleanup_after_connection_failure()
            return False

    async def _cleanup_after_connection_failure(self) -> None:
        """Clean up resources after a connection failure."""
        if self._mcp_client:
            try:
                await self._mcp_client.cleanup()
            except Exception as cleanup_e:
                logger.error(f"Error cleaning up client after connection failure: {cleanup_e}")
            finally:
                # Reset the client reference and connection state
                self._mcp_client = None

        self._update_connection_state(False)

    async def disconnect_from_server(self) -> None:
        """Disconnect from the current MCP server."""
        logger.info("Disconnecting from server")

        try:
            if self._mcp_client:
                try:
                    # Timeout the cleanup operation to prevent hanging
                    await asyncio.wait_for(self._mcp_client.cleanup(), timeout=5.0)
                except asyncio.TimeoutError as e:
                    self.error_handler.handle_error(
                        e,
                        error_context="Server disconnection",
                        user_friendly_msg="Disconnection timed out, but the application will continue to function.",
                        log_error=True,
                    )
                except Exception as e:
                    self.error_handler.handle_error(
                        e,
                        error_context="Server disconnection",
                        user_friendly_msg="An error occurred during disconnection, but the application will continue to function.",
                        log_error=True,
                    )
                finally:
                    # Always reset the client reference
                    self._mcp_client = None

            # Update the connection state
            self._update_connection_state(False)
            self.status_manager.update_status(StatusManager.STATUS_DISCONNECTED)

        except Exception as e:
            self.error_handler.handle_error(
                e,
                error_context="Server disconnection",
                user_friendly_msg="Failed to disconnect properly. The application will continue to function.",
            )

    def get_available_servers(self) -> List[Dict[str, Any]]:
        """
        Get the list of available MCP servers.

        Returns:
            List of server info dictionaries
        """
        current_time = time.time()
        if current_time - self._last_server_discovery_time < self._server_discovery_cache_timeout:
            logger.info("Using cached server discovery results")
            return self.server_discovery.available_servers

        try:
            self.server_discovery.discover_mcp_servers()
            self._last_server_discovery_time = current_time
            return self.server_discovery.available_servers
        except Exception as e:
            self.error_handler.handle_error(
                e,
                error_context="Server discovery",
                user_friendly_msg="Failed to discover available servers. Please check your network connection.",
            )
            return []

    async def process_query(self, query: str) -> None:
        """
        Process a user query through the MCP client.

        Args:
            query: The user query to process
        """
        if not self._mcp_client:
            error = ConnectionError("Not connected to any server")
            self.error_handler.handle_error(
                error,
                error_context="Query processing",
                user_friendly_msg="You are not connected to any server. Please connect first.",
            )
            return

        logger.info(f"Processing query: {query}")

        # Update status to processing query
        self.status_manager.update_status(StatusManager.STATUS_PROCESSING_QUERY)

        # Process the query
        try:
            await self._mcp_client.process_query(query)
            # Reset to idle state if we're connected, otherwise disconnected
            if self._is_connected and not self.status_manager.is_error:
                self.status_manager.update_status(StatusManager.STATUS_IDLE)
        except LogOnlyError as e:
            # Handle streaming errors with error handler
            self.error_handler.handle_error(
                e,
                error_context="Query processing",
                user_friendly_msg="Failed to get response from the language model. Please check your connection and try again.",
            )
        except Exception as e:
            # Handle other unexpected errors
            self.error_handler.handle_error(
                e,
                error_context="Query processing",
                user_friendly_msg=f"An error occurred while processing your query: {str(e)}",
            )

            # Reset to idle state if still connected
            if self._is_connected:
                self.status_manager.update_status(StatusManager.STATUS_IDLE)

    def set_connection_callback(self, callback):
        """Set a callback function to be called when connection state changes"""
        self._on_connection_changed = callback

    def _update_connection_state(self, value: bool) -> None:
        """
        Update the connection state and notify via callback

        Args:
            value: The new connection state
        """
        if self._is_connected != value:
            self._is_connected = value
            self._on_connection_changed(value)
