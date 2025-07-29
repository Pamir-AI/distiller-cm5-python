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

        # NEW: Track conversation turn state to prevent premature idle transitions
        self.conversation_turn_active = False
        self.pending_events = set()  # Track pending event IDs
        self.last_event_time = 0

        # Get conversation manager reference from bridge if possible
        if hasattr(signal_source, "conversation_manager"):
            self.signals.conversation_manager = signal_source.conversation_manager
        else:
            self.signals.conversation_manager = None

        # Connect to the dispatcher
        self.dispatcher.message_dispatched.connect(self.handle_event)

    def _start_conversation_turn(self, event_id: str) -> None:
        """Start tracking a new conversation turn."""
        self.conversation_turn_active = True
        self.pending_events.add(event_id)
        self.last_event_time = time.time()
        logger.debug(f"Started conversation turn, pending events: {self.pending_events}")

    def _complete_event(self, event_id: str) -> None:
        """Mark an event as completed and check if conversation turn is finished."""
        self.pending_events.discard(event_id)
        self.last_event_time = time.time()
        logger.debug(f"Completed event {event_id}, remaining pending: {self.pending_events}")

    def _should_reset_to_idle(self) -> bool:
        """
        Determine if it's safe to reset to idle state.
        Only reset when no events are pending and enough time has passed.
        """
        # Don't reset if we have pending events
        if self.pending_events:
            # However, if too much time has passed (30 seconds), force reset to prevent permanent stuck state
            time_since_last_event = time.time() - self.last_event_time
            if time_since_last_event > 30.0:
                logger.warning(
                    f"Forcing reset to idle after 30s timeout. Pending events: {self.pending_events}"
                )
                self.pending_events.clear()  # Clear stuck events
                return True
            return False

        # Don't reset if we're not in a conversation turn
        if not self.conversation_turn_active:
            return False

        # Give a small grace period (2 seconds) for potential follow-up events
        time_since_last_event = time.time() - self.last_event_time
        if time_since_last_event < 2.0:
            return False

        return True

    def _reset_to_idle_if_safe(self) -> None:
        """Reset to idle only if it's safe to do so."""
        if self._should_reset_to_idle() and self.is_connected:
            self.conversation_turn_active = False
            self.status_manager.update_status(StatusManager.STATUS_IDLE)
            logger.debug("Reset to idle - conversation turn complete")

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
        if event.type == EventType.MESSAGE:  # process message events from assistant text stream
            # Get status value, handling both enum and string cases
            status_value = event.status.value if hasattr(event.status, "value") else event.status

            # Handle streaming messages with bubble management
            if status_value == StatusType.IN_PROGRESS:
                # Check if this is a new message stream
                if event.id != self.current_message_id:
                    # Start new message stream
                    self.current_message_id = event.id
                    self.message_chunks = []
                    # Start tracking this conversation turn
                    self._start_conversation_turn(str(event.id))

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

                # Mark this event as completed and reset to idle only if safe
                self._complete_event(str(event.id))
                self._reset_to_idle_if_safe()

        elif event.type == EventType.ACTION:  # process action events from tool call stream
            # Handle action events with status tracking
            status_value = event.status.value if hasattr(event.status, "value") else event.status
            if status_value == StatusType.IN_PROGRESS:
                self.status_manager.update_status(StatusManager.STATUS_EXECUTING_TOOL)
                # Check if this is a new action stream
                if event.id != self.current_message_id:
                    # Start new action stream
                    self.current_message_id = event.id
                    self.message_chunks = []
                    # Start tracking this conversation turn if not already active
                    if not self.conversation_turn_active:
                        self._start_conversation_turn(str(event.id))
                    else:
                        # Add to existing conversation turn
                        self.pending_events.add(str(event.id))

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
                    self.signals.actionReceived.emit(complete_content, str(event.id), timestamp_str)

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

                # Mark this event as completed and reset to idle only if safe
                self._complete_event(str(event.id))
                self._reset_to_idle_if_safe()

        elif event.type == EventType.INFO:
            logger.debug(f"Handling INFO event: content='{event.content}', id={event.id}")
            # if event.content:
            # self.signals.infoReceived.emit(
            #     event.content, str(event.id), timestamp_str
            # )
            # Add to conversation history
            # if conversation_manager:
            #     message = {
            #         "timestamp": self._get_formatted_timestamp(),
            #         "content": f"{event.content}",
            #         "type": "Info",
            #     }
            #     conversation_manager.add_message(message)

            status_value = event.status.value if hasattr(event.status, "value") else event.status
            if status_value == StatusType.IN_PROGRESS:
                self.status_manager.update_status(StatusManager.STATUS_THINKING)
                # Start tracking this conversation turn if not already active
                if not self.conversation_turn_active:
                    self._start_conversation_turn(str(event.id))
                else:
                    # Add to existing conversation turn
                    self.pending_events.add(str(event.id))
            elif status_value == StatusType.SUCCESS:
                # Mark this event as completed and reset to idle only if safe
                self._complete_event(str(event.id))
                self._reset_to_idle_if_safe()

        elif event.type == EventType.WARNING:
            self.signals.warningReceived.emit(event.content, str(event.id), timestamp_str)

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
                self.signals.cacheEventReceived.emit(event.content, str(event.id), timestamp_str)
            else:
                # Fall back to info message if no dedicated handler
                self.signals.infoReceived.emit(event.content, str(event.id), timestamp_str)

            # Update status based on cache operation status
            status_value = event.status.value if hasattr(event.status, "value") else event.status
            operation = getattr(event, "operation", "restoration")

            if operation == "restoration":
                if status_value == StatusType.IN_PROGRESS:
                    self.status_manager.update_status("restoring_cache", event.content)
                elif status_value == StatusType.SUCCESS:
                    self.status_manager.update_status("connected", event.content)
                elif status_value == StatusType.FAILED:
                    self.status_manager.update_status("error", event.content)

            # Add to conversation history
            # if conversation_manager:
            #     message = {
            #         "timestamp": self._get_formatted_timestamp(),
            #         "content": f"{event.content}",
            #         "type": "Cache Operation",
            #     }
            #     conversation_manager.add_message(message)

        elif event.type == EventType.OBSERVATION:
            # Handle observation events
            if hasattr(self.signals, "observationReceived"):
                self.signals.observationReceived.emit(event.content, str(event.id), timestamp_str)
            else:
                # Fall back to info message if no dedicated handler
                self.signals.infoReceived.emit(event.content, str(event.id), timestamp_str)

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
                self.signals.planReceived.emit(event.content, str(event.id), timestamp_str)
            else:
                # Fall back to info message if no dedicated handler
                self.signals.infoReceived.emit(event.content, str(event.id), timestamp_str)

            # Add to conversation history
            if conversation_manager:
                message = {
                    "timestamp": self._get_formatted_timestamp(),
                    "content": f"{event.content}",
                    "type": "Plan",
                }
                conversation_manager.add_message(message)

        elif event.type == EventType.STATUS:
            # Check for specific component status events
            component = getattr(event, "component", None)
            status_value = event.status.value if hasattr(event.status, "value") else event.status

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

    def create_error_event(self, error_msg: str) -> MessageSchema:
        """
        Create an error event.

        Args:
            error_msg: The error message

        Returns:
            A MessageSchema representing the error
        """
        return MessageSchema(
            id=str(uuid.uuid4()),
            type=EventType.ERROR,
            content=error_msg,
            status=StatusType.FAILED,
            timestamp=time.time(),
        )

    def _get_formatted_timestamp(self):
        """Get a formatted timestamp string for messages."""
        from datetime import datetime

        return datetime.now().strftime("%H:%M:%S")
