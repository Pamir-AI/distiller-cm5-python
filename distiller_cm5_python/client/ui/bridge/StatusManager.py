from distiller_cm5_python.utils.logger import logger


class StatusManager:
    """
    Manages the status of the MCPClientBridge.

    Handles status updates, formatting, and emitting signals.
    """

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

    def __init__(self, bridge):
        """Initialize the status manager.

        Args:
            bridge: The parent MCPClientBridge instance
        """
        self._bridge = bridge
        self._status = self.STATUS_INITIALIZING

    @property
    def status(self):
        """Get the current status string.

        Returns:
            The current status as a string
        """
        return self._status

    @status.setter
    def status(self, value):
        """Set the status directly and emit the signal.

        Args:
            value: The new status string
        """
        if self._status != value:
            self._status = value
            self._bridge.statusChanged.emit(self._status)
            logger.info(f"Status updated: {self._status}")

    def update_status(self, status: str, **kwargs):
        """Update the status with formatting and emit the statusChanged signal.

        Args:
            status: The status template string
            **kwargs: Format parameters for the status string
        """
        self._status = status.format(**kwargs)
        self._bridge.statusChanged.emit(self._status)
        logger.info(f"Status updated: {self._status}")
