import sys
import os
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Add SDK path to sys.path if not already there
sdk_path = "/opt/distiller-cm5-sdk"
if sdk_path not in sys.path and os.path.exists(sdk_path):
    sys.path.insert(0, sdk_path)

# Import the SDK Display class
try:
    from distiller_cm5_sdk.hardware.eink import Display, DisplayError, DisplayMode
except ImportError as e:
    raise ImportError(f"distiller-cm5-sdk is required but not available: {e}")


class EinkDriver:
    """E-ink display driver that uses the distiller-cm5-sdk."""
    
    def __init__(self) -> None:
        """Initialize the SDK-based e-ink driver."""
        try:
            self._sdk_display = Display()
            # Get dimensions from SDK
            self.EPD_WIDTH, self.EPD_HEIGHT = self._sdk_display.get_dimensions()
            logger.info(f"Initialized SDK e-ink driver: {self.EPD_WIDTH}x{self.EPD_HEIGHT}")
        except Exception as e:
            logger.error(f"Failed to initialize SDK display: {e}")
            raise DisplayError(f"Failed to initialize e-ink display: {e}")
    
    def cleanup(self) -> None:
        """Clean up SDK resources."""
        if self._sdk_display:
            try:
                self._sdk_display.close()
            except Exception as e:
                logger.error(f"Error cleaning up SDK display: {e}")
    
    def pic_display(self, new_data: bytes) -> None:
        """Display new data on the e-ink display using SDK.

        Args:
            new_data: Bytes representing pixel data for e-ink display
        """
        try:
            # Validate data size
            expected_size = (self.EPD_WIDTH * self.EPD_HEIGHT) // 8
            if len(new_data) != expected_size:
                logger.error(f"Data size mismatch: got {len(new_data)}, expected {expected_size}")
                raise ValueError(f"Data must be exactly {expected_size} bytes, got {len(new_data)}")
            
            logger.debug(f"Displaying {len(new_data)} bytes on {self.EPD_WIDTH}x{self.EPD_HEIGHT} display")
            self._sdk_display.display_image(new_data, DisplayMode.FULL)
        except Exception as e:
            logger.error(f"SDK display failed: {e}")
            raise
    
    def pic_display_clear(self, poweroff: bool = False) -> None:
        """Clear the display using SDK."""
        try:
            self._sdk_display.clear()
            if poweroff:
                self._sdk_display.sleep()
        except Exception as e:
            logger.error(f"SDK clear failed: {e}")
            raise
    
    def epd_w21_init(self) -> None:
        """Initialize the e-ink display using SDK."""
        try:
            self._sdk_display.initialize()
        except Exception as e:
            logger.error(f"SDK initialization failed: {e}")
            raise
    
    def pic_display_4g(self, datas: bytes) -> None:
        """Display 4-gray image using SDK.
        
        Args:
            datas: Bytes representing 4-gray pixel data
        """
        try:
            # Validate data size
            expected_size = (self.EPD_WIDTH * self.EPD_HEIGHT) // 8
            if len(datas) != expected_size:
                logger.error(f"4G data size mismatch: got {len(datas)}, expected {expected_size}")
                raise ValueError(f"4G data must be exactly {expected_size} bytes, got {len(datas)}")
            
            logger.debug(f"Displaying 4G {len(datas)} bytes on {self.EPD_WIDTH}x{self.EPD_HEIGHT} display")
            self._sdk_display.display_image(datas, DisplayMode.FULL)
        except Exception as e:
            logger.error(f"SDK 4-gray display failed: {e}")
            raise
    
    # Compatibility methods for existing code
    def epd_init(self) -> None:
        """Initialize display (compatibility method)."""
        self.epd_w21_init()
    
    def epd_init_fast(self) -> None:
        """Initialize display in fast mode (compatibility method)."""
        self.epd_w21_init()
    
    def epd_init_part(self) -> None:
        """Initialize display for partial update (compatibility method)."""
        # SDK handles refresh modes internally
        pass
    
    def epd_init_lut(self) -> None:
        """Initialize display with LUT (compatibility method)."""
        self.epd_w21_init()
    
    def power_off(self) -> None:
        """Power off the display."""
        try:
            self._sdk_display.sleep()
        except Exception as e:
            logger.error(f"SDK power off failed: {e}")
            raise
    
    def epd_sleep(self) -> None:
        """Put display to sleep."""
        self.power_off()
