from PyQt6.QtCore import QObject
from .HeadlessRenderer import HeadlessRenderer
from .EInkRendererBridge import EInkRendererBridge
from ..display_config import config
from typing import Optional
import logging
import asyncio

logger = logging.getLogger(__name__)


class EInkRenderer(QObject):
    """
    E-Ink Renderer for displaying content on E-Ink screens.
    Optimized to work with headless Qt 6 rendering and 1-bit conversion.
    """

    def __init__(self, parent=None):
        """Initialize the E-Ink renderer."""
        super().__init__(parent)

        # Get configuration
        self._capture_interval = config["display"]["eink_refresh_interval"]
        self._adaptive_capture = config["display"]["eink_adaptive_capture"]
        self._timer_based_mode = config["display"].get("eink_timer_based_mode", False)

        # Initialize headless renderer for screen capture
        self._headless_renderer: HeadlessRenderer = HeadlessRenderer(
            parent=self, capture_interval=self._capture_interval
        )
        self._headless_renderer.set_adaptive_capture(self._adaptive_capture)

        # Initialize E-Ink bridge for hardware communication
        self._eink_bridge: EInkRendererBridge = EInkRendererBridge(parent=self)

        # Connect the renderer to the bridge
        self._headless_renderer.frameReady.connect(self._handle_frame)

        # Connect display completion signal for event-driven mode
        self._eink_bridge.displayComplete.connect(self._on_display_complete)

        self._initialized = False
        self._rendering_active = False
        self._event_driven_capture_pending = False

        logger.info(
            f"EInkRenderer initialized (mode: {'timer-based' if self._timer_based_mode else 'event-driven'})"
        )

    def initialize(self):
        """Initialize the E-Ink hardware."""
        try:
            # Initialize the hardware bridge
            if not self._eink_bridge.initialize():
                logger.error("Failed to initialize E-Ink bridge")
                return False

            # Configure optimal settings for UI content
            self._eink_bridge.set_dithering(
                False, 1
            )  # Disable dithering, we use Floyd-Steinberg in conversion

            self._initialized = True
            logger.info("EInkRenderer hardware initialized")
            return True

        except Exception as e:
            logger.error(f"Error initializing EInkRenderer: {e}")
            return False

    def set_target_window(self, window):
        """Set the QML window to render."""
        self._headless_renderer.set_target_window(window)

    def start(self):
        """Start rendering and displaying frames."""
        if not self._initialized:
            logger.warning("Cannot start - not initialized")
            return False

        if not self._rendering_active:
            self._rendering_active = True

            if self._timer_based_mode:
                # Timer-based mode: use the existing timer mechanism
                self._headless_renderer.start()
                logger.info("EInkRenderer started in timer-based mode")
            else:
                # Event-driven mode: capture first frame after a short delay
                logger.info("EInkRenderer started in event-driven mode")
                # Use QTimer to capture first frame after event loop is ready
                from PyQt6.QtCore import QTimer

                QTimer.singleShot(100, self._capture_next_frame)

            return True

        return True

    def stop(self):
        """Stop rendering and displaying frames."""
        if self._rendering_active:
            self._headless_renderer.stop()
            self._rendering_active = False
            logger.info("EInkRenderer stopped")

    def force_update(self):
        """Force an immediate frame update."""
        if self._headless_renderer:
            self._headless_renderer.force_update()

    def set_capture_interval(self, interval_ms):
        """Set the capture interval."""
        if self._headless_renderer:
            self._headless_renderer.set_capture_interval(interval_ms)

    def set_text_streaming_mode(self, enabled):
        """Enable/disable text streaming mode for better batching."""
        logger.debug(f"Text streaming mode: {'enabled' if enabled else 'disabled'}")
        
        # In event-driven mode, we might need to trigger updates during streaming
        if not self._timer_based_mode and enabled:
            # Start a timer to periodically check for updates during streaming
            if not hasattr(self, '_streaming_timer'):
                from PyQt6.QtCore import QTimer
                self._streaming_timer = QTimer()
                self._streaming_timer.timeout.connect(self._streaming_update_check)
            self._streaming_timer.start(2000)  # Check every 2 seconds
        elif hasattr(self, '_streaming_timer'):
            self._streaming_timer.stop()
            
    def _streaming_update_check(self):
        """Periodic check during text streaming to ensure display updates."""
        if self._rendering_active and not self._timer_based_mode:
            logger.debug("Streaming update check - requesting frame")
            self.force_update()

    def request_update(self):
        """Request a frame update."""
        if self._headless_renderer:
            self._headless_renderer.force_update()

    def _handle_frame(self, frame_data, width, height):
        """Handle a new frame from the headless renderer."""
        logger.info(
            f"Frame received: {width}x{height}, {len(frame_data)} bytes, event_driven_mode={not self._timer_based_mode}"
        )

        # Forward to E-Ink bridge for display
        if self._eink_bridge and self._eink_bridge.initialized:
            try:
                # For event-driven mode, we need to ensure the display isn't busy
                if (
                    not self._timer_based_mode
                    and hasattr(self._eink_bridge, "eink_driver")
                    and self._eink_bridge.eink_driver
                ):
                    if self._eink_bridge.eink_driver.is_busy():
                        logger.warning("Display is busy, skipping frame")
                        return

                # Call handle_frame directly - it has its own synchronization
                self._eink_bridge.handle_frame(frame_data, width, height)
            except Exception as e:
                logger.error(f"Error forwarding frame to E-Ink bridge: {e}")
        else:
            logger.warning("E-Ink bridge not available or initialized")

    def cleanup(self):
        """Clean up all resources."""
        self.stop()

        if hasattr(self, "_headless_renderer") and self._headless_renderer:
            self._headless_renderer.cleanup()
            self._headless_renderer = None  # type: ignore

        if hasattr(self, "_eink_bridge") and self._eink_bridge:
            self._eink_bridge.cleanup()
            self._eink_bridge = None  # type: ignore

        self._initialized = False
        logger.info("EInkRenderer cleaned up")

    def _capture_next_frame(self):
        """Capture the next frame in event-driven mode."""
        if not self._rendering_active or self._timer_based_mode:
            return

        # Mark that we're waiting for a capture
        self._event_driven_capture_pending = True

        logger.debug("Requesting frame capture in event-driven mode")

        # Request a single frame capture from the headless renderer
        if self._headless_renderer:
            self._headless_renderer.force_update()
        else:
            logger.error("No headless renderer available for capture")

    def _on_display_complete(self):
        """Called when the e-ink display completes a refresh."""
        logger.info(f"Display complete callback triggered (timer_based={self._timer_based_mode}, active={self._rendering_active})")
        if not self._timer_based_mode and self._rendering_active:
            # In event-driven mode, capture the next frame
            logger.info("Display complete, capturing next frame")
            self._capture_next_frame()
        else:
            logger.debug(f"Not capturing next frame: timer_based={self._timer_based_mode}, active={self._rendering_active}")
