from datetime import datetime
import time
from PyQt6.QtCore import QTimer


class ConversationManager:
    """
    Manages the conversation history for the MCPClientBridge.

    Handles message storage, formatting, and streaming message tracking.
    """

    def __init__(self, bridge):
        """Initialize the conversation manager.

        Args:
            bridge: The parent MCPClientBridge instance
        """
        self._bridge = bridge
        self._conversation = []
        self.current_streaming_message: dict[str, str] | None = None

        # Batch update mechanism
        self._update_pending = False
        self._last_update_time = 0
        self._update_interval = 0.5  # seconds, for batching UI updates

    def _schedule_update(self):
        """Schedule a batched UI update if not already pending."""
        current_time = time.time()

        # Only schedule a new update if enough time has passed since the last one
        if not self._update_pending or (
            current_time - self._last_update_time > self._update_interval
        ):
            self._update_pending = True
            self._last_update_time = current_time
            # Use QTimer for thread-safe signaling to the UI
            QTimer.singleShot(int(self._update_interval * 1000), self._emit_update)

    def _emit_update(self):
        """Emit the signal for the batched update."""
        self._update_pending = False
        self._bridge.conversationChanged.emit()

    def add_message(self, message):
        """Add a message to the conversation history and schedule a UI update.

        Args:
            message: A message dict with timestamp and content keys
        """
        # Ensure the message has a type field, default to "Message" if not provided
        if "type" not in message:
            message["type"] = "Message"

        self._conversation.append(message)
        self._schedule_update()

    def clear(self):
        """Clear the conversation history."""
        self._conversation = []
        # Immediate update for clear operation (not batched)
        self._bridge.conversationChanged.emit()

    def get_messages(self):
        """Get the raw conversation messages list.

        Returns:
            The internal conversation list
        """
        return self._conversation

    def get_formatted_messages(self):
        """Format the conversation messages for display in the UI.

        Returns:
            A list of formatted message strings
        """
        formatted_messages = []
        for message in self._conversation:
            timestamp = message.get("timestamp", "")
            content = message.get("content", "")
            # Get message type, default to "Message" if not present
            msg_type = message.get("type", "Message")

            # Format message as expected by MessageItem: "[timestamp] sender: content::type"
            # If content starts with "You: ", it's a user message, otherwise it's an assistant message
            if content.startswith("You: "):
                formatted_messages.append(f"[{timestamp}] {content}::{msg_type}")
            else:
                formatted_messages.append(
                    f"[{timestamp}] Assistant: {content}::{msg_type}"
                )
        return formatted_messages

    def get_timestamp(self):
        """Get the current timestamp for a message.

        Returns:
            A formatted timestamp string
        """
        return datetime.now().strftime("%H:%M:%S")

    def reset_streaming_message(self):
        """Reset the current streaming message reference.

        This should be called whenever starting a fresh message stream.
        """
        self.current_streaming_message = None
        if self._update_pending:
            self._emit_update()  # Force update on stream completion
