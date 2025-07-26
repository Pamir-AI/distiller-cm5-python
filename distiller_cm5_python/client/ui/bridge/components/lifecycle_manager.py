"""
Lifecycle manager component for the MCPClientBridge.
Handles application lifecycle events such as startup, shutdown, and restart.
"""

from typing import Optional, Callable
import logging
import asyncio
import threading
import time
import os
import psutil

from distiller_cm5_python.client.ui.bridge.StatusManager import StatusManager
from distiller_cm5_python.client.ui.bridge.ConversationManager import (
    ConversationManager,
)
from distiller_cm5_python.client.mid_layer.mcp_client import MCPClient

logger = logging.getLogger(__name__)

# Exit delay constant
EXIT_DELAY_MS = 500  # milliseconds


class LifecycleManager:
    """
    Manages application lifecycle events.
    Handles graceful startup, shutdown, and restart.
    """

    def __init__(
        self, status_manager: StatusManager, conversation_manager: ConversationManager, bridge=None
    ):
        """
        Initialize the lifecycle manager.

        Args:
            status_manager: The status manager to update based on lifecycle events
            conversation_manager: The conversation manager to add lifecycle messages to
            bridge: Optional bridge instance for cleanup (added for WiFi setup cleanup)
        """
        self.status_manager = status_manager
        self.conversation_manager = conversation_manager
        self.bridge = bridge

    async def shutdown_process(self, mcp_client: Optional[MCPClient]) -> None:
        """
        Unified shutdown process to handle all cleanup.

        Args:
            mcp_client: The MCP client to clean up
        """
        logger.info("Bridge shutdown initiated")
        self.status_manager.update_status(StatusManager.STATUS_SHUTTING_DOWN)

        try:
            # Clean up bridge first (includes WiFi setup, e-ink, etc.)
            if self.bridge and hasattr(self.bridge, "cleanup"):
                try:
                    await self.bridge.cleanup()
                    logger.info("Completed bridge cleanup (includes WiFi setup and e-ink)")
                except Exception as e:
                    logger.error(f"Error during bridge cleanup: {e}", exc_info=True)

            # Clean up client if exists
            if mcp_client:
                try:
                    await mcp_client.cleanup()
                    logger.info("Completed MCP client cleanup")
                except Exception as e:
                    logger.error(f"Error during client cleanup: {e}", exc_info=True)

            # Terminate dangling processes
            self._terminate_dangling_processes()

            logger.info("Force quitting application from bridge")

            # Try to quit Qt application gracefully first
            try:
                from PyQt6.QtWidgets import QApplication

                app_instance = QApplication.instance()
                if app_instance:
                    logger.info("Requesting Qt application quit")
                    app_instance.quit()
                    # Give Qt a moment to process the quit request
                    await asyncio.sleep(0.2)
            except Exception as e:
                logger.error(f"Error requesting Qt quit: {e}")

            # Also stop the asyncio event loop
            try:
                loop = asyncio.get_running_loop()
                if loop and loop.is_running():
                    logger.info("Stopping asyncio event loop")
                    loop.stop()
            except Exception as e:
                logger.error(f"Error stopping asyncio loop: {e}")

            # Use threading for final exit as backup
            threading.Thread(target=self._force_exit, daemon=True).start()
            await asyncio.sleep(0.1)  # Short sleep to let logs flush

            # Force exit if Qt quit didn't work
            logger.info("Executing force exit")
            os._exit(0)  # Force immediate exit
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
            self._force_exit()

    def _force_exit(self) -> None:
        """Force the application to exit after a short delay."""
        time.sleep(EXIT_DELAY_MS / 1000.0)
        logger.info("Executing final force exit")
        self._terminate_dangling_processes(force=True)
        os._exit(0)

    def _terminate_dangling_processes(self, force: bool = False) -> None:
        """
        Find and terminate any dangling MCP processes.

        Args:
            force: Whether to force kill processes
        """
        logger.info("Checking for dangling MCP processes")

        try:
            # Find our process ID
            current_process = psutil.Process(os.getpid())
            children = current_process.children(recursive=True)

            for child in children:
                try:
                    # Check if it's an MCP-related process
                    if force or any(
                        mcp_name in " ".join(child.cmdline()).lower()
                        for mcp_name in ["mcp", "model-control"]
                    ):
                        logger.info(f"Terminating process {child.pid}: {' '.join(child.cmdline())}")
                        if force:
                            # Force kill
                            child.kill()
                        else:
                            # Try graceful termination first
                            child.terminate()
                            try:
                                child.wait(timeout=1)
                            except psutil.TimeoutExpired:
                                # Force kill if it doesn't terminate
                                logger.info(f"Process {child.pid} didn't terminate, force killing")
                                child.kill()
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                ):
                    # Process already gone or can't be accessed
                    pass
                except Exception as e:
                    logger.error(f"Error terminating process {child.pid}: {e}")
        except Exception as e:
            logger.error(f"Error finding/terminating dangling processes: {e}", exc_info=True)

    async def restart_application(
        self,
        is_connected: "property",
        mcp_client: Optional[MCPClient],
        disconnect_func: Callable,
        connect_server_func: Callable,
    ) -> None:
        """
        Restart the application without completely shutting down.

        Args:
            is_connected: Property indicating connection status
            mcp_client: The MCP client instance
            disconnect_func: Function to disconnect from server
            connect_server_func: Function to connect to server
        """
        try:
            logger.info("Starting application restart")
            self.status_manager.update_status(StatusManager.STATUS_RESTARTING)

            # Store the current server path for reconnection
            selected_server_path = None
            if mcp_client and hasattr(mcp_client, "server_script_path"):
                selected_server_path = getattr(mcp_client, "server_script_path", None)

            # Clear the conversation
            self.conversation_manager.clear()

            # Check connection state without using property directly
            bridge_obj = None
            try:
                # Get the bridge instance from the status manager's parent reference
                bridge_obj = getattr(self.status_manager, "parent", None)
            except Exception:
                logger.warning("Could not get bridge instance from status manager")

            # Use the bridge instance to check connection state if available
            current_is_connected = False
            if bridge_obj and hasattr(bridge_obj, "_is_connected"):
                current_is_connected = bridge_obj._is_connected

            # Disconnect from the server
            if current_is_connected:
                await disconnect_func()
                # Wait for disconnect to complete
                await asyncio.sleep(0.5)

            # Reset processing state
            self.status_manager.update_status(StatusManager.STATUS_DISCONNECTED)

            # Try to reconnect to the same server
            if selected_server_path and os.path.exists(selected_server_path):
                logger.info(f"Restarting with server: {selected_server_path}")

                # Extract server name for status messages
                server_name = (
                    os.path.basename(selected_server_path)
                    .replace("_server.py", "")
                    .replace(".py", "")
                )

                # Update UI to show connecting status
                self.status_manager.update_status(StatusManager.STATUS_CONNECTING)

                # Connect to the same server
                try:
                    await connect_server_func(server_name)
                except Exception as e:
                    logger.error(f"Failed to reconnect to server during restart: {e}")
                    # Fall back to server selection
                    await connect_server_func()
            else:
                # If no previous server or it doesn't exist, show server selection
                await connect_server_func()

            # Update status
            if bridge_obj and hasattr(bridge_obj, "_is_connected"):
                current_is_connected = bridge_obj._is_connected

            if current_is_connected:
                self.status_manager.update_status(StatusManager.STATUS_IDLE)
                logger.info("Application restart completed successfully")
            else:
                self.status_manager.update_status(StatusManager.STATUS_DISCONNECTED)
                logger.warning("Application restarted but not connected to server")

            logger.info("Application restart completed")

        except Exception as e:
            logger.error(f"Error during application restart: {e}", exc_info=True)
            self.status_manager.update_status(StatusManager.STATUS_ERROR)

    async def initialize_bridge(self, server_discovery_func: Callable) -> bool:
        """
        Initialize the bridge components.

        Args:
            server_discovery_func: Function to discover available servers

        Returns:
            True if initialization was successful, False otherwise
        """
        logger.info("Initializing bridge components")
        self.status_manager.update_status(StatusManager.STATUS_INITIALIZING)

        # Pre-discover available servers during initialization
        server_discovery_func()

        logger.info("Bridge initialization completed")
        return True
