from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QRect, Qt, QSize, QPoint
from PyQt6.QtGui import QPixmap, QScreen, QImage, QPainter, QTransform
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQuick import QQuickWindow
from threading import Lock
import logging
import numpy as np
from .Eink_Driver import config

logger = logging.getLogger(__name__)

class EInkRenderer(QObject):
    """
    Class to handle rendering Qt content to an e-ink display.
    This class captures the screen content and signals when a new frame is ready.
    """
    frameReady = pyqtSignal(bytearray, int, int)  # Signal emitted when a new frame is ready: (data, width, height)
    
    def __init__(self, parent=None, capture_interval=500, buffer_size=2):
        """
        Initialize the E-Ink renderer.
        
        Args:
            parent: Parent QObject
            capture_interval: Milliseconds between frame captures
            buffer_size: Number of frames to buffer
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
        
    def start(self):
        """Start the screen capture process"""
        if not self._rendering_active:
            logger.info(f"Starting e-ink renderer with interval {self._capture_interval}ms")
            self._rendering_active = True
            self._capture_timer.start(self._capture_interval)
            
    def stop(self):
        """Stop the screen capture process"""
        if self._rendering_active:
            logger.info("Stopping e-ink renderer")
            self._capture_timer.stop()
            self._rendering_active = False
            with self._buffer_lock:
                self._frame_buffer.clear()
    
    def set_capture_interval(self, interval_ms):
        """Set the capture interval in milliseconds"""
        self._capture_interval = max(50, interval_ms)  # Don't allow less than 50ms
        if self._rendering_active:
            self._capture_timer.setInterval(self._capture_interval)
            logger.info(f"E-ink renderer interval changed to {self._capture_interval}ms")
    
    def force_update(self):
        """Force an update on the next capture, even if the screen hasn't changed"""
        self._force_update = True
        # Trigger a capture immediately
        QTimer.singleShot(0, self._capture_frame)
    
    def _capture_frame(self):
        """Capture the current screen content"""
        error_count = getattr(self, '_error_count', 0)
        
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
            logger.debug(f"Window: {main_window.objectName() or 'unnamed'}, Size: {main_window.width()}x{main_window.height()}")
            
            # Get the window size
            width = main_window.width()
            height = main_window.height()
            
            # Try different approaches to capture the actual window content
            image = None
            
            # Approach 1: For QQuickWindow (QML content)
            if isinstance(main_window, QQuickWindow):
                try:
                    logger.debug("Trying QQuickWindow grabbing approach")
                    # This method is available in PyQt6 and should work in offscreen mode
                    image = main_window.grabWindow()
                    logger.debug("Successfully captured QQuickWindow content")
                except Exception as e1:
                    logger.warning(f"QQuickWindow grabbing failed: {e1}")
            
            # Approach 2: Use QPixmap.grabWidget() if available
            if image is None:
                try:
                    logger.debug("Trying QPixmap.grabWidget approach")
                    pixmap = QPixmap(width, height)
                    pixmap.fill(Qt.GlobalColor.white)  # Start with a white background
                    
                    # Try different APIs based on what's available
                    if hasattr(pixmap, 'grabWidget'):
                        # Older PyQt versions
                        pixmap = pixmap.grabWidget(main_window.winId())
                    elif hasattr(QPixmap, 'grabWindow'):
                        # Try direct static method
                        pixmap = QPixmap.grabWindow(main_window.winId())
                    
                    image = pixmap.toImage()
                    logger.debug("Successfully captured widget content")
                except Exception as e2:
                    logger.warning(f"Widget grabbing failed: {e2}")
            
            # Approach 3: Last resort - create a blank image with a border
            if image is None:
                logger.warning("Could not capture actual UI content, falling back to test pattern")
                image = QImage(width, height, QImage.Format.Format_ARGB32)
                image.fill(Qt.GlobalColor.white)  # Fill with white background
                
                # Draw a simple border to at least show something
                for x in range(width):
                    for y in range(height):
                        # Draw a border
                        if x < 2 or x >= width-2 or y < 2 or y >= height-2:
                            image.setPixelColor(x, y, Qt.GlobalColor.black)
                
                # Draw text to indicate this is a fallback
                # Draw "OFFSCREEN MODE" text (simplified)
                text_y = height // 2 - 5
                text_x = width // 2 - 40
                # Just draw a line for simplicity
                for x in range(text_x, text_x + 80):
                    image.setPixelColor(x, text_y, Qt.GlobalColor.black)
                    image.setPixelColor(x, text_y + 10, Qt.GlobalColor.black)
                
                logger.debug("Created fallback image with border")
            
            # Save the image to a file for debugging
            # image.save("captured_screen.png")
            # logger.debug(f"Saved screen capture to captured_screen.png")
            
            # Convert to e-ink compatible format (assuming 1-bit black and white)
            eink_data = self._convert_to_eink_format(image)
            
            # # For debugging, save the binary data
            # with open("eink_data.bin", "wb") as f:
            #     f.write(eink_data)
            
            # Check if frame is different from previous
            if self._force_update or self._is_frame_different(eink_data):
                logger.debug(f"New frame captured: {len(eink_data)} bytes")
                self._add_to_buffer(eink_data, image.width(), image.height())
                self._last_frame = eink_data
                self._force_update = False
                
            # Reset error count on success
            self._error_count = 0
                
        except Exception as e:
            # Increment error count and log
            self._error_count = error_count + 1
            logger.error(f"Error capturing frame: {e}", exc_info=True)
            
            # If we've had too many errors in a row, slow down the capture rate
            if self._error_count > 5:
                old_interval = self._capture_timer.interval()
                new_interval = min(2000, old_interval * 2)  # Double interval up to 2 seconds max
                
                if old_interval != new_interval:
                    logger.warning(f"Too many errors, reducing capture rate: {old_interval}ms -> {new_interval}ms")
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
        
        # Get image dimensions
        width = image.width()
        height = image.height()
        
        # Calculate output buffer size (1 bit per pixel, 8 pixels per byte)
        bytes_per_row = (width + 7) // 8
        total_bytes = bytes_per_row * height
        
        # DEBUG ONLY - save the original grayscale image for reference
        try:
            if self._force_update:
                image.save("debug_original.png")
        except Exception:
            pass
        
        # ONLY mirror the image horizontally (left-to-right) without flipping vertically
        # The vertical flip is already happening somewhere else in the pipeline
        mirrored_data = [0] * (width * height)
        
        # ONLY do horizontal mirroring: x -> (width-1-x)
        # Keep y the same (no vertical flipping)
        for y in range(height):
            for x in range(width):
                # Get original pixel value
                original_value = image.pixelColor(x, y).red()
                
                # Calculate destination position after mirroring:
                # - For horizontal mirroring ONLY: x -> (width-1-x)
                # - Keep y the same (no vertical flipping)
                dest_x = width - 1 - x
                dest_y = y  # Keep the same y coordinate
                
                # Store in 1D array - calculate linear index
                dest_index = dest_y * width + dest_x
                mirrored_data[dest_index] = original_value
                
        # Check if dithering is enabled in config
        dithering_enabled = bool(config.get("display", "eink_dithering_enabled") or False)
        
        if dithering_enabled:
            # Apply Floyd-Steinberg dithering to the mirrored data
            print(f"Applying dithering to image")
            dithered_data = self._apply_dithering(mirrored_data, width, height)
        else:
            # No dithering, use the mirrored data directly
            dithered_data = mirrored_data
        
        # Convert the processed data (either dithered or not) to 1-bit representation
        output = bytearray(total_bytes)
        white_count = 0
        black_count = 0
        
        for y in range(height):
            for x_byte in range(bytes_per_row):
                byte_val = 0
                for bit in range(8):
                    x = x_byte * 8 + bit
                    if x < width:
                        # Get pixel from our processed data
                        index = y * width + x
                        pixel_gray = dithered_data[index]
                        
                        # INVERTED bit logic: bit 1 = WHITE, bit 0 = BLACK
                        # Set bit 1 for WHITE pixels (>= 128) 
                        if pixel_gray >= 128:  # If pixel is WHITE
                            byte_val |= (1 << (7 - bit))  # MSB first
                            white_count += 1
                        else:
                            black_count += 1
                
                # Store the byte in the output buffer
                output[y * bytes_per_row + x_byte] = byte_val
        
        process_type = "Dithered" if dithering_enabled else "Mirrored"
        print(f"{process_type} image statistics: WHITE pixels: {white_count}, BLACK pixels: {black_count}")
        print(f"Output buffer size: {len(output)} bytes")
        
        return output
        
    def _apply_dithering(self, image_data, width, height):
        """
        Apply Floyd-Steinberg dithering to the image data.
        
        Args:
            image_data: 1D array of grayscale pixel values
            width: Image width
            height: Image height
            
        Returns:
            1D array of dithered pixel values
        """
        # Convert 1D array to 2D for easier processing
        pixels = np.array(image_data, dtype=np.float32).reshape(height, width)
        
        # Make a copy to avoid modifying the original
        dithered = pixels.copy()
        
        # Apply Floyd-Steinberg dithering
        for y in range(height - 1):
            for x in range(1, width - 1):
                old_pixel = dithered[y, x]
                # Find nearest color (0 or 255)
                new_pixel = 0 if old_pixel < 128 else 255
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
            new_pixel = 0 if old_pixel < 128 else 255
            dithered[height - 1, x] = new_pixel
            
            # Can only distribute error horizontally
            quant_error = old_pixel - new_pixel
            dithered[height - 1, x + 1] += quant_error * 7 / 16
        
        # Clip values to 0-255 range to account for possible overflow
        dithered = np.clip(dithered, 0, 255).astype(np.uint8)
        
        # Convert back to 1D array
        return dithered.flatten().tolist()
    
    def _is_frame_different(self, new_frame):
        """Check if the new frame is different from the last one"""
        if self._last_frame is None:
            return True
            
        if len(new_frame) != len(self._last_frame):
            return True
            
        # Simple comparison - can be optimized for performance
        # Consider comparing only a sample of bytes or using numpy for large frames
        return new_frame != self._last_frame
    
    def _add_to_buffer(self, frame_data, width, height):
        """Add a frame to the buffer and emit signal if buffer is ready"""
        with self._buffer_lock:
            self._frame_buffer.append((frame_data, width, height))
            
            # Keep buffer at desired size
            while len(self._frame_buffer) > self._buffer_size:
                self._frame_buffer.pop(0)
                
            # Emit the frame ready signal with the newest frame
            newest_frame = self._frame_buffer[-1]
            self.frameReady.emit(newest_frame[0], newest_frame[1], newest_frame[2])