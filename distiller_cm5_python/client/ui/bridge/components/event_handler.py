"""
Event handling component for the MCPClientBridge.
Handles receiving events from the event dispatcher and forwarding them to appropriate handlers.
"""

from typing import Protocol, Union, cast
import logging
import time
import uuid

from PyQt6.QtCore import QObject, pyqtSignal

from distiller_cm5_python.client.ui.events.event_types import (
    EventType,
    StatusType,
    MessageSchema,
    CacheEvent,
)
from distiller_cm5_python.client.ui.events.event_dispatcher import EventDispatcher
from distiller_cm5_python.client.ui.bridge.StatusManager import StatusManager

logger = logging.getLogger(__name__)


class BridgeEventSignals(Protocol):
    """Protocol defining the required signals for event handling"""

    messageReceived: pyqtSignal
    actionReceived: pyqtSignal
    infoReceived: pyqtSignal
    warningReceived: pyqtSignal
    errorReceived: pyqtSignal
    functionReceived: pyqtSignal
    observationReceived: pyqtSignal
    planReceived: pyqtSignal
    statusChanged: pyqtSignal
    messageSchemaReceived: pyqtSignal
    cacheEventReceived: pyqtSignal


class BridgeEventHandler:
    """
    Handles events from the dispatcher and forwards them to the appropriate handlers.
    Decouples event handling from the main bridge class.
    """

    def __init__(
        self,
        dispatcher: EventDispatcher,
        status_manager: StatusManager,
        signal_source: Union[QObject, BridgeEventSignals],
        connected_property: "property",
    ):
        """
        Initialize the event handler.

        Args:
            dispatcher: The event dispatcher to receive events from
            status_manager: The status manager to update based on events
            signal_source: The object that provides signals for event emission
            connected_property: A property that indicates if the bridge is connected
        """
        self.dispatcher = dispatcher
        self.status_manager = status_manager
        self.signals = cast(BridgeEventSignals, signal_source)
        self.is_connected = connected_property

        # Track current message ID for bubble management
        self.current_message_id = None
        self.message_chunks = []

        # Get conversation manager reference from bridge if possible
        if hasattr(signal_source, "conversation_manager"):
            self.signals.conversation_manager = signal_source.conversation_manager
        else:
            self.signals.conversation_manager = None

        # Connect to the dispatcher
        self.dispatcher.message_dispatched.connect(self.handle_event)

    def handle_event(self, event: MessageSchema) -> None:
        """
        Handle events from the dispatcher.

        Args:
            event: The MessageSchema event to handle
        """
        try:
            # Handle new MessageSchema format
            if isinstance(event, MessageSchema):
                self._handle_message_schema(event)
            else:
                # This case should ideally not be reached if dispatcher only sends MessageSchema
                logger.error(f"Invalid event type received: {type(event)}")
                return
        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)

    def _handle_message_schema(self, event: MessageSchema) -> None:
        """
        Handle events in the MessageSchema format.

        Args:
            event: The MessageSchema event to handle
        """
        # Convert timestamp to string if it exists
        timestamp_str = str(event.timestamp) if event.timestamp else None

        # Emit the raw message schema event
        try:
            # Convert the MessageSchema to a dictionary for QML
            event_dict = event.dict()
            # Emit the messageSchemaReceived signal with the event data
            self.signals.messageSchemaReceived.emit(event_dict)
        except Exception as e:
            logger.error(f"Error converting MessageSchema to dict: {e}", exc_info=True)

        # Get conversation manager from the bridge if available
        conversation_manager = getattr(self.signals, "conversation_manager", None)

        # Handle different event types
        if (
            event.type == EventType.MESSAGE
        ):  # process message events from assistant text stream
            # Get status value, handling both enum and string cases
            status_value = (
                event.status.value if hasattr(event.status, "value") else event.status
            )

            # Handle streaming messages with bubble management
            if status_value == StatusType.IN_PROGRESS:
                # Check if this is a new message stream
                if event.id != self.current_message_id:
                    # Start new message stream
                    self.current_message_id = event.id
                    self.message_chunks = []

                # Accumulate message chunks
                self.message_chunks.append(event.content)
                # Emit the accumulated content to maintain proper message state in UI
                accumulated_content = "".join(self.message_chunks)
                if accumulated_content:
                    self.signals.messageReceived.emit(
                        accumulated_content, str(event.id), "", status_value
                    )

            elif status_value == StatusType.SUCCESS:
                # Complete the message
                if self.message_chunks:
                    complete_content = "".join(self.message_chunks)
                    self.signals.messageReceived.emit(
                        complete_content, str(event.id), timestamp_str, status_value
                    )
                    # Add to conversation history
                    if conversation_manager:
                        message = {
                            "timestamp": self._get_formatted_timestamp(),
                            "content": complete_content,
                            "type": "Message",
                        }
                        conversation_manager.add_message(message)

                # Reset tracking
                self.current_message_id = None
                self.message_chunks = []

                # Update status to idle when message is complete
                if self.is_connected:
                    self.status_manager.update_status(StatusManager.STATUS_IDLE)

        elif (
            event.type == EventType.ACTION
        ):  # process action events from tool call stream
            # Handle action events with status tracking
            status_value = (
                event.status.value if hasattr(event.status, "value") else event.status
            )
            if status_value == StatusType.IN_PROGRESS:
                self.status_manager.update_status(StatusManager.STATUS_EXECUTING_TOOL)
                # Check if this is a new action stream
                if event.id != self.current_message_id:
                    # Start new action stream
                    self.current_message_id = event.id
                    self.message_chunks = []

                # Accumulate action chunks
                self.message_chunks.append(event.content)
                # Emit the accumulated content
                accumulated_content = "".join(self.message_chunks)
                self.signals.actionReceived.emit(accumulated_content, str(event.id), "")

            elif status_value == StatusType.SUCCESS:
                # Complete the action
                if self.message_chunks:
                    # Use accumulated chunks for complete action
                    complete_content = "".join(self.message_chunks)
                    self.signals.actionReceived.emit(
                        complete_content, str(event.id), timestamp_str
                    )

                    # Add to conversation history
                    if conversation_manager:
                        message = {
                            "timestamp": self._get_formatted_timestamp(),
                            "content": complete_content,
                            "type": "Action",
                        }
                        conversation_manager.add_message(message)

                # Reset tracking
                self.current_message_id = None
                self.message_chunks = []

                # Update status when action is complete
                if self.is_connected:
                    self.status_manager.update_status(StatusManager.STATUS_IDLE)

        elif event.type == EventType.INFO:
            logger.debug(
                f"Handling INFO event: content='{event.content}', id={event.id}"
            )
            # INFO events are handled via status updates only - the UI doesn't
            # need to show these in the chat
            status_value = (
                event.status.value if hasattr(event.status, "value") else event.status
            )
            if status_value == StatusType.IN_PROGRESS:
                self.status_manager.update_status(StatusManager.STATUS_THINKING)
            elif status_value == StatusType.SUCCESS:
                # Update status when INFO event is complete
                if self.is_connected:
                    self.status_manager.update_status(StatusManager.STATUS_IDLE)

        elif event.type == EventType.WARNING:
            self.signals.warningReceived.emit(
                event.content, str(event.id), timestamp_str
            )

            # Add to conversation history
            if conversation_manager:
                message = {
                    "timestamp": self._get_formatted_timestamp(),
                    "content": f"{event.content}",
                    "type": "Warning",
                }
                conversation_manager.add_message(message)

        elif event.type == EventType.ERROR:
            self.signals.errorReceived.emit(event.content, str(event.id), timestamp_str)

            # Add to conversation history
            if conversation_manager:
                message = {
                    "timestamp": self._get_formatted_timestamp(),
                    "content": f"{event.content}",
                    "type": "Error",
                }
                conversation_manager.add_message(message)

        elif event.type == EventType.CACHE:
            # Handle cache events
            if hasattr(self.signals, "cacheEventReceived"):
                # If we have a dedicated handler, use it
                self.signals.cacheEventReceived.emit(
                    event.content, str(event.id), timestamp_str
                )
            else:
                # Fall back to info message if no dedicated handler
                self.signals.infoReceived.emit(
                    event.content, str(event.id), timestamp_str
                )

            # Update status based on cache operation status
            status_value = (
                event.status.value if hasattr(event.status, "value") else event.status
            )
            operation = getattr(event, "operation", "restoration")

            if operation == "restoration":
                if status_value == StatusType.IN_PROGRESS:
                    self.status_manager.update_status("restoring_cache", event.content)
                elif status_value == StatusType.SUCCESS:
                    self.status_manager.update_status("connected", event.content)
                elif status_value == StatusType.FAILED:
                    self.status_manager.update_status("error", event.content)

            # Cache operations don't need to be added to the conversation history

        elif event.type == EventType.OBSERVATION:
            # Handle observation events
            if hasattr(self.signals, "observationReceived"):
                self.signals.observationReceived.emit(
                    event.content, str(event.id), timestamp_str
                )
            else:
                # Fall back to info message if no dedicated handler
                self.signals.infoReceived.emit(
                    event.content, str(event.id), timestamp_str
                )

            # Add to conversation history
            if conversation_manager:
                message = {
                    "timestamp": self._get_formatted_timestamp(),
                    "content": f"{event.content}",
                    "type": "Observation",
                }
                conversation_manager.add_message(message)

        elif event.type == EventType.PLAN:
            # Handle plan events
            if hasattr(self.signals, "planReceived"):
                self.signals.planReceived.emit(
                    event.content, str(event.id), timestamp_str
                )
            else:
                # Fall back to info message if no dedicated handler
                self.signals.infoReceived.emit(
                    event.content, str(event.id), timestamp_str
                )

            # Add to conversation history
            if conversation_manager:
                message = {
                    "timestamp": self._get_formatted_timestamp(),
                    "content": f"{event.content}",
                    "type": "Plan",
                }
                conversation_manager.add_message(message)
                
        elif event.type == EventType.FUNCTION:
            # Handle function events
            if hasattr(self.signals, "functionReceived"):
                self.signals.functionReceived.emit(
                    event.content, str(event.id), timestamp_str
                )
            else:
                # Fall back to info message if no dedicated handler
                self.signals.infoReceived.emit(
                    event.content, str(event.id), timestamp_str
                )

            # Add to conversation history
            if conversation_manager:
                message = {
                    "timestamp": self._get_formatted_timestamp(),
                    "content": f"{event.content}",
                    "type": "Function",
                }
                conversation_manager.add_message(message)

        elif event.type == EventType.STATUS:
            # Check for specific component status events
            component = getattr(event, "component", None)
            status_value = (
                event.status.value if hasattr(event.status, "value") else event.status
            )

            if component == "connection":
                if status_value == StatusType.FAILED:
                    self.status_manager.update_status("error", event.content)
                elif status_value == StatusType.SUCCESS:
                    self.status_manager.update_status("connected", event.content)
                elif status_value == StatusType.IN_PROGRESS:
                    self.status_manager.update_status("connecting", event.content)
            else:
                # Handle other status events normally
                status_str = event.content
                self.status_manager.update_status(status_str)

            # Always emit the status changed signal
            self.signals.statusChanged.emit(event.content)

        else:
            logger.warning(f"Unknown event type: {event.type}")

    def _get_formatted_timestamp(self):
        """Get a formatted timestamp string for messages."""
        from datetime import datetime

        return datetime.now().strftime("%H:%M:%S")
