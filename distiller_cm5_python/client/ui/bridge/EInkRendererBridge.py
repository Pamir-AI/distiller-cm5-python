import numpy as np
import time
from typing import List, Optional
from threading import Lock
from PyQt6.QtCore import QObject, pyqtSlot, QTimer
from PyQt6.QtGui import QImage
from numba import jit
from .Eink_Driver import EinkDriver, config

class EInkRendererBridge(QObject):
    """
    Bridge between EInkRenderer and the e-ink display driver.
    Handles format conversion, dithering, and proper e-ink initialization sequence.
    """
    
    def __init__(self, parent=None):
        """Initialize the e-ink renderer bridge"""
        super().__init__(parent)
        self.eink_driver = None
        self.last_image_cache = None
        self.driver_lock = Lock()
        self.initialized = False
        self._dithering_enabled = True
        self._init_timer = QTimer()
        self._init_timer.setSingleShot(True)
        self._init_timer.timeout.connect(self._delayed_init)
        
        # Frame tracking for refresh strategy
        self._frame_count = 0
        self._first_frame = True
        
        # Get refresh settings from config
        self._full_refresh_interval = int(config.get("display", "eink_full_refresh_interval") or 30)
        print(f"E-Ink display will do full refresh every {self._full_refresh_interval} frames")
        
    def initialize(self):
        """Initialize the e-ink display driver with proper sequence"""
        try:
            print("Initializing E-Ink display driver...")
            with self.driver_lock:
                # Initialize the driver 
                self.eink_driver = EinkDriver()
                
                # In headless environments, we need more robust initialization
                # Perform a quick test to see if the driver is responsive
                try:
                    self.eink_driver.epd_w21_init()
                    print("E-Ink display hardware detected")
                except Exception as hw_err:
                    print(f"Warning: E-Ink hardware initialization issue: {hw_err}")
                    # Continue anyway - some errors are expected in headless mode
                
                # Start a timer to complete initialization after hardware is ready
                self._init_timer.start(100)  # 100ms delay before completing initialization
                
            return True
        except Exception as e:
            print(f"Error initializing e-ink display: {e}")
            return False
            
    def _delayed_init(self):
        """Complete the initialization sequence after hardware is ready"""
        try:
            with self.driver_lock:
                if not self.eink_driver:
                    print("E-ink driver not initialized")
                    return
                    
                # Proper initialization sequence - only initialize with fast mode
                # We'll call epd_init_part() when sending the first frame
                self.eink_driver.epd_init_fast()  # Initial hardware setup
                
                self.initialized = True
                self._first_frame = True  # Mark that we need to send first frame
                self._frame_count = 0
                print("E-ink display initialized successfully")
        except Exception as e:
            print(f"Error in delayed e-ink initialization: {e}")
    
    def set_dithering(self, enabled: bool):
        """Enable or disable dithering"""
        self._dithering_enabled = enabled
    
    @pyqtSlot(bytearray, int, int)
    def handle_frame(self, frame_data: bytearray, width: int, height: int):
        """
        Handle a new frame from the EInkRenderer.
        
        Args:
            frame_data: Data from EInkRenderer where bit 1 = BLACK, bit 0 = WHITE
                        (We've reverted back to the original convention where BLACK is 1, WHITE is 0)
            width: Frame width
            height: Frame height
        """
        if not self.initialized or not self.eink_driver:
            return
        
        try:
            with self.driver_lock:
                # Convert directly from frame_data to e-ink display format
                display_data = self.frame_to_eink_data(frame_data, width, height)
                
                # Determine refresh strategy based on frame count
                if self._first_frame:
                    # First frame after initialization - already in fast mode
                    # No need to call epd_init_fast(), already done in initialization
                    self._first_frame = False
                    self._frame_count = 1
                elif self._frame_count >= self._full_refresh_interval:
                    # Time for a full refresh
                    self.eink_driver.epd_init_fast()
                    self._frame_count = 1  # Reset counter
                else:
                    # Normal partial update
                    self.eink_driver.epd_init_part()
                    self._frame_count += 1
                
                # Send the data to the display
                try:
                    self.eink_driver.pic_display(display_data)
                except Exception as e:
                    print(f"Error displaying frame: {e}")
                
        except Exception as e:
            print(f"Error processing frame for e-ink: {e}")
    
    def frame_to_eink_data(self, frame_data: bytearray, width: int, height: int) -> List[int]:
        """
        Convert frame data directly to e-ink display format.
        This is a simplified pipeline that processes the data with fewer conversions.
        
        Args:
            frame_data: Data from EInkRenderer where bit 1 = BLACK, bit 0 = WHITE
                        (We've reverted back to the original convention where BLACK is 1, WHITE is 0)
            width: Frame width
            height: Frame height
            
        Returns:
            Data ready for e-ink display
        """
        # The frame_data is in 1-bit packed format from EInkRenderer
        # where bit 1 = BLACK, bit 0 = WHITE (using original convention)
        # We just need to convert it to the format expected by the e-ink display
        
        # Calculate bytes per row in the source data
        bytes_per_row = (width + 7) // 8
        total_bytes = bytes_per_row * height
        
        # Ensure we have the expected amount of data
        if len(frame_data) != total_bytes:
            print(f"Warning: Unexpected data size. Got {len(frame_data)}, expected {total_bytes}")
            # Pad or truncate to expected size
            if len(frame_data) < total_bytes:
                frame_data = frame_data + bytearray(total_bytes - len(frame_data))
            else:
                frame_data = frame_data[:total_bytes]
        
        # Convert bytearray to list of integers for the e-ink display
        return [int(b) for b in frame_data]
    
    def _bits_to_qimage(self, frame_data: bytearray, width: int, height: int) -> QImage:
        """
        Convert packed 1-bit data to a QImage.
        
        Args:
            frame_data: Packed 1-bit pixel data
            width: Image width
            height: Image height
            
        Returns:
            QImage representation of the frame
        """
        # Create a grayscale image
        image = QImage(width, height, QImage.Format.Format_Grayscale8)
        
        # Calculate bytes per row in the source data
        bytes_per_row = (width + 7) // 8
        
        # Fill image with white background
        image.fill(255)
        
        # Set pixels from the packed bits
        for y in range(height):
            for x in range(width):
                byte_index = y * bytes_per_row + x // 8
                if byte_index < len(frame_data):
                    bit_index = 7 - (x % 8)
                    bit_value = (frame_data[byte_index] >> bit_index) & 0x01
                    # In our data, 1 = black, 0 = white
                    pixel_value = 0 if bit_value else 255
                    # Use setPixel instead of setPixelColor with fromValue
                    image.setPixel(x, y, pixel_value)
        
        return image
    
    def _qimage_to_numpy(self, image: QImage) -> np.ndarray:
        """
        Convert QImage to numpy array.
        
        Args:
            image: QImage to convert
            
        Returns:
            Numpy array representation of the image
        """
        width = image.width()
        height = image.height()
        
        # Get image bytes per line
        bytes_per_line = image.bytesPerLine()
        
        # Get pointer to image data
        ptr = image.bits()
        ptr.setsize(bytes_per_line * height)
        
        # Create numpy array from image data
        arr = np.array(ptr).reshape(height, bytes_per_line)
        
        # If bytes_per_line is wider than width, trim the array
        if bytes_per_line > width:
            arr = arr[:, :width]
            
        return arr
    
    def preprocess_1bit(self, pixels: np.ndarray, dtype=np.float32) -> np.ndarray:
        """
        Preprocess image for 1-bit display.
        
        Args:
            pixels: Input pixel array
            dtype: Data type for output array
            
        Returns:
            Preprocessed pixel array
        """
        # Convert to float for processing if not already
        if pixels.dtype != np.float32 and dtype == np.float32:
            pixels = pixels.astype(np.float32)
        
        return pixels
    
    def _instance_dump_1bit(self, pixels: np.ndarray) -> List[int]:
        """
        Convert an image to 1-bit representation.
        
        Args:
            pixels: The input pixel array
            
        Returns:
            A list of integers representing the 1-bit image
        """
        # Flatten the array for processing
        # Ensure pixels are in valid range after dithering
        pixels = np.clip(pixels, 0, 255)
        pixels_quantized = np.digitize(pixels, bins=[64, 128, 192], right=True)

        # Calculate the needed size for the result
        result_size = (pixels.size + 7) // 8
        int_pixels = np.zeros(result_size, dtype=np.uint8)

        index = 0
        for i in range(pixels_quantized.size):
            bit = 1 if pixels_quantized.flat[i] in [2, 3] else 0
            if i % 8 == 0 and i > 0:
                index += 1
            int_pixels[index] |= bit << (7 - (i % 8))
        return [int(x) for x in int_pixels]
    
    def _instance_dump_1bit_with_dithering(self, pixels: np.ndarray) -> List[int]:
        """
        Convert an image to 1-bit representation with dithering.
        
        Args:
            pixels: The input pixel array
            
        Returns:
            A list of integers representing the 1-bit image with dithering
        """
        # Make a copy of the pixels to avoid modifying the original
        pixels_copy = pixels.copy()
        # Apply dithering to the copy
        pixels_dithered = self._instance_floyd_steinberg_dithering(pixels_copy)
        # Convert to 1-bit
        return self._instance_dump_1bit(pixels_dithered)
    
    def _instance_floyd_steinberg_dithering(self, pixels: np.ndarray) -> np.ndarray:
        """
        Apply Floyd-Steinberg dithering to an image.
        
        Args:
            pixels: The input pixel array
            
        Returns:
            The dithered pixel array
        """
        for y in range(pixels.shape[0] - 1):
            for x in range(1, pixels.shape[1] - 1):
                old_pixel = pixels[y, x]
                new_pixel = np.round(old_pixel / 85) * 85
                pixels[y, x] = new_pixel
                quant_error = old_pixel - new_pixel
                pixels[y, x + 1] += quant_error * 7 / 16
                pixels[y + 1, x - 1] += quant_error * 3 / 16
                pixels[y + 1, x] += quant_error * 5 / 16
                pixels[y + 1, x + 1] += quant_error * 1 / 16
        return pixels
    
    def cleanup(self):
        """Clean up e-ink display resources"""
        if self.eink_driver:
            try:
                with self.driver_lock:
                    # Clear the display before shutting down
                    self.eink_driver.pic_display_clear(poweroff=True)
                    self.eink_driver.cleanup()
                    print("E-ink display cleaned up")
            except Exception as e:
                print(f"Error cleaning up e-ink display: {e}")
            
            self.eink_driver = None
            self.initialized = False

# Try to use the more optimized numba functions if available
try:
    from numba import jit
    
    @jit(nopython=True, cache=True)
    def dump_1bit(pixels: np.ndarray) -> list:
        """
        Convert an image to 1-bit representation.

        Args:
            pixels: The input pixel array
            
        Returns:
            A list of integers representing the 1-bit image
        """
        # Flatten the array for processing
        # Ensure pixels are in valid range after dithering
        pixels = np.clip(pixels, 0, 255)
        pixels_quantized = np.digitize(pixels, bins=[64, 128, 192], right=True)

        # Calculate the needed size for the result
        result_size = (pixels.size + 7) // 8
        int_pixels = np.zeros(result_size, dtype=np.uint8)

        index = 0
        for i in range(pixels_quantized.size):
            bit = 1 if pixels_quantized.flat[i] in [2, 3] else 0
            if i % 8 == 0 and i > 0:
                index += 1
            int_pixels[index] |= bit << (7 - (i % 8))
        return [int(x) for x in int_pixels]

    @jit(nopython=True, cache=True)
    def floydSteinbergDithering_numba(pixels: np.ndarray) -> np.ndarray:
        """
        Apply Floyd-Steinberg dithering to an image.

        Args:
            pixels: The input pixel array
            
        Returns:
            The dithered pixel array
        """
        for y in range(pixels.shape[0] - 1):
            for x in range(1, pixels.shape[1] - 1):
                old_pixel = pixels[y, x]
                new_pixel = np.round(old_pixel / 85) * 85
                pixels[y, x] = new_pixel
                quant_error = old_pixel - new_pixel
                pixels[y, x + 1] += quant_error * 7 / 16
                pixels[y + 1, x - 1] += quant_error * 3 / 16
                pixels[y + 1, x] += quant_error * 5 / 16
                pixels[y + 1, x + 1] += quant_error * 1 / 16
        return pixels

    @jit(nopython=True, cache=True)
    def dump_1bit_with_dithering(pixels: np.ndarray) -> list:
        """
        Convert an image to 1-bit representation with dithering.

        Args:
            pixels: The input pixel array
            
        Returns:
            A list of integers representing the 1-bit image with dithering
        """
        # Make a copy of the pixels to avoid modifying the original
        pixels_copy = pixels.copy()
        # Apply dithering to the copy
        pixels_dithered = floydSteinbergDithering_numba(pixels_copy)
        # Convert to 1-bit
        return dump_1bit(pixels_dithered)
    
    # Create wrapper functions that can be used as instance methods
    def _instance_dump_1bit(self, pixels):
        """Instance method wrapper for dump_1bit"""
        return dump_1bit(pixels)
        
    def _instance_dump_1bit_with_dithering(self, pixels):
        """Instance method wrapper for dump_1bit_with_dithering"""
        return dump_1bit_with_dithering(pixels)
        
    def _instance_floyd_steinberg_dithering(self, pixels):
        """Instance method wrapper for floydSteinbergDithering_numba"""
        return floydSteinbergDithering_numba(pixels)
    
    # Replace the methods with optimized versions using proper wrappers
    EInkRendererBridge._dump_1bit = _instance_dump_1bit
    EInkRendererBridge._dump_1bit_with_dithering = _instance_dump_1bit_with_dithering
    EInkRendererBridge._floyd_steinberg_dithering = _instance_floyd_steinberg_dithering
    
    print("Using Numba-optimized e-ink conversion functions")
except ImportError:
    print("Numba not available, using standard e-ink conversion functions") 