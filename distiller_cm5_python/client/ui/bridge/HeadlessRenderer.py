from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QOffscreenSurface, QOpenGLContext
from PyQt6.QtQuick import QQuickWindow, QQuickRenderTarget
from PyQt6.QtWidgets import QApplication
import hashlib
import logging
import time
from threading import Lock
from typing import Optional
import numpy as np
from ..display_config import config

logger = logging.getLogger(__name__)


class HeadlessRenderer(QObject):
    """
    Qt 6 headless renderer using QQuickRenderTarget.
    """

    frameReady = pyqtSignal(
        bytearray, int, int
    )  # Signal emitted when a new frame is ready: (data, width, height)

    def __init__(self, parent=None, capture_interval=1000):
        """
        Initialize the headless renderer.

        Args:
            parent: Parent QObject
            capture_interval: Milliseconds between frame captures (default: 1000ms)
        """
        super().__init__(parent)
        self._capture_interval = capture_interval
        self._capture_timer = QTimer(self)
        self._capture_timer.timeout.connect(self._capture_frame)
        self._rendering_active = False

        # Frame tracking for efficient diffing
        self._last_frame_hash = None
        self._force_update = False

        # Offscreen rendering setup
        self._offscreen_surface: Optional[QOffscreenSurface] = None
        self._context: Optional[QOpenGLContext] = None
        self._target_window: Optional[QQuickWindow] = None
        self._render_lock = Lock()

        # Configuration
        self._width = config["display"]["width"]
        self._height = config["display"]["height"]

        # Performance tracking
        self._last_update_time = 0
        self._consecutive_unchanged_frames = 0
        self._adaptive_capture = config["display"].get("eink_adaptive_capture", True)
        self._min_interval = 500
        self._max_interval = 3000

        logger.info(f"HeadlessRenderer initialized for {self._width}x{self._height} display")

    def set_target_window(self, window):
        """Set the QML window to render from."""
        self._target_window = window
        if window:
            self._setup_offscreen_rendering()

    def _setup_offscreen_rendering(self):
        """Set up proper offscreen rendering context."""
        try:
            # Create offscreen surface
            self._offscreen_surface = QOffscreenSurface()

            # Set the format to match what we need
            format = self._offscreen_surface.requestedFormat()
            format.setMajorVersion(3)
            format.setMinorVersion(3)
            self._offscreen_surface.setFormat(format)

            # Create the surface
            if not self._offscreen_surface.create():
                logger.error("Failed to create offscreen surface")
                return False

            # Create OpenGL context
            self._context = QOpenGLContext()
            self._context.setFormat(format)

            if not self._context.create():
                logger.error("Failed to create OpenGL context")
                return False

            logger.info("Offscreen rendering context created successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to setup offscreen rendering: {e}")
            return False

    def start(self):
        """Start the screen capture process."""
        if not self._rendering_active:
            logger.info(f"Starting headless renderer with interval {self._capture_interval}ms")
            self._rendering_active = True
            self._last_update_time = time.time()
            # Start timer even if offscreen surface creation failed - fallback methods will handle
            self._capture_timer.start(self._capture_interval)

    def stop(self):
        """Stop the screen capture process."""
        if self._rendering_active:
            logger.info("Stopping headless renderer")
            self._capture_timer.stop()
            self._rendering_active = False

    def set_capture_interval(self, interval_ms):
        """Set the capture interval in milliseconds."""
        self._capture_interval = max(50, interval_ms)
        if self._rendering_active:
            self._capture_timer.setInterval(self._capture_interval)
            logger.info(f"Capture interval changed to {self._capture_interval}ms")

    def set_adaptive_capture(self, enabled):
        """Enable or disable adaptive capture rate."""
        self._adaptive_capture = enabled
        logger.info(f"Adaptive capture {'enabled' if enabled else 'disabled'}")

    def force_update(self):
        """Force an update on the next capture."""
        self._force_update = True
        QTimer.singleShot(0, self._capture_frame)

    def _capture_frame(self):
        """Capture the current QML content using modern Qt 6 methods."""
        if not self._target_window:
            logger.warning("No target window set for rendering")
            return

        try:
            with self._render_lock:
                # Method 1: Try QQuickRenderTarget approach (Qt 6.2+)
                image = self._render_with_target()

                # Method 2: Fallback to grabWindow if available
                if image is None:
                    image = self._render_with_grab()

                # Method 3: Create test pattern if all else fails
                if image is None:
                    logger.debug("All rendering methods failed, using test pattern")
                    image = self._create_test_pattern()

                if image is None:
                    logger.error("Failed to capture frame with all methods")
                    return

                # Convert to E-Ink compatible format
                eink_data = self._convert_to_eink_format(image)

                # Check if frame is different using hash comparison
                if self._force_update or self._is_frame_different(eink_data):
                    current_time = time.time()
                    logger.debug(
                        f"New frame captured: {len(eink_data)} bytes, "
                        f"{current_time - self._last_update_time:.2f}s since last update"
                    )

                    # Emit the frame ready signal
                    self.frameReady.emit(eink_data, self._width, self._height)

                    self._last_update_time = current_time
                    self._force_update = False
                    self._consecutive_unchanged_frames = 0

                    # Reset interval for adaptive capture
                    if (
                        self._adaptive_capture
                        and self._capture_timer.interval() > self._min_interval
                    ):
                        self._capture_timer.setInterval(self._min_interval)

                else:
                    # Handle unchanged frames
                    self._consecutive_unchanged_frames += 1

                    # Adaptive interval increase
                    if self._adaptive_capture and self._consecutive_unchanged_frames > 5:
                        current_interval = self._capture_timer.interval()
                        new_interval = min(
                            self._max_interval,
                            current_interval + min(500, current_interval // 2),
                        )

                        if new_interval > current_interval:
                            logger.debug(
                                f"No changes for {self._consecutive_unchanged_frames} frames, "
                                f"increasing interval: {current_interval}ms -> {new_interval}ms"
                            )
                            self._capture_timer.setInterval(new_interval)

        except Exception as e:
            logger.error(f"Error capturing frame: {e}", exc_info=True)

    def _render_with_target(self):
        """Try rendering using QQuickRenderTarget (Qt 6.2+)."""
        try:
            # Check if QQuickRenderTarget.fromImage is available (Qt 6.2+)
            if not hasattr(QQuickRenderTarget, "fromImage"):
                logger.debug("QQuickRenderTarget.fromImage not available (requires Qt 6.2+)")
                return None

            # Check if target window exists and has required methods
            if not self._target_window:
                logger.debug("No target window available")
                return None

            if not hasattr(self._target_window, "setRenderTarget") or not hasattr(
                self._target_window, "renderTarget"
            ):
                logger.debug("Target window does not support render target methods")
                return None

            # Create target image
            target_image = QImage(self._width, self._height, QImage.Format.Format_ARGB32)
            target_image.fill(0xFFFFFFFF)  # White background

            # Create render target - use getattr to safely access Qt 6.2+ API
            fromImage = getattr(QQuickRenderTarget, "fromImage", None)
            if not fromImage:
                logger.debug("QQuickRenderTarget.fromImage not available")
                return None

            render_target = fromImage(target_image)

            # Set render target on window
            old_target = self._target_window.renderTarget()
            self._target_window.setRenderTarget(render_target)

            # Force a render
            QApplication.processEvents()

            # Restore original render target
            self._target_window.setRenderTarget(old_target)

            logger.debug("Successfully rendered using QQuickRenderTarget")
            return target_image

        except Exception as e:
            logger.debug(f"QQuickRenderTarget method failed: {e}")
            return None

    def _render_with_grab(self):
        """Fallback: try multiple grab methods."""
        try:
            if not self._target_window:
                logger.debug("No target window available for grab methods")
                return None

            # Method 1: Try grabWindow
            if hasattr(self._target_window, "grabWindow"):
                try:
                    image = self._target_window.grabWindow()
                    if image and not image.isNull():
                        logger.debug("Successfully rendered using grabWindow")
                        return image
                except Exception as e:
                    logger.debug(f"grabWindow failed: {e}")

            # Method 2: Try QQuickWindow's own grab method for headless
            if hasattr(self._target_window, "contentItem"):
                try:
                    content_item = self._target_window.contentItem()
                    if content_item:
                        # Force process any pending events
                        QApplication.processEvents()

                        # Try direct QQuickItem grab
                        if hasattr(content_item, "grabToImage"):
                            grab_result = content_item.grabToImage()
                            # grabToImage is async, but in offscreen mode it should be immediate
                            if grab_result:
                                QApplication.processEvents()  # Process the grab
                                image = grab_result.image()
                                if image and not image.isNull():
                                    logger.debug(
                                        "Successfully rendered using contentItem.grabToImage"
                                    )
                                    return image
                except Exception as e:
                    logger.debug(f"contentItem.grabToImage failed: {e}")

            # Method 3: Try manual rendering for offscreen platform
            try:
                if hasattr(self._target_window, "contentItem"):
                    content_item = self._target_window.contentItem()
                    if content_item:
                        # Create image directly
                        image = QImage(self._width, self._height, QImage.Format.Format_ARGB32)
                        image.fill(0xFFFFFFFF)  # White background

                        # Basic rendering attempt
                        from PyQt6.QtGui import QPainter

                        painter = QPainter(image)
                        # This likely won't work in offscreen mode, but worth trying
                        if hasattr(content_item, "render"):
                            content_item.render(painter)
                            painter.end()
                            logger.debug("Successfully rendered using manual QPainter method")
                            return image
                        painter.end()

            except Exception as e:
                logger.debug(f"Manual rendering failed: {e}")

            logger.debug("All grab methods failed")

        except Exception as e:
            logger.debug(f"Grab methods failed: {e}")

        return None

    def _create_test_pattern(self):
        """Create a test pattern when rendering fails."""
        logger.warning("Creating test pattern - actual rendering failed")

        image = QImage(self._width, self._height, QImage.Format.Format_ARGB32)
        image.fill(0xFFFFFFFF)  # White background

        # Draw simple border and text indicator
        for x in range(self._width):
            for y in range(self._height):
                if x < 2 or x >= self._width - 2 or y < 2 or y >= self._height - 2:
                    image.setPixel(x, y, 0xFF000000)  # Black border

        # Draw "HEADLESS MODE" indicator
        text_y = self._height // 2 - 5
        text_x = self._width // 2 - 40
        for x in range(text_x, min(text_x + 80, self._width)):
            if text_y < self._height:
                image.setPixel(x, text_y, 0xFF000000)
            if text_y + 10 < self._height:
                image.setPixel(x, text_y + 10, 0xFF000000)

        return image

    def _convert_to_eink_format(self, image):
        """
        Convert QImage to E-Ink compatible 1-bit format.
        """
        # Convert to grayscale
        if image.format() != QImage.Format.Format_Grayscale8:
            image = image.convertToFormat(QImage.Format.Format_Grayscale8)

        width, height = image.width(), image.height()
        bytes_per_row = (width + 7) // 8
        total_bytes = bytes_per_row * height

        # Extract grayscale data
        ptr = image.bits()
        ptr.setsize(height * image.bytesPerLine())
        pixels = np.frombuffer(ptr, dtype=np.uint8).reshape(height, image.bytesPerLine())[:, :width]

        # Horizontal flip
        pixels = np.fliplr(pixels)

        # Apply gamma correction for better E-Ink contrast
        gamma_value = config["display"]["eink_bw_conversion"].get("gamma_value", 0.8)
        pixels = ((pixels / 255.0) ** gamma_value * 255).astype(np.uint8)

        # Simple threshold conversion
        threshold = config["display"].get("eink_threshold", 128)
        binary = pixels > threshold

        # Pack into 1-bit format (8 pixels per byte)
        output = np.zeros(total_bytes, dtype=np.uint8)

        for y in range(height):
            for x_byte in range(bytes_per_row):
                byte_val = 0
                for bit in range(8):
                    x = x_byte * 8 + bit
                    if x < width and binary[y, x]:
                        byte_val |= 1 << (7 - bit)
                output[y * bytes_per_row + x_byte] = byte_val

        return bytearray(output)

    def _is_frame_different(self, frame_data):
        """
        Efficient frame comparison using SHA256 hash.
        Much faster than pixel-by-pixel comparison.
        """
        # Calculate hash of frame data
        frame_hash = hashlib.sha256(frame_data).hexdigest()

        if frame_hash != self._last_frame_hash:
            self._last_frame_hash = frame_hash
            return True

        return False

    def cleanup(self):
        """Clean up resources."""
        self.stop()

        if self._context:
            self._context = None

        if self._offscreen_surface:
            self._offscreen_surface = None

        logger.info("HeadlessRenderer cleaned up")
