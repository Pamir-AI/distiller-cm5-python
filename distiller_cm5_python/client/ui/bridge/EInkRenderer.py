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

        # Initialize headless renderer for screen capture
        self._headless_renderer: HeadlessRenderer = HeadlessRenderer(
            parent=self, capture_interval=self._capture_interval
        )
        self._headless_renderer.set_adaptive_capture(self._adaptive_capture)

        # Initialize E-Ink bridge for hardware communication
        self._eink_bridge: EInkRendererBridge = EInkRendererBridge(parent=self)

        # Connect the renderer to the bridge
        self._headless_renderer.frameReady.connect(self._handle_frame)

        self._initialized = False
        self._rendering_active = False

        logger.info("EInkRenderer initialized")

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
            self._headless_renderer.start()
            self._rendering_active = True
            logger.info("EInkRenderer started")
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
        # This functionality can be implemented in HeadlessRenderer if needed
        logger.debug(f"Text streaming mode: {'enabled' if enabled else 'disabled'}")

    def request_update(self):
        """Request a frame update."""
        if self._headless_renderer:
            self._headless_renderer.force_update()

    def _handle_frame(self, frame_data, width, height):
        """Handle a new frame from the headless renderer."""
        logger.debug(f"Processing frame: {width}x{height}, {len(frame_data)} bytes")

        # Forward to E-Ink bridge for display
        if self._eink_bridge and self._eink_bridge.initialized:
            try:
                # Use asyncio.to_thread for non-blocking operation
                asyncio.create_task(
                    asyncio.to_thread(
                        self._eink_bridge.handle_frame, frame_data, width, height
                    )
                )
            except Exception as e:
                logger.error(f"Error forwarding frame to E-Ink bridge: {e}")
        else:
            logger.warning("E-Ink bridge not available or initialized")

    def cleanup(self):
        """Clean up all resources."""
        self.stop()

        if hasattr(self, '_headless_renderer') and self._headless_renderer:
            self._headless_renderer.cleanup()
            self._headless_renderer = None  # type: ignore

        if hasattr(self, '_eink_bridge') and self._eink_bridge:
            self._eink_bridge.cleanup()
            self._eink_bridge = None  # type: ignore

        self._initialized = False
        logger.info("EInkRenderer cleaned up")
