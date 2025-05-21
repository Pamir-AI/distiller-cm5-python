import numpy as np
import time
from typing import List, Optional, Tuple
from threading import Lock
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSlot, QTimer
from PyQt6.QtGui import QImage
from .EinkDriver import EinkDriver
from ..display_config import config
import logging

logger = logging.getLogger(__name__)


class DitheringMethod(Enum):
    NONE = 0
    FLOYD_STEINBERG = 1
    ORDERED = 2


class EInkRendererBridge(QObject):
    """
    Bridge between EInkRenderer and the e-ink display driver.
    Handles format conversion, dithering, and proper e-ink initialization sequence.
    """

    def __init__(self, parent=None):
        """Initialize the e-ink renderer bridge"""
        super().__init__(parent)
        self.eink_driver = None
        self.driver_lock = Lock()
        self.initialized = False

        # Dithering configuration
        self._dithering_enabled = True
        self._dithering_method = DitheringMethod.FLOYD_STEINBERG

        # Threshold configuration
        self._threshold = config["display"].get("eink_threshold", 128)
        self._threshold = max(
            0, min(255, self._threshold)
        )  # Ensure it's in valid range

        # Initialization
        self._init_timer = QTimer()
        self._init_timer.setSingleShot(True)
        self._init_timer.timeout.connect(self._delayed_init)

        # Frame tracking for refresh strategy
        self._frame_count = 0
        self._first_frame = True

        # Get refresh settings from config
        self._full_refresh_interval = config["display"]["eink_full_refresh_interval"]
        logger.info(
            f"E-Ink display will do full refresh every {self._full_refresh_interval} frames"
        )

    def initialize(self):
        """Initialize the e-ink display driver with proper sequence"""
        if self.initialized and self.eink_driver:
            logger.info("E-Ink display already initialized")
            return True

        try:
            logger.info("Initializing E-Ink display driver...")
            with self.driver_lock:
                # Initialize the driver
                self.eink_driver = EinkDriver()

                try:
                    self.eink_driver.epd_w21_init()
                    logger.info("E-Ink display hardware detected")
                except Exception as hw_err:
                    logger.warning(f"E-Ink hardware initialization issue: {hw_err}")

                # Start a timer to complete initialization after hardware is ready
                self._init_timer.start(
                    100
                )  # 100ms delay before completing initialization

            return True
        except Exception as e:
            logger.error(f"Error initializing e-ink display: {e}")
            return False

    def _delayed_init(self):
        """Complete the initialization sequence after hardware is ready"""
        try:
            with self.driver_lock:
                if not self.eink_driver:
                    logger.warning("E-ink driver not initialized")
                    return

                # Proper initialization sequence
                if config["display"]["Full_Refresh_LUT_MODE"]:
                    self.eink_driver.epd_init_lut()
                else:
                    self.eink_driver.epd_init_fast()  # Initial hardware setup

                self.initialized = True
                self._first_frame = True
                self._frame_count = 0
                logger.info("E-ink display initialized successfully")
        except Exception as e:
            logger.error(f"Error in delayed e-ink initialization: {e}")

    def set_dithering(
        self, enabled: bool, method: int = DitheringMethod.FLOYD_STEINBERG.value
    ):
        """
        Enable or disable dithering

        Args:
            enabled: Whether dithering is enabled
            method: Dithering method (0=None, 1=Floyd-Steinberg, 2=Ordered)
        """
        self._dithering_enabled = enabled
        try:
            self._dithering_method = DitheringMethod(method)
        except ValueError:
            logger.warning(
                f"Invalid dithering method {method}, defaulting to Floyd-Steinberg"
            )
            self._dithering_method = DitheringMethod.FLOYD_STEINBERG

        # Get threshold value from config
        self._threshold = config["display"].get("eink_threshold", 128)
        self._threshold = max(
            0, min(255, self._threshold)
        )  # Ensure it's in valid range

        logger.info(
            f"Dithering {'enabled' if enabled else 'disabled'}, method: {self._dithering_method.name}, threshold: {self._threshold}"
        )

    @pyqtSlot(bytearray, int, int)
    def handle_frame(self, frame_data: bytearray, width: int, height: int):
        """
        Handle a new frame from the EInkRenderer.

        Args:
            frame_data: Data from EInkRenderer where bit 1 = BLACK, bit 0 = WHITE
            width: Frame width
            height: Frame height
        """
        if not self.initialized or not self.eink_driver:
            logger.debug("Skipping frame, display not initialized")
            return

        try:
            with self.driver_lock:
                # Convert directly from frame_data to e-ink display format
                display_data = self.frame_to_eink_data(frame_data, width, height)

                # Apply refresh strategy based on frame count
                self._apply_refresh_strategy()

                # Send the data to the display
                try:
                    self.eink_driver.pic_display(display_data)
                    # if config["display"]["Full_Refresh_LUT_MODE"]: 
                    #     time.sleep(1.3)
                except Exception as e:
                    logger.error(f"Error displaying frame: {e}")

        except Exception as e:
            logger.error(f"Error processing frame for e-ink: {e}")
            self._recover_driver()

    def _apply_refresh_strategy(self):
        """Apply the appropriate refresh strategy based on frame count"""
        if self._first_frame:
            # First frame after initialization - already in fast mode
            self._first_frame = False
            self._frame_count = 1
        elif self._frame_count >= self._full_refresh_interval:
            # Time for a full refresh
            if config["display"]["Full_Refresh_LUT_MODE"]:
                self.eink_driver.epd_init_lut()
                logger.info("FULL REFRESH LUT MODE")
            else:
                self.eink_driver.epd_init_fast()
                logger.info("FULL REFRESH FAST MODE")
            self._frame_count = 1  # Reset counter
        else:
            # Normal partial update
            self.eink_driver.epd_init_part()
            self._frame_count += 1

    def _recover_driver(self):
        """Attempt to recover the e-ink driver after an error"""
        with self.driver_lock:
            try:
                if self.eink_driver:
                    self.eink_driver.cleanup()
                self.eink_driver = None
                self.initialized = False
                self.initialize()
                logger.info("E-ink driver recovered successfully")
            except Exception as e:
                logger.error(f"Failed to recover driver: {e}")

    def frame_to_eink_data(
        self, frame_data: bytearray, width: int, height: int
    ) -> List[int]:
        """
        Convert frame data directly to e-ink display format.

        Args:
            frame_data: Data from EInkRenderer where bit 1 = BLACK, bit 0 = WHITE
            width: Frame width
            height: Frame height

        Returns:
            Data ready for e-ink display
        """
        # Calculate bytes per row in the source data
        bytes_per_row = (width + 7) // 8
        total_bytes = bytes_per_row * height

        # Ensure we have the expected amount of data
        if len(frame_data) != total_bytes:
            logger.warning(
                f"Unexpected data size. Got {len(frame_data)}, expected {total_bytes}"
            )
            if len(frame_data) < total_bytes:
                frame_data = frame_data + bytearray(total_bytes - len(frame_data))
            else:
                frame_data = frame_data[:total_bytes]

        # Invert bits (renderer: 1=WHITE, driver: 1=BLACK)
        data_np = np.array(frame_data, dtype=np.uint8)
        data_np = ~data_np  # Bitwise NOT to invert (1->0, 0->1)
        return data_np.tolist()

    def cleanup(self):
        """Clean up e-ink display resources"""
        if self.eink_driver:
            try:
                with self.driver_lock:
                    # Clear the display before shutting down
                    
                    self.eink_driver.pic_display_clear(poweroff=True)
                    # if config["display"]["Full_Refresh_LUT_MODE"]: 
                    #     time.sleep(1.3)
                    self.eink_driver.cleanup()
                    logger.info("E-ink display cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up e-ink display: {e}")

            self.eink_driver = None
            self.initialized = False


# Try to use the more optimized numba functions if available
try:
    from numba import jit

    @jit(nopython=True, cache=True)
    def _numba_dump_1bit(pixels: np.ndarray, threshold: int = 128) -> list:
        """Convert an image to 1-bit representation."""
        # Threshold and convert to binary
        pixels = np.clip(pixels, 0, 255)
        pixels_binary = (pixels > threshold).astype(np.uint8)

        # Calculate the needed size for the result
        height, width = pixels.shape
        bytes_per_row = (width + 7) // 8
        result_size = bytes_per_row * height
        int_pixels = np.zeros(result_size, dtype=np.uint8)

        # Pack bits into bytes efficiently
        idx = 0
        for y in range(height):
            for x_byte in range(bytes_per_row):
                byte_val = 0
                for bit in range(8):
                    x = x_byte * 8 + bit
                    if x < width and pixels_binary[y, x]:
                        byte_val |= 1 << (7 - bit)  # MSB first
                int_pixels[idx] = byte_val
                idx += 1

        return [int(x) for x in int_pixels]

    @jit(nopython=True, cache=True)
    def _numba_floyd_steinberg(pixels: np.ndarray, threshold: int = 128) -> np.ndarray:
        """Apply Floyd-Steinberg dithering to an image."""
        height, width = pixels.shape
        pixels = pixels.copy()  # Make a copy to avoid modifying the original

        # Process all rows except the last one
        for y in range(height - 1):
            for x in range(1, width - 1):
                old_pixel = pixels[y, x]
                new_pixel = 0 if old_pixel < threshold else 255
                pixels[y, x] = new_pixel
                quant_error = old_pixel - new_pixel

                # Distribute error to neighboring pixels
                pixels[y, x + 1] += quant_error * 7 / 16
                pixels[y + 1, x - 1] += quant_error * 3 / 16
                pixels[y + 1, x] += quant_error * 5 / 16
                pixels[y + 1, x + 1] += quant_error * 1 / 16

        # Handle the last row separately (no pixels below to distribute error to)
        y = height - 1
        for x in range(1, width - 1):
            old_pixel = pixels[y, x]
            new_pixel = 0 if old_pixel < threshold else 255
            pixels[y, x] = new_pixel
            quant_error = old_pixel - new_pixel
            pixels[y, x + 1] += quant_error * 7 / 16

        return pixels

    @jit(nopython=True, cache=True)
    def _numba_ordered_dithering(
        pixels: np.ndarray, threshold_base: int = 128
    ) -> np.ndarray:
        """Apply ordered dithering to an image."""
        # Define 8x8 Bayer matrix for ordered dithering - scaled by threshold_base/128
        # This adjusts the dithering pattern based on the threshold value
        scale_factor = threshold_base / 128.0

        bayer_matrix = (
            np.array(
                [
                    [0, 48, 12, 60, 3, 51, 15, 63],
                    [32, 16, 44, 28, 35, 19, 47, 31],
                    [8, 56, 4, 52, 11, 59, 7, 55],
                    [40, 24, 36, 20, 43, 27, 39, 23],
                    [2, 50, 14, 62, 1, 49, 13, 61],
                    [34, 18, 46, 30, 33, 17, 45, 29],
                    [10, 58, 6, 54, 9, 57, 5, 53],
                    [42, 26, 38, 22, 41, 25, 37, 21],
                ],
                dtype=np.float32,
            )
            / 64.0
            * 255
            * scale_factor
        )

        height, width = pixels.shape
        result = np.zeros((height, width), dtype=np.uint8)

        # Apply threshold based on the Bayer matrix
        for y in range(height):
            for x in range(width):
                threshold = bayer_matrix[y % 8, x % 8]
                result[y, x] = 0 if pixels[y, x] < threshold else 255

        return result

    # Use Numba optimized functions
    logger.info("Using Numba-optimized e-ink conversion functions")

except ImportError:
    # Fallback to standard Python implementation
    logger.info("Numba not available, using standard e-ink conversion functions")

    def _numba_dump_1bit(pixels: np.ndarray, threshold: int = 128) -> list:
        """Standard Python implementation of dump_1bit"""
        # Threshold and convert to binary
        pixels = np.clip(pixels, 0, 255)
        pixels_binary = (pixels > threshold).astype(np.uint8)

        # Calculate the needed size for the result
        height, width = pixels.shape
        bytes_per_row = (width + 7) // 8
        result_size = bytes_per_row * height
        int_pixels = np.zeros(result_size, dtype=np.uint8)

        # Pack bits into bytes
        idx = 0
        for y in range(height):
            for x_byte in range(bytes_per_row):
                byte_val = 0
                for bit in range(8):
                    x = x_byte * 8 + bit
                    if x < width and pixels_binary[y, x]:
                        byte_val |= 1 << (7 - bit)  # MSB first
                int_pixels[idx] = byte_val
                idx += 1

        return [int(x) for x in int_pixels]

    def _numba_floyd_steinberg(pixels: np.ndarray, threshold: int = 128) -> np.ndarray:
        """Standard Python implementation of Floyd-Steinberg dithering"""
        height, width = pixels.shape
        pixels = pixels.copy()  # Make a copy to avoid modifying the original

        for y in range(height - 1):
            for x in range(1, width - 1):
                old_pixel = pixels[y, x]
                new_pixel = 0 if old_pixel < threshold else 255
                pixels[y, x] = new_pixel
                quant_error = old_pixel - new_pixel

                pixels[y, x + 1] += quant_error * 7 / 16
                pixels[y + 1, x - 1] += quant_error * 3 / 16
                pixels[y + 1, x] += quant_error * 5 / 16
                pixels[y + 1, x + 1] += quant_error * 1 / 16

        # Handle the last row separately
        y = height - 1
        for x in range(1, width - 1):
            old_pixel = pixels[y, x]
            new_pixel = 0 if old_pixel < threshold else 255
            pixels[y, x] = new_pixel
            quant_error = old_pixel - new_pixel
            pixels[y, x + 1] += quant_error * 7 / 16

        return pixels

    def _numba_ordered_dithering(
        pixels: np.ndarray, threshold_base: int = 128
    ) -> np.ndarray:
        """Standard Python implementation of ordered dithering"""
        # Define 8x8 Bayer matrix for ordered dithering - scaled by threshold_base/128
        # This adjusts the dithering pattern based on the threshold value
        scale_factor = threshold_base / 128.0

        bayer_matrix = (
            np.array(
                [
                    [0, 48, 12, 60, 3, 51, 15, 63],
                    [32, 16, 44, 28, 35, 19, 47, 31],
                    [8, 56, 4, 52, 11, 59, 7, 55],
                    [40, 24, 36, 20, 43, 27, 39, 23],
                    [2, 50, 14, 62, 1, 49, 13, 61],
                    [34, 18, 46, 30, 33, 17, 45, 29],
                    [10, 58, 6, 54, 9, 57, 5, 53],
                    [42, 26, 38, 22, 41, 25, 37, 21],
                ]
            )
            / 64.0
            * 255
            * scale_factor
        )

        height, width = pixels.shape
        result = np.zeros((height, width), dtype=np.uint8)

        for y in range(height):
            for x in range(width):
                threshold = bayer_matrix[y % 8, x % 8]
                result[y, x] = 0 if pixels[y, x] < threshold else 255

        return result
