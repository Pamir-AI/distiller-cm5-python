from PyQt6.QtCore import QObject, pyqtSignal
import logging

logger = logging.getLogger(__name__)


class StatusManager(QObject):
    """Manages the status system for the UI/client"""

    # Status constants - main states
    STATUS_IDLE = "idle"
    STATUS_INITIALIZING = "initializing"
    STATUS_CONNECTING = "connecting"
    STATUS_CONNECTED = "connected"
    STATUS_PROCESSING = "processing"
    STATUS_THINKING = "thinking"  # More specific processing state
    STATUS_PROCESSING_QUERY = "processing_query"  # When processing a query
    STATUS_EXECUTING_TOOL = "executing_tool"  # When executing a tool
    STATUS_RESTORING_CACHE = "restoring_cache"  # When restoring model cache
    STATUS_READY = "ready"
    STATUS_ERROR = "error"
    STATUS_DISCONNECTED = "disconnected"
    STATUS_RESTARTING = "restarting"
    STATUS_SHUTTING_DOWN = "shutting_down"
    STATUS_CONFIG_APPLIED = "config_applied"

    # Signal to update UI with status changes
    statusChanged = pyqtSignal(str, str)  # status, details

    def __init__(self, parent=None):
        """Initialize the status manager"""
        super().__init__(parent)
        self._current_status = self.STATUS_IDLE
        self._status_details = ""
        self._is_error = False  # Track error state
        logger.info("StatusManager initialized")

    def update_status(self, status, details="", **kwargs):
        """
        Update the current status and emit signals for UI

        Args:
            status: The new status string (use STATUS_* constants)
            details: Optional details about the status
            **kwargs: Additional keyword arguments, such as server_name, error
        """
        if "error" in kwargs:
            error_msg = kwargs["error"]
            details = f"Error: {error_msg}" if not details else details
            self._is_error = True

        # Process additional kwargs if needed
        if "server_name" in kwargs and not details:
            details = f"Connected to {kwargs['server_name']}"

        # Only update and emit signal if status actually changed
        status_changed = (
            self._current_status != status or self._status_details != details
        )

        if status_changed:
            # Add detailed logging of status transition
            logger.info(
                f"Status transition: {self._current_status} -> {status} (Details: {details})"
            )

            # Reset error flag if moving to a non-error state
            if status != self.STATUS_ERROR:
                self._is_error = False

            self._current_status = status
            self._status_details = details

            # Emit signal for UI components to update
            self.statusChanged.emit(status, details)

    def get_current_status(self):
        """
        Get the current status

        Returns:
            Tuple of (status, details)
        """
        return (self._current_status, self._status_details)

    @property
    def status(self):
        """Return the current status string."""
        return self._current_status

    @property
    def is_error(self):
        """Check if the system is in error state"""
        return self._is_error or self._current_status == self.STATUS_ERROR

    @property
    def is_processing(self):
        """Check if the system is in any processing state"""
        processing_states = [
            self.STATUS_PROCESSING,
            self.STATUS_THINKING,
            self.STATUS_PROCESSING_QUERY,
            self.STATUS_EXECUTING_TOOL,
            self.STATUS_RESTORING_CACHE,  # Add cache restoration as a processing state
        ]
        return self._current_status in processing_states

    def cleanup(self):
        """Clean up resources and reset status"""
        self.update_status(self.STATUS_IDLE)
        logger.info("StatusManager cleaned up")
