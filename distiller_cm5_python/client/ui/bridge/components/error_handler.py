"""
Error handling component for the MCPClientBridge.
Provides a unified error handling mechanism.
"""

from typing import Optional, Callable
import logging
import time
import uuid
import asyncio

from distiller_cm5_python.client.ui.events.event_types import (
    EventType,
    StatusType,
    MessageSchema,
)
from distiller_cm5_python.client.ui.events.event_dispatcher import EventDispatcher
from distiller_cm5_python.client.ui.bridge.StatusManager import StatusManager
from distiller_cm5_python.client.ui.bridge.ConversationManager import (
    ConversationManager,
)
from distiller_cm5_python.utils.distiller_exception import (
    UserVisibleError,
    LogOnlyError,
)

logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Centralized error handling for the bridge.
    Handles logging errors, updating status, and displaying user-friendly messages.
    """

    def __init__(
        self,
        status_manager: StatusManager,
        conversation_manager: ConversationManager,
        dispatcher: EventDispatcher,
        error_signal: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the error handler.

        Args:
            status_manager: The status manager to update on errors
            conversation_manager: The conversation manager to add error messages to
            dispatcher: The event dispatcher to send error events to
            error_signal: Optional signal to emit error messages to the UI
        """
        self.status_manager = status_manager
        self.conversation_manager = conversation_manager
        self.dispatcher = dispatcher
        self.error_signal = error_signal

    def handle_error(
        self,
        error: Exception,
        error_context: str = "Operation",
        log_error: bool = True,
        user_friendly_msg: Optional[str] = None,
    ) -> str:
        """
        Handle an error with standardized logging, status updates, and user notification.

        Args:
            error: The exception to handle
            error_context: The context in which the error occurred
            log_error: Whether to log the error
            user_friendly_msg: Optional user-friendly error message

        Returns:
            The user-facing error message
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
            error_msg = (
                user_friendly_msg
                or f"{error_context} timed out. Server may be busy or unavailable."
            )
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

        # Add error to conversation
        self.conversation_manager.add_message(
            {
                "timestamp": self.conversation_manager.get_timestamp(),
                "content": f"Error: {error_msg}",
            }
        )

        # Emit the error signal for QML if available
        if self.error_signal:
            self.error_signal(error_msg)

        # Force UI state reset with an error event
        error_event = MessageSchema(
            id=str(uuid.uuid4()),
            type=EventType.ERROR,
            content=error_msg,
            status=StatusType.FAILED,
            timestamp=time.time(),
        )
        self.dispatcher.dispatch(error_event)

        return error_msg
