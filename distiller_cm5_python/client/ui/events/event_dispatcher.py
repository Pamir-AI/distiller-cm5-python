import json
import os
import time
import logging
from typing import Optional, Callable, List, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal

from distiller_cm5_python.client.ui.events.event_types import (
    MessageSchema,
    EventType,
    StatusType,
)

# Get logger instance for this module
logger = logging.getLogger(__name__)


class EventDispatcher(QObject):
    """
    Dispatches MessageSchema objects to listeners, optionally logging to file in debug mode.
    """

    # Signal for new MessageSchema objects
    message_dispatched = pyqtSignal(object)

    def __init__(self, debug: bool = False, log_path: Optional[str] = None):
        super().__init__()
        self.debug = debug
        self.log_path = log_path
        self._file = open(log_path, "a") if (debug and log_path) else None
        self._event_handlers: Dict[EventType, List[Callable]] = {}

        # Create a dedicated log directory for event logs if specified
        if debug and not log_path:
            log_dir = os.path.join(os.getcwd(), "event_logs")
            os.makedirs(log_dir, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            self.log_path = os.path.join(log_dir, f"event_log_{timestamp}.jsonl")
            self._file = open(self.log_path, "a")

    def dispatch(self, evt: MessageSchema):
        """
        Dispatch a MessageSchema event to all registered handlers.
        """
        # Handle MessageSchema
        if isinstance(evt, MessageSchema):
            # Log the event
            if self._file:
                self._file.write(evt.to_json() + "\n")
                self._file.flush()

            # Log to console in debug mode
            # logger.debug(f"[MessageSchema] {evt.dict()}")

            # Emit to registered signal handlers
            self.message_dispatched.emit(evt)

            # Call any registered handlers for this event type
            if evt.type in self._event_handlers:
                for handler in self._event_handlers[evt.type]:
                    try:
                        handler(evt)
                    except Exception as e:
                        logger.error(f"Error in event handler: {e}")

        elif not isinstance(evt, MessageSchema):
            logger.warning(f"Invalid event type received: {type(evt)}, expected MessageSchema")

    def register_handler(self, event_type: EventType, handler: Callable):
        """Register a handler for a specific event type"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        return self

    def unregister_handler(self, event_type: EventType, handler: Callable):
        """Unregister a handler for a specific event type"""
        if event_type in self._event_handlers and handler in self._event_handlers[event_type]:
            self._event_handlers[event_type].remove(handler)
        return self

    def close(self):
        """Close the log file if open"""
        if self._file:
            self._file.close()
            self._file = None
