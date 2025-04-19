# pyright: reportArgumentType=false
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer, pyqtProperty
from PyQt6.QtWidgets import QApplication
from distiller_cm5_python.client.mid_layer.mcp_client import MCPClient
from qasync import asyncSlot
from distiller_cm5_python.utils.config import *
from distiller_cm5_python.utils.logger import logger
import asyncio
import os
import sys
import time  # Add time import for debouncing

from distiller_cm5_python.client.ui.bridge.ConversationManager import ConversationManager
from distiller_cm5_python.client.ui.bridge.StatusManager import StatusManager
from distiller_cm5_python.client.ui.bridge.ServerDiscovery import ServerDiscovery
from distiller_cm5_python.client.ui.utils.NetworkUtils import NetworkUtils
from distiller_cm5_python.utils.distiller_exception import UserVisibleError, LogOnlyError


class MCPClientBridge(QObject):
    """
    Bridge between the UI and the MCPClient.

    Handles the communication between the QML UI and the Python backend.
    Manages conversation state, server discovery, and client connection.
    """

    conversationChanged = pyqtSignal()  # Signal for conversation changes
    logLevelChanged = pyqtSignal(str)  # Signal for logging level changes
    statusChanged = pyqtSignal(str)  # Signal for status changes
    availableServersChanged = pyqtSignal(list)  # Signal for available servers list
    isConnectedChanged = pyqtSignal(bool)  # Signal for connection status
    messageReceived = pyqtSignal(
        str, str
    )  # Signal for new messages (message, timestamp)
    listeningStarted = pyqtSignal()  # Signal for when listening starts
    listeningStopped = pyqtSignal()  # Signal for when listening stops
    errorOccurred = pyqtSignal(str)  # Signal for errors
    bridgeReady = pyqtSignal()  # Signal for when the bridge is fully initialized

    def __init__(self, parent=None):
        """MCPClientBridge initializes the MCPClient and manages the conversation state."""
        super().__init__(parent=parent)

        # Initialize sub-components
        self.status_manager = StatusManager(self)
        self.conversation_manager = ConversationManager(self)
        # Ensure streaming message is reset at startup
        self.conversation_manager.reset_streaming_message()
        self.server_discovery = ServerDiscovery(self)
        self.network_utils = NetworkUtils()

        # Initialize client-related properties
        self._is_connected = False
        self._is_ready = False
        self._loop = asyncio.get_event_loop()
        self.config_path = './'
        # Get logging level with proper default value
        self._current_log_level = config.get("logging", "level", default="DEBUG").upper()
        self._selected_server_path = None
        self.client = None  # Will be initialized when a server is selected
        
        # Server discovery cache for debouncing
        self._last_server_discovery_time = 0
        self._server_discovery_cache_timeout = 5  # seconds
        
        # Configuration cache for optimized access
        self._config_cache = {}
        self._config_dirty = False
        self._config_save_timer = None
        self._config_cache_timeout = 300  # seconds - how long to keep cached values
        self._config_cache_timestamps = {}  # Track when values were cached

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
        logger.info("Initializing bridge components")
        self.status_manager.update_status(StatusManager.STATUS_INITIALIZING)
        
        # Pre-discover available servers during initialization
        self.server_discovery.discover_mcp_servers()
        
        logger.info("Bridge initialization completed")
        return True

    @pyqtSlot(result=str)
    def get_status(self):
        """Return the current status of the client"""
        return self.status_manager.status

    @pyqtSlot(result=list)
    def get_conversation(self):
        """Return the current conversation as a list of formatted messages"""
        return self.conversation_manager.get_formatted_messages()

    @asyncSlot(str)
    async def submit_query(self, query: str):
        """Submit a query to the server and update the conversation"""
        try:
            if not query.strip():
                return
                
            if not self._is_connected:
                raise ConnectionError("Not connected to any server. Please connect first.")
                
            # Add user message
            user_message = {
                "timestamp": self.conversation_manager.get_timestamp(),
                "content": f"You: {query}",
            }
            self.conversation_manager.add_message(user_message)
            logger.info(f"User query added to conversation: {query}")
            
            # Process the query in a separate task to avoid blocking the UI
            # This is particularly important for long running queries
            asyncio.create_task(self._process_query_task(query))
            
        except Exception as e:
            self._handle_error(e, "Query submission", user_friendly_msg="Failed to submit query. Please check your connection and try again.")
        
    async def _process_query_task(self, query: str):
        """Process query in a separate task to avoid blocking the UI thread."""
        try:
            await self.process_query(query)
        except Exception as e:
            self._handle_error(e, "Query processing", user_friendly_msg=f"Error processing query: {query[:30]}...")

    @pyqtSlot()
    def clear_conversation(self):
        """Clear the conversation history"""
        self.conversation_manager.clear()
        clear_message = {
            "timestamp": self.conversation_manager.get_timestamp(),
            "content": "Conversation cleared.",
        }
        self.conversation_manager.add_message(clear_message)
        logger.info("Conversation cleared")

    @pyqtSlot(bool)
    def toggle_streaming(self, enabled: bool):
        """Enable or disable streaming mode, streaming here refers to the ability to receive partial responses from the server."""
        if self.client is None:
            logger.error("Client is not initialized")
            return
        self.client.streaming = enabled
        self.client.llm_provider.streaming = enabled
        status = "enabled" if enabled else "disabled"
        self.status_manager.status = f"Streaming {status}"
        self.conversation_manager.add_message(
            {
                "timestamp": self.conversation_manager.get_timestamp(),
                "content": f"Streaming {status}",
            }
        )
        logger.info(f"Streaming {status}")
        self.statusChanged.emit(self.status_manager.status)

    @pyqtSlot(str, str, result="QVariant")
    def getConfigValue(self, section: str, key: str) -> str:
        """Get a configuration value, always returning a string.
        Uses an in-memory cache to reduce disk I/O and improve UI responsiveness.
        """
        # Generate a cache key for this config value
        cache_key = f"{section}.{key}"
        current_time = time.time()
        
        # Check if the value is in the cache and not expired
        if (cache_key in self._config_cache and 
            current_time - self._config_cache_timestamps.get(cache_key, 0) < self._config_cache_timeout):
            logger.debug(f"Cache hit for {cache_key}")
            return self._config_cache[cache_key]
        
        # Not in cache or expired, need to fetch from config
        logger.debug(f"Cache miss for {cache_key}, fetching from config")
        
        # Get the active provider name for LLM-specific configs
        if cache_key == "active_llm_provider":
            value = config.get("active_llm_provider")
        # Special cases for provider-specific configuration
        elif section == "llm":
            # Map old flat "llm" section to new "llm_providers.{active_provider}" structure
            active_provider_name = config.get("active_llm_provider")
            value = config.get("llm_providers", active_provider_name, key)
            logger.debug(
                f"Getting provider config value {key} for {active_provider_name}: {value} (type: {type(value)})"
            )
        elif section == "llama_cpp" and key == "start_wait_time":
            # Special case for llama_cpp specific settings
            value = config.get(section, key, default=30)
            logger.debug(
                f"Getting config value for {section}.{key}: {value} (type: {type(value)})"
            )
        else:
            # Regular configuration paths
            value = config.get(section, key)
            logger.debug(
                f"Getting config value for {section}.{key}: {value} (type: {type(value)})"
            )
        
        # Format the value for QML
        if value is None:
            logger.debug(f"Value is None, returning empty string")
            result = ""
        elif isinstance(value, list):
            if key == "stop":
                # For stop sequences, escape special characters for QML
                result = "\n".join(
                    str(v).encode("unicode_escape").decode("utf-8") for v in value
                )
            else:
                result = ",".join(str(v) for v in value)
        elif section == "logging" and key == "level":
            # Return the current log level in uppercase
            result = self._current_log_level
        else:
            result = str(value)
            
        # Cache the result
        self._config_cache[cache_key] = result
        self._config_cache_timestamps[cache_key] = current_time
        
        logger.debug(f"Cached value for {cache_key}: {result}")
        return result

    @pyqtSlot(str, str, "QVariant")
    def setConfigValue(self, section: str, key: str, value):
        """Set a configuration value and update the cache."""
        # Cache key for consistent cache management 
        cache_key = f"{section}.{key}"
        logger.debug(f"Setting config value: {cache_key} = {value}")

        # Process the value first
        if key == "stop" and isinstance(value, str):
            # For stop sequences, escape special characters for QML
            processed_value = [
                v.encode("utf-8").decode("unicode_escape")
                for v in value.split("\n")
                if v
            ]
        elif key in ["timeout", "top_k", "n_ctx", "max_tokens", "streaming_chunk_size"]:
            processed_value = int(value) if value != "" else 0
        elif key in ["temperature", "top_p", "repetition_penalty"]:
            processed_value = float(value) if value != "" else 0.0
        elif key == "streaming" or key == "file_enabled":
            processed_value = bool(value)
        elif section == "logging" and key == "level":
            processed_value = value.upper()
            # Update the current log level cache
            self._current_log_level = processed_value
        else:
            processed_value = value

        # Special cases for provider-specific configuration
        if section == "llm":
            # Map flat "llm" section to proper nested path
            active_provider_name = self.getConfigValue("active_llm_provider", "")
            config.set("llm_providers", active_provider_name, key, processed_value)
            logger.debug(f"Setting LLM provider config: llm_providers.{active_provider_name}.{key} = {processed_value}")
            
            # Update the cache for this specific provider setting
            provider_cache_key = f"llm_providers.{active_provider_name}.{key}"
            self._update_config_cache(provider_cache_key, str(processed_value))
        elif section == "llama_cpp" and key == "start_wait_time":
            # Special case for llama_cpp specific settings
            config.set(section, key, processed_value)
            self._update_config_cache(cache_key, str(processed_value))
        else:
            # Regular configuration paths
            config.set(section, key, processed_value)
            self._update_config_cache(cache_key, str(processed_value))
        
        # Mark configuration as dirty for delayed save
        self._config_dirty = True
        
        # Signal that config has changed - might want to emit a dedicated signal if needed
        # self.configChanged.emit(section, key)
        
    def _update_config_cache(self, cache_key, value):
        """Update the configuration cache with a new value."""
        logger.debug(f"Updating config cache: {cache_key} = {value}")
        self._config_cache[cache_key] = value
        self._config_cache_timestamps[cache_key] = time.time()

    @asyncSlot()
    async def applyConfig(self):
        """Apply configuration changes by restarting the client."""
        try:
            self.status_manager.update_status(StatusManager.STATUS_INITIALIZING)
            self.conversation_manager.add_message(
                {
                    "timestamp": self.conversation_manager.get_timestamp(),
                    "content": "Applying configuration changes...",
                }
            )

            # Store the current conversation
            current_conversation = self.conversation_manager.get_messages_copy()

            # Wait for any pending configuration saves to complete
            if self._config_save_timer and not self._config_save_timer.done():
                try:
                    await self._config_save_timer
                except asyncio.CancelledError:
                    # The timer was cancelled, which is fine - just means we'll save now
                    pass
                except Exception as save_error:
                    logger.warning(f"Error in pending config save: {save_error}")
                    
            # Ensure configuration is saved to disk if there are pending changes
            if self._config_dirty:
                try:
                    config.save_to_file(self.config_path)
                    self._config_dirty = False
                    logger.info(f"Configuration saved successfully before apply")
                except Exception as save_error:
                    self._handle_error(save_error, "Config save", 
                        user_friendly_msg=f"Warning: Could not save pending changes: {str(save_error)}")

            # Clean up existing client
            if self.client:
                self.conversation_manager.add_message(
                    {
                        "timestamp": self.conversation_manager.get_timestamp(),
                        "content": "Disconnecting from server...",
                    }
                )

                # First attempt - normal cleanup
                try:
                    cleanup_task = asyncio.create_task(self.client.cleanup())
                    await asyncio.wait_for(cleanup_task, timeout=5.0)
                    await asyncio.sleep(1)
                except asyncio.TimeoutError:
                    logger.warning("Cleanup timeout during configuration apply, forcing disconnect")
                    self.conversation_manager.add_message(
                        {
                            "timestamp": self.conversation_manager.get_timestamp(),
                            "content": "Cleanup is taking longer than expected, forcing disconnect...",
                        }
                    )
                except Exception as cleanup_error:
                    # Use the centralized error handler with specific context
                    self._handle_error(
                        cleanup_error, 
                        "Client cleanup", 
                        user_friendly_msg="Warning: Client resources may not be fully released."
                    )

                # Ensure client is fully reset regardless of cleanup success
                self.client = None
                self.is_connected = False
                self.isConnectedChanged.emit(False)

            # Extra delay to ensure all resources are released
            await asyncio.sleep(1.0)

            # Reload the configuration from file
            self.conversation_manager.add_message(
                {
                    "timestamp": self.conversation_manager.get_timestamp(),
                    "content": "Reloading configuration...",
                }
            )
            
            try:
                # Clear configuration cache before reload to ensure fresh values
                self._config_cache = {}
                self._config_cache_timestamps = {}
                config.reload()
                logger.info("Configuration cache cleared and config reloaded")
            except Exception as config_error:
                raise ValueError(f"Failed to reload configuration: {str(config_error)}. Check your config file for syntax errors.")

            # Add a small delay after config reload
            await asyncio.sleep(0.5)

            # Update global variables after config reload
            global SERVER_URL, MODEL_NAME, PROVIDER_TYPE, API_KEY, TIMEOUT, STREAMING_ENABLED
            
            try:
                # Get the active provider configuration
                active_provider_name = config.get("active_llm_provider")
                if not active_provider_name:
                    raise ValueError("No active LLM provider specified in configuration.")
                    
                active_provider_config = config.get("llm_providers", active_provider_name)
                if not active_provider_config:
                    raise ValueError(f"Configuration for provider '{active_provider_name}' not found.")
                
                # Update global variables from the active provider
                SERVER_URL = active_provider_config.get("server_url")
                if not SERVER_URL:
                    raise ValueError(f"No server URL specified for provider '{active_provider_name}'.")
                    
                MODEL_NAME = active_provider_config.get("model_name")
                if not MODEL_NAME:
                    raise ValueError(f"No model name specified for provider '{active_provider_name}'.")
                    
                PROVIDER_TYPE = active_provider_config.get("provider_type", active_provider_name)
                API_KEY = active_provider_config.get("api_key", "")
                TIMEOUT = active_provider_config.get("timeout", 120)
                STREAMING_ENABLED = active_provider_config.get("streaming", True)
            except ValueError as config_value_error:
                # Re-raise with more specific context
                raise ValueError(f"Configuration error: {str(config_value_error)}")
            except Exception as config_extract_error:
                # Re-raise unexpected errors with generic message
                raise ValueError(f"Error extracting configuration values: {str(config_extract_error)}")

            # Create new client with updated config
            self.conversation_manager.add_message(
                {
                    "timestamp": self.conversation_manager.get_timestamp(),
                    "content": "Creating new client with updated configuration...",
                }
            )

            # Reconnect if previously connected
            if self._selected_server_path:
                await self._connect_to_selected_server(
                    os.path.basename(self._selected_server_path)
                )

            self.status_manager.update_status(StatusManager.STATUS_CONFIG_APPLIED)
            # Ensure we keep current conversation
            self.conversation_manager.set_messages(current_conversation)
            self.conversation_manager.add_message(
                {
                    "timestamp": self.conversation_manager.get_timestamp(),
                    "content": "Configuration applied successfully.",
                }
            )

        except Exception as e:
            self._handle_error(e, "Configuration apply", 
                user_friendly_msg=f"Failed to apply configuration changes: {str(e)}")

    @pyqtSlot()
    def saveConfigToFile(self):
        """Save the current configuration to file with debouncing.
        
        Uses a timer to debounce rapid save requests, ensuring we don't
        repeatedly write to disk when multiple settings are changed in succession.
        """
        if not self._config_dirty:
            logger.debug("Configuration not dirty, skipping save")
            return
            
        logger.info(f"Scheduling configuration save to {self.config_path}")
        
        # Cancel existing timer if it's running
        if self._config_save_timer and not self._config_save_timer.done():
            self._config_save_timer.cancel()
            
        # Schedule a new save with a delay
        self._config_save_timer = asyncio.create_task(self._debounced_save_config())
        
    async def _debounced_save_config(self):
        """Perform the actual configuration save after a delay."""
        # Delay for a moment to allow batching multiple changes
        await asyncio.sleep(1.0)
        
        try:
            logger.info(f"Saving configuration to {self.config_path}")
            config.save_to_file(self.config_path)
            self._config_dirty = False
            logger.info(f"Configuration saved successfully to {self.config_path}")
        except Exception as e:
            self._handle_error(e, "Config save", 
                user_friendly_msg=f"Failed to save configuration: {str(e)}")

    async def connect_to_server(self):
        """Ask the user to select a server from the list of available servers."""
        self.status_manager.update_status(StatusManager.STATUS_INITIALIZING)

        if not self.server_discovery.available_servers:
            self.server_discovery.discover_mcp_servers()

        if not self.server_discovery.available_servers:
            self.status_manager.update_status(
                StatusManager.STATUS_ERROR, error="No MCP servers found"
            )
            self.conversation_manager.add_message(
                {
                    "timestamp": self.conversation_manager.get_timestamp(),
                    "content": "Error: No MCP servers found.",
                }
            )
            self.errorOccurred.emit("No MCP servers found")
            return False

        # Wait for user to select a server in UI before proceeding
        logger.info("Available servers discovered. Waiting for user selection.")
        self.status_manager.update_status(StatusManager.STATUS_DISCONNECTED)
        self.availableServersChanged.emit(self.server_discovery.available_servers)

        return True

    async def process_query(self, query: str):
        """Process the user query and handle the response from the server."""
        try:
            if not self.client:
                raise ConnectionError("Not connected to any server. Please connect first.")

            self.status_manager.update_status(StatusManager.STATUS_PROCESSING)

            # Reset any existing streaming message to ensure we don't append to it
            # This is crucial to prevent new responses from being added to previous chat bubbles
            self.conversation_manager.reset_streaming_message()
            
            # Start tracking response content
            assistant_message = {
                "timestamp": self.conversation_manager.get_timestamp(),
                "content": "",
            }
            self.conversation_manager.add_message(assistant_message)
            self.conversation_manager.current_streaming_message = assistant_message

            # Use a batching mechanism for updating the UI to avoid excessive redraws
            last_update_time = time.time()
            update_interval = 0.05  # 50ms minimum between UI updates
            accumulated_chunks = ""

            self.status_manager.update_status(StatusManager.STATUS_STREAMING)

            # Use the MCPClient process_query interface, which now returns a generator for streaming responses
            async for chunk in self.client.process_query(query):
                if chunk.startswith("\n[Error:") or chunk.startswith("\n[Unexpected Error:") or chunk.startswith("\n[Reached max tool iterations"):
                    # Error messages from the MCP client
                    if self.conversation_manager.current_streaming_message:
                        self.conversation_manager.current_streaming_message["content"] += chunk
                        # Force immediate update for error messages
                        self.conversationChanged.emit()
                    continue
                
                # Handle special marker to create a new message bubble after tool calls
                if chunk == "__NEW_RESPONSE_AFTER_TOOL_CALLS__":
                    # Reset the current streaming message to ensure we create a new one
                    self.conversation_manager.reset_streaming_message()
                    # Create a new message bubble for the response after tool calls
                    assistant_message = {
                        "timestamp": self.conversation_manager.get_timestamp(),
                        "content": "",
                    }
                    self.conversation_manager.add_message(assistant_message)
                    self.conversation_manager.current_streaming_message = assistant_message
                    # Reset accumulated chunks for the new message
                    accumulated_chunks = ""
                    continue

                # If this is a new response after tool calls (in case marker wasn't received)
                if chunk and chunk.strip() and not self.conversation_manager.current_streaming_message:
                    # Create a new message bubble for the response after tool calls
                    logger.info("Creating new message bubble for response after tool calls")
                    assistant_message = {
                        "timestamp": self.conversation_manager.get_timestamp(),
                        "content": "",
                    }
                    self.conversation_manager.add_message(assistant_message)
                    self.conversation_manager.current_streaming_message = assistant_message
                    # Reset accumulated chunks for the new message
                    accumulated_chunks = ""

                if self.conversation_manager.current_streaming_message:
                    # Accumulate chunks before updating the UI
                    accumulated_chunks += chunk
                    
                    # Update the message content with the new chunk
                    self.conversation_manager.current_streaming_message["content"] += chunk
                    
                    # Only update the UI at the specified interval to avoid excessive redraws
                    current_time = time.time()
                    if current_time - last_update_time >= update_interval:
                        self.conversationChanged.emit()
                        last_update_time = current_time

            # Final update after streaming is complete
            self.status_manager.update_status(StatusManager.STATUS_IDLE)
            
            # Force a final UI update to ensure the last chunks are displayed
            if accumulated_chunks:
                self.conversationChanged.emit()

            # Emit the messageReceived signal when the response is complete
            if self.conversation_manager.current_streaming_message:
                timestamp = self.conversation_manager.current_streaming_message[
                    "timestamp"
                ]
                message = self.conversation_manager.current_streaming_message["content"]
                self.conversation_manager.reset_streaming_message()
                self.messageReceived.emit(message, timestamp)

        except Exception as e:
            self._handle_error(e, "Query processing", 
                user_friendly_msg="Failed to process your query. Please check your connection and try again.")

    async def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up MCPClientBridge resources")
        if self.client:
            try:
                await self.client.cleanup()
                self.client = None
                logger.info("Client cleanup completed")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}", exc_info=True)
                # Ensure client is set to None even if cleanup fails
                self.client = None

        # Reset conversation state to free memory
        if hasattr(self, 'conversation_manager') and self.conversation_manager:
            self.conversation_manager.reset_streaming_message()
            # Only keep the last 5 messages to free memory
            messages = self.conversation_manager.get_messages()
            if len(messages) > 5:
                self.conversation_manager.set_messages(messages[-5:])
        
        # Reset server discovery cache
        if hasattr(self, '_last_server_discovery_time'):
            self._last_server_discovery_time = 0

        self.is_connected = False
        self.status_manager.update_status(StatusManager.STATUS_DISCONNECTED)
        logger.info("MCPClientBridge cleanup completed")

    @pyqtSlot()
    def reset_status(self):
        """Reset the status to idle."""
        if self._is_connected:
            self.status_manager.update_status(StatusManager.STATUS_IDLE)
        else:
            self.status_manager.update_status(StatusManager.STATUS_DISCONNECTED)

    @pyqtSlot()
    def shutdown(self):
        """Handle application shutdown gracefully."""
        logger.info("Shutdown requested")
        self.status_manager.update_status(StatusManager.STATUS_SHUTTING_DOWN)

        try:
            # Schedule cleanup to run on the event loop
            coro = self._do_shutdown_cleanup()
            asyncio.create_task(coro)

            # We'll also set a timer to force quit after a timeout
            # This ensures the app exits even if async cleanup hangs
            QTimer.singleShot(5000, self._force_quit)

            logger.info("Shutdown initiated")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
            self._force_quit()

    def _force_quit(self):
        """Force the application to quit if normal shutdown doesn't complete."""
        logger.warning("Forcing application to quit")
        app_instance = QApplication.instance()
        if app_instance:
            app_instance.quit()
        else:
            logger.error("Failed to get QApplication instance for quit")
            # Force exit as fallback
            sys.exit(1)

    async def _do_shutdown_cleanup(self):
        """Perform cleanup operations during shutdown."""
        try:
            logger.info("Performing shutdown cleanup")

            # Disconnect from server
            if self.client:
                logger.info("Cleaning up client during shutdown")
                try:
                    await asyncio.wait_for(self.client.cleanup(), timeout=3.0)
                except asyncio.TimeoutError:
                    logger.warning("Client cleanup timeout during shutdown")
                except Exception as e:
                    logger.error(
                        f"Error cleaning up client during shutdown: {e}", exc_info=True
                    )
                finally:
                    self.client = None

            logger.info("Shutdown cleanup completed")
        except Exception as e:
            logger.error(f"Error during shutdown cleanup: {e}", exc_info=True)
        finally:
            # Ensure the application quits
            app_instance = QApplication.instance()
            if app_instance:
                app_instance.quit()
            else:
                logger.error("Failed to get QApplication instance for quit")
                # Force exit as fallback
                sys.exit(1)

    @pyqtSlot()
    def getAvailableServers(self):
        """Get the list of available MCP servers."""
        current_time = time.time()
        if current_time - self._last_server_discovery_time < self._server_discovery_cache_timeout:
            logger.info("Using cached server discovery results")
            self.availableServersChanged.emit(self.server_discovery.available_servers)
            return self.server_discovery.available_servers

        self.server_discovery.discover_mcp_servers()
        self.availableServersChanged.emit(self.server_discovery.available_servers)
        self._last_server_discovery_time = current_time
        return self.server_discovery.available_servers

    @pyqtSlot(str)
    def setServerPath(self, server_path):
        """Set the path to the MCP server script."""
        logger.info(f"Setting server path: {server_path}")
        self._selected_server_path = server_path
        # Connection will be handled explicitly by the UI

    @pyqtSlot(result=str)
    def connectToServer(self):
        """Connect to the selected MCP server without blocking the UI thread."""
        try:
            if not self._selected_server_path:
                raise ValueError("No server selected. Please choose a server before connecting.")

            # Extract server name for status messages
            server_name = (
                os.path.basename(self._selected_server_path)
                .replace("_server.py", "")
                .replace(".py", "")
            )

            if not os.path.exists(self._selected_server_path):
                raise FileNotFoundError(f"Server script not found: {self._selected_server_path}")

            # Update UI immediately to show connecting status
            self.status_manager.update_status(StatusManager.STATUS_CONNECTING)
            
            # Create task to connect in the background
            asyncio.create_task(self._connect_to_selected_server(server_name))
            return ""  # Empty string indicates success (no error)
            
        except Exception as e:
            error_msg = self._handle_error(e, "Server connection", 
                          user_friendly_msg=f"Failed to connect to server: {str(e)}")
            return error_msg  # Return error message string

    async def _connect_to_selected_server(self, server_name):
        """Connect to the selected server asynchronously with enhanced error handling."""
        try:
            # Status update moved to the calling method for immediate UI feedback
            self.conversation_manager.add_message(
                {
                    "timestamp": self.conversation_manager.get_timestamp(),
                    "content": f"Connecting to server: {server_name}...",
                }
            )

            # Create new client if needed
            if not self.client:
                self.client = MCPClient(
                    streaming=STREAMING_ENABLED,
                    llm_server_url=SERVER_URL,
                    provider_type=PROVIDER_TYPE,
                    model=MODEL_NAME,
                    api_key=API_KEY,
                    timeout=TIMEOUT,
                )

            # Connect to server with explicit timeout to prevent hanging
            try:
                connect_task = self.client.connect_to_server(self._selected_server_path)
                connected = await asyncio.wait_for(connect_task, timeout=30.0)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Connection to {server_name} timed out after 30 seconds. Server may be busy or unreachable.")

            if not connected:
                raise ConnectionError(f"Failed to establish connection with {server_name} server. Check server status and configuration.")

            self.is_connected = True
            server_display_name = self.client.server_name or server_name
            self.status_manager.update_status(
                StatusManager.STATUS_CONNECTED, server_name=server_display_name
            )
            self.conversation_manager.add_message(
                {
                    "timestamp": self.conversation_manager.get_timestamp(),
                    "content": f"Connected to {server_display_name}",
                }
            )
        except Exception as e:
            # Ensure client is reset in case of errors
            if self.client:
                try:
                    await self.client.cleanup()
                except Exception as cleanup_e:
                    logger.error(f"Error cleaning up client after connection failure: {cleanup_e}")
                finally:
                    self.client = None

            self._handle_error(e, f"Connection to server '{server_name}'")

    @pyqtSlot(result=bool)
    def isConnected(self):
        """Check if the client is connected to a server."""
        return self._is_connected

    @pyqtSlot()
    def startListening(self):
        """Start voice listening (emit the signal for UI update)."""
        try:
            logger.info("Voice activation requested")
            
            # Check if client is connected
            if not self._is_connected:
                raise ConnectionError("Cannot activate voice: not connected to any server.")
                
            # Emit signal for UI update
            self.listeningStarted.emit()
            
            # In this version, we indicate that voice is not yet implemented
            # This is a placeholder for future implementation with Whisper or similar
            raise NotImplementedError("Voice activation is not implemented in this version.")
            
        except Exception as e:
            self._handle_error(e, "Voice activation", 
                user_friendly_msg="Voice activation is not available in this version.")
            # Still emit the signal to update UI appropriately
            self.listeningStopped.emit()

    @pyqtSlot()
    def stopListening(self):
        """Stop voice listening (emit the signal for UI update)."""
        try:
            logger.info("Voice deactivation requested")
            # Emit signal for UI update
            self.listeningStopped.emit()
            self.status_manager.update_status(StatusManager.STATUS_IDLE)
        except Exception as e:
            self._handle_error(e, "Voice deactivation")
            
    @pyqtSlot()
    def disconnectFromServer(self):
        """Disconnect from the MCP server."""
        logger.info("Disconnecting from server")

        async def _do_disconnect():
            try:
                if self.client:
                    await self.client.cleanup()
                    self.client = None
                self.is_connected = False
                self.status_manager.update_status(StatusManager.STATUS_DISCONNECTED)
                self.conversation_manager.add_message(
                    {
                        "timestamp": self.conversation_manager.get_timestamp(),
                        "content": "Disconnected from server",
                    }
                )
            except Exception as e:
                self._handle_error(e, "Server disconnection", 
                    user_friendly_msg="Error disconnecting from server. Some resources may not be properly released.")

        asyncio.create_task(_do_disconnect())

    @pyqtSlot(result=str)
    def getWifiIpAddress(self):
        """Get the WiFi IP address of the system."""
        return self.network_utils.get_wifi_ip_address()

    def _handle_error(self, error, error_context="Operation", log_error=True, user_friendly_msg=None):
        """Centralized error handling for consistent error reporting to UI and logs.
        
        Args:
            error: The exception that occurred
            error_context: Description of what operation was being performed
            log_error: Whether to log the error with traceback
            user_friendly_msg: Optional user-friendly message override
        
        Returns:
            Formatted error message that was emitted
        """
        # Format different error types appropriately
        if isinstance(error, UserVisibleError):
            # UserVisibleError is already formatted for end users
            error_msg = str(error)
            log_with_traceback = False
        elif isinstance(error, LogOnlyError):
            # LogOnlyError should be logged with details but shown with generic message
            error_msg = user_friendly_msg or f"{error_context} failed. See logs for details."
            log_with_traceback = True
        elif isinstance(error, TimeoutError) or isinstance(error, asyncio.TimeoutError):
            error_msg = user_friendly_msg or f"{error_context} timed out. Server may be busy or unavailable."
            log_with_traceback = True
        elif isinstance(error, FileNotFoundError):
            error_msg = user_friendly_msg or f"Required file not found: {str(error)}"
            log_with_traceback = False
        elif isinstance(error, ConnectionError):
            error_msg = user_friendly_msg or f"Connection error: {str(error)}"
            log_with_traceback = True
        else:
            # For unexpected errors, use a generic message unless overridden
            error_msg = user_friendly_msg or f"{error_context} failed: {str(error)}"
            log_with_traceback = True
        
        # Log the error appropriately
        if log_error:
            if log_with_traceback:
                logger.error(f"{error_context} error: {error}", exc_info=True)
            else:
                logger.error(f"{error_context} error: {error}")
        
        # Update status and conversation with error
        self.status_manager.update_status(StatusManager.STATUS_ERROR, error=error_msg)
        
        # Add error to conversation if it's not already there
        self.conversation_manager.add_message({
            "timestamp": self.conversation_manager.get_timestamp(),
            "content": f"Error: {error_msg}"
        })
        
        # Emit the error signal for QML
        self.errorOccurred.emit(error_msg)
        
        return error_msg
