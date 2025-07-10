from PyQt6.QtCore import QObject, QTimer, pyqtSignal, Qt
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQuick import QQuickWindow
from threading import Lock
import logging
import numpy as np
import time
import os
from ..display_config import config
from .bw_conversion import convert_to_bw

logger = logging.getLogger(__name__)


class EInkRenderer(QObject):
    """
    Class to handle rendering Qt content to an e-ink display.
    This class captures the screen content and signals when a new frame is ready.
    """

    frameReady = pyqtSignal(
        bytearray, int, int
    )  # Signal emitted when a new frame is ready: (data, width, height)

    def __init__(self, parent=None, capture_interval=1000, buffer_size=1):
        """
        Initialize the E-Ink renderer.

        Args:
            parent: Parent QObject
            capture_interval: Milliseconds between frame captures (default: 1000ms)
            buffer_size: Number of frames to buffer (default: 1 to reduce memory usage)
        """
        super().__init__(parent)
        self._capture_interval = capture_interval
        self._buffer_size = max(1, buffer_size)
        self._frame_buffer = []
        self._buffer_lock = Lock()
        self._capture_timer = QTimer(self)
        self._capture_timer.timeout.connect(self._capture_frame)
        self._rendering_active = False
        self._last_frame = None
        self._force_update = False
        self._error_count = 0

        # For frame comparison optimization
        self._sample_ratio = 0.1  # Sample 10% of pixels for quick comparison
        self._min_samples = 50  # Minimum number of samples to check
        self._max_samples = 500  # Maximum number of samples to check
        self._sample_indices = None

        # Activity tracking to dynamically adjust capture rate
        self._last_update_time = 0
        self._consecutive_unchanged_frames = 0
        self._max_interval = 3000  # Max interval: 3 seconds
        self._min_interval = 500  # Min interval: 0.5 seconds
        self._adaptive_capture = True

        # Debouncing mechanism to prevent rapid successive updates
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._debounced_capture)
        self._debounce_delay = 300  # 300ms debounce delay
        self._pending_capture = False
        self._text_streaming_mode = False  # Track if we're in text streaming mode
        self._last_text_update = 0

        # Debug capture settings
        self._save_capture = config["display"].get("eink_save_capture", False)
        self._capture_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "debug_capture.png",
        )

    def start(self):
        """Start the screen capture process"""
        if not self._rendering_active:
            logger.info(
                f"Starting e-ink renderer with interval {self._capture_interval}ms"
            )
            self._rendering_active = True
            self._last_update_time = time.time()
            self._capture_timer.start(self._capture_interval)

    def stop(self):
        """Stop the screen capture process"""
        if self._rendering_active:
            logger.info("Stopping e-ink renderer")
            self._capture_timer.stop()
            self._debounce_timer.stop()  # Stop debounce timer as well
            self._rendering_active = False
            self._pending_capture = False  # Reset pending capture flag
            with self._buffer_lock:
                self._frame_buffer.clear()

    def set_capture_interval(self, interval_ms):
        """Set the capture interval in milliseconds"""
        self._capture_interval = max(50, interval_ms)  # Don't allow less than 50ms
        if self._rendering_active:
            self._capture_timer.setInterval(self._capture_interval)
            logger.info(
                f"E-ink renderer interval changed to {self._capture_interval}ms"
            )

    def set_adaptive_capture(self, enabled):
        """Enable or disable adaptive capture rate"""
        self._adaptive_capture = enabled

    def force_update(self):
        """Force an update on the next capture, even if the screen hasn't changed"""
        self._force_update = True
        # Trigger a capture immediately
        QTimer.singleShot(0, self._capture_frame)

    def force_render_update(self):
        """Forces an immediate capture and render cycle, bypassing the timer."""
        if not self._rendering_active:
            logger.warning("Renderer not active, cannot force update.")
            return
        logger.debug("Forcing immediate render update...")
        # Set the force_update flag to ensure the frame difference check is skipped
        self._force_update = True 
        # Use QTimer.singleShot to queue the capture on the event loop immediately
        QTimer.singleShot(0, self._capture_frame)

    def set_text_streaming_mode(self, enabled):
        """Enable or disable text streaming mode for better batching during responses"""
        self._text_streaming_mode = enabled
        if enabled:
            self._last_text_update = time.time()
            logger.debug("Text streaming mode enabled")
        else:
            logger.debug("Text streaming mode disabled")
            # Force an immediate update when streaming ends
            self.force_render_update()

    def request_update(self):
        """Request an update with debouncing to prevent rapid successive updates"""
        if not self._rendering_active:
            return
            
        current_time = time.time()
        
        # In text streaming mode, use longer debounce delay
        if self._text_streaming_mode:
            self._last_text_update = current_time
            debounce_delay = 800  # 800ms debounce for text streaming
        else:
            debounce_delay = self._debounce_delay
            
        # If debounce timer is already running, just mark that we need a capture
        if self._debounce_timer.isActive():
            self._pending_capture = True
            return
            
        # Start the debounce timer
        self._pending_capture = True
        self._debounce_timer.start(debounce_delay)

    def _debounced_capture(self):
        """Perform the actual capture after debounce delay"""
        if self._pending_capture:
            self._pending_capture = False
            self._capture_frame()

    def _capture_frame(self):
        """Capture the current screen content"""
        error_count = getattr(self, "_error_count", 0)
        
        # Skip capture if we're in debounce mode and this is a regular timer capture
        if self._debounce_timer.isActive() and not self._force_update:
            return

        try:
            # Get the application instance
            app = QApplication.instance()
            if not app:
                logger.error("No QApplication instance available")
                return

            # Get the top-level windows - should work even in offscreen mode
            windows = QApplication.topLevelWindows()
            if not windows:
                logger.error("No top-level windows found")
                return

            main_window = windows[0]
            # logger.debug(f"Window: {main_window.objectName() or 'unnamed'}, Size: {main_window.width()}x{main_window.height()}")

            # Get the window size
            width = main_window.width()
            height = main_window.height()

            # Try different approaches to capture the actual window content
            image = None

            # Approach 1: For QQuickWindow (QML content)
            if isinstance(main_window, QQuickWindow):
                try:
                    # logger.debug("Trying QQuickWindow grabbing approach")
                    # This method is available in PyQt6 and should work in offscreen mode
                    image = main_window.grabWindow()
                    # logger.debug("Successfully captured QQuickWindow content")
                except Exception as e1:
                    logger.warning(f"QQuickWindow grabbing failed: {e1}")

            # Approach 2: Use QPixmap.grabWidget() if available
            if image is None:
                try:
                    logger.debug("Trying QPixmap.grabWidget approach")
                    pixmap = QPixmap(width, height)
                    pixmap.fill(Qt.GlobalColor.white)  # Start with a white background

                    # Try different APIs based on what's available
                    if hasattr(pixmap, "grabWidget"):
                        # Older PyQt versions
                        pixmap = pixmap.grabWidget(main_window.winId())
                    elif hasattr(QPixmap, "grabWindow"):
                        # Try direct static method
                        pixmap = QPixmap.grabWindow(main_window.winId())

                    image = pixmap.toImage()
                    logger.debug("Successfully captured widget content")
                except Exception as e2:
                    logger.warning(f"Widget grabbing failed: {e2}")

            # Approach 3: Last resort - create a blank image with a border
            if image is None:
                logger.warning(
                    "Could not capture actual UI content, falling back to test pattern"
                )
                image = QImage(width, height, QImage.Format.Format_ARGB32)
                image.fill(Qt.GlobalColor.white)  # Fill with white background

                # Draw a simple border to at least show something
                for x in range(width):
                    for y in range(height):
                        # Draw a border
                        if x < 2 or x >= width - 2 or y < 2 or y >= height - 2:
                            image.setPixelColor(x, y, Qt.GlobalColor.black)

                # Draw text to indicate this is a fallback
                # Draw "OFFSCREEN MODE" text (simplified)
                text_y = height // 2 - 5
                text_x = width // 2 - 40
                # Just draw a line for simplicity
                for x in range(text_x, text_x + 80):
                    image.setPixelColor(x, text_y, Qt.GlobalColor.black)
                    image.setPixelColor(x, text_y + 10, Qt.GlobalColor.black)

            # Save the capture if enabled
            if self._save_capture and image:
                try:
                    image.save(self._capture_path)
                    logger.debug(f"Saved screen capture to {self._capture_path}")
                except Exception as e:
                    logger.warning(f"Failed to save screen capture: {e}")

            # Convert to e-ink compatible format (assuming 1-bit black and white)
            eink_data = self._convert_to_eink_format(image)

            # Check if frame is different from previous - use sparse sampling for efficiency
            if self._force_update or self._is_frame_different(eink_data, width, height):
                current_time = time.time()
                logger.debug(
                    f"New frame captured: {len(eink_data)} bytes, {current_time - self._last_update_time:.2f}s since last update"
                )
                self._add_to_buffer(eink_data, width, height)
                self._last_frame = eink_data
                self._last_update_time = current_time
                self._force_update = False
                self._consecutive_unchanged_frames = 0

                # Reset the capture interval to minimum after a change is detected
                if (
                    self._adaptive_capture
                    and self._capture_timer.interval() > self._min_interval
                ):
                    self._capture_timer.setInterval(self._min_interval)
                    logger.debug(
                        f"Content changed, setting capture interval to {self._min_interval}ms"
                    )
            else:
                # Frame didn't change - possibly slow down capture rate if configured
                self._consecutive_unchanged_frames += 1

                # Adapt capture rate based on inactivity
                if self._adaptive_capture and self._consecutive_unchanged_frames > 5:
                    current_interval = self._capture_timer.interval()
                    # Increase interval gradually up to max_interval
                    new_interval = min(
                        self._max_interval,
                        current_interval + min(500, current_interval // 2),
                    )

                    if new_interval > current_interval:
                        logger.debug(
                            f"No changes detected for {self._consecutive_unchanged_frames} frames, "
                            + f"increasing capture interval: {current_interval}ms -> {new_interval}ms"
                        )
                        self._capture_timer.setInterval(new_interval)

            # Reset error count on success
            self._error_count = 0

        except Exception as e:
            # Increment error count and log
            self._error_count = error_count + 1
            logger.error(f"Error capturing frame: {e}", exc_info=True)

            # If we've had too many errors in a row, slow down the capture rate
            if self._error_count > 5:
                old_interval = self._capture_timer.interval()
                new_interval = min(
                    2000, old_interval * 2
                )  # Double interval up to 2 seconds max

                if old_interval != new_interval:
                    logger.warning(
                        f"Too many errors, reducing capture rate: {old_interval}ms -> {new_interval}ms"
                    )
                    self._capture_timer.setInterval(new_interval)

                # After 20 consecutive errors, stop the renderer to prevent resource drain
                if self._error_count > 20:
                    logger.error("Too many consecutive errors, stopping E-Ink renderer")
                    self.stop()

    def _convert_to_eink_format(self, image):
        """
        Convert QImage to e-ink compatible format.
        Simple, direct conversion from RGB/ARGB to 1-bit black and white.

        Args:
            image: QImage to convert

        Returns:
            bytearray of 1-bit data (8 pixels per byte)
        """
        # First, ensure we have a grayscale image
        if image.format() != QImage.Format.Format_Grayscale8:
            image = image.convertToFormat(QImage.Format.Format_Grayscale8)

        width, height = image.width(), image.height()
        bytes_per_row = (width + 7) // 8
        total_bytes = bytes_per_row * height

        # Extract grayscale data
        ptr = image.bits()
        ptr.setsize(height * image.bytesPerLine())
        pixels = np.frombuffer(ptr, dtype=np.uint8).reshape(
            height, image.bytesPerLine()
        )[:, :width]

        # Horizontal mirroring
        pixels_mirrored = pixels[:, ::-1].copy()

        # Apply dithering if enabled
        if config["display"]["eink_dithering_enabled"]:
            logger.debug("Applying Floyd-Steinberg dithering")
            pixels_dithered = self._apply_dithering(
                pixels_mirrored.flatten(),
                width,
                height,
                config["display"].get("eink_threshold", 128),
            )
            pixels_dithered = np.array(pixels_dithered, dtype=np.uint8).reshape(
                height, width
            )
        else:
            pixels_dithered = pixels_mirrored

        # Convert to 1-bit using the selected method
        logger.debug("Applying BW conversion")
        binary = convert_to_bw(pixels_dithered, config["display"])

        # Pack the binary image into a bytearray (8 pixels per byte)
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

    def _apply_dithering(self, image_data, width, height, threshold=128):
        """
        Apply Floyd-Steinberg dithering to the image data.

        Args:
            image_data: 1D array of grayscale pixel values
            width: Image width
            height: Image height
            threshold: Threshold for black/white conversion (0-255)

        Returns:
            1D array of dithered pixel values
        """
        # If the BW conversion config specifies gamma correction, apply it before dithering
        bw_config = config["display"].get("eink_bw_conversion", {})
        use_gamma = bw_config.get("use_gamma", False)
        gamma_value = bw_config.get("gamma_value", 0.7)

        # Convert 1D array to 2D for easier processing
        pixels = np.array(image_data, dtype=np.float32).reshape(height, width)

        # Apply gamma correction if enabled
        if use_gamma:
            from .bw_conversion import apply_gamma_correction

            pixels = apply_gamma_correction(pixels, gamma_value)

        # Make a copy to avoid modifying the original
        dithered = pixels.copy()

        # Process in chunks to reduce memory usage
        chunk_size = min(32, height)  # Process 32 rows at a time

        for chunk_start in range(0, height - 1, chunk_size):
            chunk_end = min(chunk_start + chunk_size, height - 1)

            # Apply Floyd-Steinberg dithering to this chunk
            for y in range(chunk_start, chunk_end):
                for x in range(1, width - 1):
                    old_pixel = dithered[y, x]
                    # Find nearest color using threshold
                    new_pixel = 0 if old_pixel < threshold else 255
                    dithered[y, x] = new_pixel

                    # Compute quantization error
                    quant_error = old_pixel - new_pixel

                    # Distribute error to neighboring pixels
                    dithered[y, x + 1] += quant_error * 7 / 16
                    dithered[y + 1, x - 1] += quant_error * 3 / 16
                    dithered[y + 1, x] += quant_error * 5 / 16
                    dithered[y + 1, x + 1] += quant_error * 1 / 16

        # Handle last row special case (no pixels below to distribute error to)
        for x in range(1, width - 1):
            old_pixel = dithered[height - 1, x]
            new_pixel = 0 if old_pixel < threshold else 255
            dithered[height - 1, x] = new_pixel

            # Can only distribute error horizontally
            quant_error = old_pixel - new_pixel
            dithered[height - 1, x + 1] += quant_error * 7 / 16

        # Clip values to 0-255 range to account for possible overflow
        dithered = np.clip(dithered, 0, 255).astype(np.uint8)

        # Convert back to 1D array
        return dithered.flatten().tolist()

    def _is_frame_different(self, new_frame, width, height):
        """
        Check if the new frame is different from the last one using sparse sampling.

        Args:
            new_frame: The new frame data
            width: Frame width
            height: Frame height

        Returns:
            True if frames are different, False otherwise
        """
        if self._last_frame is None:
            return True

        if len(new_frame) != len(self._last_frame):
            return True

        # Sparse sampling for efficient comparison
        bytes_per_row = (width + 7) // 8
        total_bytes = len(new_frame)

        # First time: Generate sample indices if not already done
        if self._sample_indices is None:
            # Calculate number of samples (10% of total, with min/max limits)
            num_samples = max(
                self._min_samples,
                min(self._max_samples, int(total_bytes * self._sample_ratio)),
            )

            # Create random indices covering the whole frame
            np.random.seed(42)  # Use fixed seed for reproducibility
            self._sample_indices = np.random.choice(
                total_bytes, num_samples, replace=False
            )
            logger.debug(f"Created {num_samples} sample points for frame comparison")

        # Compare only the bytes at sample positions
        for idx in self._sample_indices:
            if idx < total_bytes and new_frame[idx] != self._last_frame[idx]:
                return True

        # If we need more accuracy, we can add a second check that looks at regions
        # where we expect changes (like the center of the screen)

        # Check center region of the screen (where content changes are most likely)
        center_y_start = height // 4
        center_y_end = (height * 3) // 4
        center_x_start = width // 4
        center_x_end = (width * 3) // 4

        # Convert to byte positions
        center_x_byte_start = center_x_start // 8
        center_x_byte_end = (center_x_end + 7) // 8

        # Check a subset of bytes in the center region
        sample_step = max(
            1, (center_y_end - center_y_start) // 10
        )  # Check ~10 rows in center

        for y in range(center_y_start, center_y_end, sample_step):
            row_start = y * bytes_per_row + center_x_byte_start
            row_end = y * bytes_per_row + center_x_byte_end

            # Skip if out of bounds
            if row_end >= total_bytes:
                continue

            # Check bytes in this center row with a step
            for i in range(row_start, row_end, max(1, (row_end - row_start) // 5)):
                if new_frame[i] != self._last_frame[i]:
                    return True

        # If we reach here, frames are considered identical
        return False

    def _add_to_buffer(self, frame_data, width, height):
        """
        Add a frame to the buffer and emit signal.
        Uses direct buffer management to reduce memory usage.

        Args:
            frame_data: The frame data
            width: Frame width
            height: Frame height
        """
        with self._buffer_lock:
            # Clear previous frames to save memory if not needed
            if len(self._frame_buffer) >= self._buffer_size:
                self._frame_buffer.clear()

            # Add new frame
            self._frame_buffer.append((frame_data, width, height))

            # Keep buffer at desired size
            while len(self._frame_buffer) > self._buffer_size:
                self._frame_buffer.pop(0)

            # Emit the frame ready signal with the newest frame
            newest_frame = self._frame_buffer[-1]
            self.frameReady.emit(newest_frame[0], newest_frame[1], newest_frame[2])
