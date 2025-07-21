import time
import spidev
from typing import List
import numpy as np
from threading import Thread, Lock
import asyncio
from concurrent.futures import ThreadPoolExecutor
import queue
import logging
import lgpio

logger = logging.getLogger(__name__)


class EinkDriver:
    def __init__(self) -> None:
        self.LUT_4G: List[int] = [
            0x01,
            0x05,
            0x20,
            0x19,
            0x0A,
            0x01,
            0x01,
            0x05,
            0x0A,
            0x01,
            0x0A,
            0x01,
            0x01,
            0x01,
            0x05,
            0x09,
            0x02,
            0x03,
            0x04,
            0x01,
            0x01,
            0x01,
            0x04,
            0x04,
            0x02,
            0x00,
            0x01,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x01,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x01,
            0x01,
            0x01,
            0x05,
            0x20,
            0x19,
            0x0A,
            0x01,
            0x01,
            0x05,
            0x4A,
            0x01,
            0x8A,
            0x01,
            0x01,
            0x01,
            0x05,
            0x49,
            0x02,
            0x83,
            0x84,
            0x01,
            0x01,
            0x01,
            0x84,
            0x84,
            0x82,
            0x00,
            0x01,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x01,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x01,
            0x01,
            0x01,
            0x05,
            0x20,
            0x99,
            0x8A,
            0x01,
            0x01,
            0x05,
            0x4A,
            0x01,
            0x8A,
            0x01,
            0x01,
            0x01,
            0x05,
            0x49,
            0x82,
            0x03,
            0x04,
            0x01,
            0x01,
            0x01,
            0x04,
            0x04,
            0x02,
            0x00,
            0x01,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x01,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x01,
            0x01,
            0x01,
            0x85,
            0x20,
            0x99,
            0x0A,
            0x01,
            0x01,
            0x05,
            0x4A,
            0x01,
            0x8A,
            0x01,
            0x01,
            0x01,
            0x05,
            0x49,
            0x02,
            0x83,
            0x04,
            0x01,
            0x01,
            0x01,
            0x04,
            0x04,
            0x02,
            0x00,
            0x01,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x01,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x01,
            0x01,
            0x01,
            0x85,
            0xA0,
            0x99,
            0x0A,
            0x01,
            0x01,
            0x05,
            0x4A,
            0x01,
            0x8A,
            0x01,
            0x01,
            0x01,
            0x05,
            0x49,
            0x02,
            0x43,
            0x04,
            0x01,
            0x01,
            0x01,
            0x04,
            0x04,
            0x42,
            0x00,
            0x01,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x01,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x01,
            0x01,
            0x09,
            0x10,
            0x3F,
            0x3F,
            0x00,
            0x0B,
        ]

        self.emptyImage: List[int] = [0xFF] * 24960
        self.oldData: List[int] = [0] * 12480

        self.lut_vcom = [
            0x01,
            0x0A,
            0x0A,
            0x0A,
            0x0A,
            0x01,
            0x01,
            0x02,
            0x0F,
            0x01,
            0x0F,
            0x01,
            0x01,
            0x01,
            0x01,
            0x0A,
            0x00,
            0x0A,
            0x00,
            0x01,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ]

        self.lut_ww = [
            0x01,
            0x4A,
            0x4A,
            0x0A,
            0x0A,
            0x01,
            0x01,
            0x02,
            0x8F,
            0x01,
            0x4F,
            0x01,
            0x01,
            0x01,
            0x01,
            0x8A,
            0x00,
            0x8A,
            0x00,
            0x01,
            0x01,
            0x01,
            0x80,
            0x00,
            0x80,
            0x00,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ]

        self.lut_bw = [
            0x01,
            0x4A,
            0x4A,
            0x0A,
            0x0A,
            0x01,
            0x01,
            0x02,
            0x8F,
            0x01,
            0x4F,
            0x01,
            0x01,
            0x01,
            0x01,
            0x8A,
            0x00,
            0x8A,
            0x00,
            0x01,
            0x01,
            0x01,
            0x80,
            0x00,
            0x80,
            0x00,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ]

        self.lut_wb = [
            0x01,
            0x0A,
            0x0A,
            0x8A,
            0x8A,
            0x01,
            0x01,
            0x02,
            0x8F,
            0x01,
            0x4F,
            0x01,
            0x01,
            0x01,
            0x01,
            0x4A,
            0x00,
            0x4A,
            0x00,
            0x01,
            0x01,
            0x01,
            0x40,
            0x00,
            0x40,
            0x00,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ]

        self.lut_bb = [
            0x01,
            0x0A,
            0x0A,
            0x8A,
            0x8A,
            0x01,
            0x01,
            0x02,
            0x8F,
            0x01,
            0x4F,
            0x01,
            0x01,
            0x01,
            0x01,
            0x4A,
            0x00,
            0x4A,
            0x00,
            0x01,
            0x01,
            0x01,
            0x40,
            0x00,
            0x40,
            0x00,
            0x01,
            0x01,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
        ]

        # Raspberry Pi GPIO Pin Definitions
        self.DC_PIN = 7
        self.RST_PIN = 13
        self.BUSY_PIN = 9

        self.EPD_WIDTH = 240
        self.EPD_HEIGHT = 416

        # Initialize lgpio for Raspberry Pi
        self.chip = 0  # Default gpiochip number
        self.lgpio_handle = lgpio.gpiochip_open(self.chip)

        self.spi = self.EPD_GPIO_Init()
        self.epd_w21_init_4g()

        # Async SPI communication setup
        self._spi_lock = Lock()
        self._write_queue = queue.Queue()
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="eink_spi"
        )
        self._running = True

        # Start the SPI worker thread
        self._spi_worker = Thread(target=self._spi_worker_thread, daemon=True)
        self._spi_worker.start()

    def safe_writebytes(self, data, chunk_size=4096):
        """Queue data for async SPI writing."""
        if not self._running:
            logger.warning("SPI driver not running, ignoring write request")
            return

        self._write_queue.put(("data", data, chunk_size))

    def _spi_worker_thread(self):
        """Background thread for handling SPI operations."""
        logger.info("SPI worker thread started")

        while self._running:
            try:
                # Get item from queue with timeout
                try:
                    item = self._write_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                operation, *args = item

                if operation == "data":
                    data, chunk_size = args
                    self._write_chunks_sync(data, chunk_size)
                elif operation == "command":
                    command = args[0]
                    self._execute_command_sync(command)
                elif operation == "stop":
                    break

                self._write_queue.task_done()

            except Exception as e:
                logger.error(f"Error in SPI worker thread: {e}", exc_info=True)

        logger.info("SPI worker thread stopped")

    def _write_chunks_sync(self, data, chunk_size):
        """Synchronous chunked write operation."""
        with self._spi_lock:
            try:
                data_np = np.array(data, dtype=np.uint8)
                for i in range(0, len(data), chunk_size):
                    chunk = data_np[i : i + chunk_size].tolist()
                    self.spi.writebytes(chunk)
            except Exception as e:
                logger.error(f"SPI write error: {e}")
                raise

    def _execute_command_sync(self, command_func):
        """Execute a command function synchronously in the SPI thread."""
        with self._spi_lock:
            try:
                command_func()
            except Exception as e:
                logger.error(f"SPI command error: {e}")
                raise

    def queue_command(self, command_func):
        """Queue a command function for async execution."""
        if not self._running:
            logger.warning("SPI driver not running, ignoring command")
            return

        self._write_queue.put(("command", command_func))

    def cleanup(self) -> None:
        # Stop the SPI worker thread
        if hasattr(self, "_running"):
            self._running = False
            self._write_queue.put(("stop",))

            if hasattr(self, "_spi_worker") and self._spi_worker.is_alive():
                self._spi_worker.join(timeout=2.0)
                if self._spi_worker.is_alive():
                    logger.warning("SPI worker thread did not stop gracefully")

        # Shutdown thread pool
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)

        # Close GPIO
        if hasattr(self, "lgpio_handle"):
            lgpio.gpiochip_close(self.lgpio_handle)

    def EPD_GPIO_Init(self) -> spidev.SpiDev:
        # Configure GPIO pins with lgpio
        lgpio.gpio_claim_output(self.lgpio_handle, self.DC_PIN, 0)
        lgpio.gpio_claim_output(self.lgpio_handle, self.RST_PIN, 0)
        # For input with pull-up, flags=1 means pull-up
        lgpio.gpio_claim_input(self.lgpio_handle, self.BUSY_PIN, lgpio.SET_PULL_UP)

        bus = 0
        device = 0
        spi = spidev.SpiDev()
        spi.open(bus, device)
        spi.max_speed_hz = 30000000
        spi.mode = 0
        return spi

    def SPI_Delay(self) -> None:
        """Delay for SPI communication, used to tune frequency"""
        time.sleep(0.000001)

    def SPI_Write(self, value: int) -> List[int]:
        return self.spi.xfer2([value])

    def epd_w21_write_cmd(self, command: int) -> None:
        self.SPI_Delay()
        lgpio.gpio_write(self.lgpio_handle, self.DC_PIN, 0)  # Low for command
        self.SPI_Write(command)

    def epd_w21_write_data(self, data: int) -> None:
        self.SPI_Delay()
        lgpio.gpio_write(self.lgpio_handle, self.DC_PIN, 1)  # High for data
        self.SPI_Write(data)

    def delay_xms(self, xms: int) -> None:
        time.sleep(xms / 1000.0)

    def epd_w21_init(self) -> None:
        self.delay_xms(100)
        lgpio.gpio_write(self.lgpio_handle, self.RST_PIN, 0)  # Reset active low
        self.delay_xms(20)
        lgpio.gpio_write(self.lgpio_handle, self.RST_PIN, 1)  # Reset inactive
        self.delay_xms(20)

    def EPD_Display(self, image: List[int]) -> None:
        width = (self.EPD_WIDTH + 7) // 8
        height = self.EPD_HEIGHT

        self.epd_w21_write_cmd(0x10)
        for j in range(height):
            for i in range(width):
                self.epd_w21_write_data(image[i + j * width])

        self.epd_w21_write_cmd(0x13)
        for _ in range(height * width):
            self.epd_w21_write_data(0x00)

        self.epd_w21_write_cmd(0x12)
        self.delay_xms(1)  # Necessary delay
        self.lcd_chkstatus()

    def lcd_chkstatus(self) -> None:
        # For lgpio, 0 means low which indicates busy
        while lgpio.gpio_read(self.lgpio_handle, self.BUSY_PIN) == 0:
            time.sleep(0.01)  # Wait 10ms before checking again

    def epd_sleep(self) -> None:
        self.power_off() # Power off the display

        self.epd_w21_write_cmd(0x07)  # Deep sleep
        self.epd_w21_write_data(0xA5)

    def epd_init(self) -> None:
        self.epd_w21_init()  # Reset the e-paper display

        self.epd_w21_write_cmd(0x04)  # Power on
        self.lcd_chkstatus()  # Implement this to check the display's busy status

        self.epd_w21_write_cmd(0x50)  # VCOM and data interval setting
        self.epd_w21_write_data(0x97)  # Settings for your display

    def epd_init_fast(self) -> None:
        self.epd_w21_init()  # Reset the e-paper display

        self.epd_w21_write_cmd(0x04)  # Power on
        self.lcd_chkstatus()  # Implement this to check the display's busy status

        self.epd_w21_write_cmd(0xE0)
        self.epd_w21_write_data(0x02)

        self.epd_w21_write_cmd(0xE5)
        self.epd_w21_write_data(0x5A)

    def epd_init_part(self) -> None:
        self.epd_w21_init()  # Reset the e-paper display

        self.epd_w21_write_cmd(0x04)  # Power on
        self.lcd_chkstatus()  # Implement this to check the display's busy status

        self.epd_w21_write_cmd(0xE0)
        self.epd_w21_write_data(0x02)

        self.epd_w21_write_cmd(0xE5)
        self.epd_w21_write_data(0x6E)

        self.epd_w21_write_cmd(0x50)
        self.epd_w21_write_data(0xD7)

    def power_off(self) -> None:
        # Power off the display
        self.epd_w21_write_cmd(0x02)
        self.lcd_chkstatus()

    def write_4g_lut(self) -> None:
        # Write the full LUT to the display
        self.epd_w21_write_cmd(0x20)  # Write VCOM register
        for i in range(42):
            self.epd_w21_write_data(self.LUT_4G[i])

        self.epd_w21_write_cmd(0x21)  # Write LUTWW register
        for i in range(42, 84):
            self.epd_w21_write_data(self.LUT_4G[i])

        self.epd_w21_write_cmd(0x22)  # Write LUTR register
        for i in range(84, 126):
            self.epd_w21_write_data(self.LUT_4G[i])

        self.epd_w21_write_cmd(0x23)  # Write LUTW register
        for i in range(126, 168):
            self.epd_w21_write_data(self.LUT_4G[i])

        self.epd_w21_write_cmd(0x24)  # Write LUTB register
        for i in range(168, 210):
            self.epd_w21_write_data(self.LUT_4G[i])

    def epd_w21_init_4g(self) -> None:
        # Initialize the 4-gray e-paper display
        self.epd_w21_init()  # Reset the e-paper display

        # Panel Setting
        self.epd_w21_write_cmd(0x00)
        self.epd_w21_write_data(0xFF)  # LUT from MCU
        self.epd_w21_write_data(0x0D)

        # Power Setting
        self.epd_w21_write_cmd(0x01)
        self.epd_w21_write_data(0x03)  # Enable internal VSH, VSL, VGH, VGL
        self.epd_w21_write_data(self.LUT_4G[211])  # VGH=20V, VGL=-20V
        self.epd_w21_write_data(self.LUT_4G[212])  # VSH=15V
        self.epd_w21_write_data(self.LUT_4G[213])  # VSL=-15V
        self.epd_w21_write_data(self.LUT_4G[214])  # VSHR

        # Booster Soft Start
        self.epd_w21_write_cmd(0x06)
        self.epd_w21_write_data(0xD7)  # D7
        self.epd_w21_write_data(0xD7)  # D7
        self.epd_w21_write_data(0x27)  # 2F

        # PLL Control - Frame Rate
        self.epd_w21_write_cmd(0x30)
        self.epd_w21_write_data(self.LUT_4G[210])  # PLL

        # CDI Setting
        self.epd_w21_write_cmd(0x50)
        self.epd_w21_write_data(0x57)

        # TCON Setting
        self.epd_w21_write_cmd(0x60)
        self.epd_w21_write_data(0x22)

        # Resolution Setting
        self.epd_w21_write_cmd(0x61)
        self.epd_w21_write_data(0xF0)  # HRES[7:3] - 240
        self.epd_w21_write_data(0x01)  # VRES[15:8] - 320
        self.epd_w21_write_data(0xA0)  # VRES[7:0]

        self.epd_w21_write_cmd(0x65)
        # Additional resolution setting, if needed
        self.epd_w21_write_data(0x00)

        # VCOM_DC Setting
        self.epd_w21_write_cmd(0x82)
        self.epd_w21_write_data(self.LUT_4G[215])  # -2.0V

        # Power Saving Register
        self.epd_w21_write_cmd(0xE3)
        self.epd_w21_write_data(0x88)  # VCOM_W[3:0], SD_W[3:0]

        # LUT Setting
        self.write_4g_lut()

        # Power ON
        self.epd_w21_write_cmd(0x04)
        self.lcd_chkstatus()  # Check if the display is ready

    def pic_display_4g(self, datas: List[int]) -> None:
        """Display 4-gray image using async SPI communication."""
        # Ensure datas is a flat list of 24960 bytes
        if len(datas) != 24960:
            raise ValueError("datas must be a flat list of 24960 integers")

        # Convert to NumPy array and reshape to (12480, 2)
        datas_np = np.array(datas, dtype=np.uint8).reshape(12480, 2)
        byte0, byte1 = datas_np[:, 0], datas_np[:, 1]

        # Vectorized packing for MSBs (0x10)
        packed_msbs = np.zeros(12480, dtype=np.uint8)
        for bit, shift in [(7, 7), (5, 6), (3, 5), (1, 4)]:
            packed_msbs |= ((byte0 >> bit) & 1) << shift
            packed_msbs |= ((byte1 >> bit) & 1) << (shift - 4)

        # Vectorized packing for LSBs (0x13)
        packed_lsbs = np.zeros(12480, dtype=np.uint8)
        for bit, shift in [(6, 7), (4, 6), (2, 5), (0, 4)]:
            packed_lsbs |= ((byte0 >> bit) & 1) << shift
            packed_lsbs |= ((byte1 >> bit) & 1) << (shift - 4)

        # Queue the display sequence for async execution
        def display_sequence():
            # Send old data (0x10)
            self.epd_w21_write_cmd(0x10)
            lgpio.gpio_write(self.lgpio_handle, self.DC_PIN, 1)  # Data mode

        self.queue_command(display_sequence)
        self.safe_writebytes(packed_msbs.tolist())

        def display_sequence2():
            # Send new data (0x13)
            self.epd_w21_write_cmd(0x13)
            lgpio.gpio_write(self.lgpio_handle, self.DC_PIN, 1)  # Data mode

        self.queue_command(display_sequence2)
        self.safe_writebytes(packed_lsbs.tolist())

        def refresh_sequence():
            # Refresh command
            self.epd_w21_write_cmd(0x12)
            self.delay_xms(1)  # Necessary delay for the display refresh
            self.lcd_chkstatus()  # Check the display status

        self.queue_command(refresh_sequence)

    def pic_display(self, new_data: List[int]) -> None:
        """Display new data using async SPI communication.

        Args:
            new_data: Flat list of 12480 integers representing pixel data
        """
        if len(new_data) != 12480:
            raise ValueError("new_data must be a flat list of 12480 integers")

        # Queue the display sequence for async execution
        def display_sequence():
            # Transfer old data
            self.epd_w21_write_cmd(0x10)
            lgpio.gpio_write(self.lgpio_handle, self.DC_PIN, 1)  # Data mode

        self.queue_command(display_sequence)
        self.safe_writebytes(self.oldData)

        def display_sequence2():
            # Transfer new data
            self.epd_w21_write_cmd(0x13)
            lgpio.gpio_write(self.lgpio_handle, self.DC_PIN, 1)  # Data mode

        self.queue_command(display_sequence2)
        self.safe_writebytes(new_data)

        # Update old data for next frame
        self.oldData = list(new_data)

        def refresh_sequence():
            # Refresh display
            self.epd_w21_write_cmd(0x12)
            self.delay_xms(1)  # Necessary delay for the display refresh
            self.lcd_chkstatus()  # Check if the display is ready

        self.queue_command(refresh_sequence)

    def epd_lut(self):
        self.epd_w21_write_cmd(0x20)  # 写入VCOM LUT
        for value in self.lut_vcom:
            self.epd_w21_write_data(value)

        self.epd_w21_write_cmd(0x21)  # 写入WW LUT
        for value in self.lut_ww:
            self.epd_w21_write_data(value)

        self.epd_w21_write_cmd(0x22)  # 写入BW LUT
        for value in self.lut_bw:
            self.epd_w21_write_data(value)

        self.epd_w21_write_cmd(0x23)  # 写入WB LUT
        for value in self.lut_wb:
            self.epd_w21_write_data(value)

        self.epd_w21_write_cmd(0x24)  # 写入BB LUT
        for value in self.lut_bb:
            self.epd_w21_write_data(value)

    def epd_init_lut(self):
        lgpio.gpio_write(self.lgpio_handle, self.RST_PIN, 0)
        self.delay_xms(10)
        lgpio.gpio_write(self.lgpio_handle, self.RST_PIN, 1)
        self.delay_xms(10)

        self.epd_w21_write_cmd(0x04)  # 开启电源
        self.lcd_chkstatus()  # 等待屏幕空闲

        self.epd_w21_write_cmd(0x00)  # 面板设置
        self.epd_w21_write_data(0xF7)

        self.epd_w21_write_cmd(0x09)  # 取消波形默认设置

        self.epd_w21_write_cmd(0x01)  # 电源设置
        self.epd_w21_write_data(0x03)
        self.epd_w21_write_data(0x10)
        self.epd_w21_write_data(0x3F)
        self.epd_w21_write_data(0x3F)
        self.epd_w21_write_data(0x3F)

        self.epd_w21_write_cmd(0x06)  # Booster soft start设置
        self.epd_w21_write_data(0xD7)
        self.epd_w21_write_data(0xD7)
        self.epd_w21_write_data(0x33)

        self.epd_w21_write_cmd(0x30)  # PLL控制（频率设置）
        self.epd_w21_write_data(0x09)

        self.epd_w21_write_cmd(0x50)  # VCOM和数据间隔设置
        self.epd_w21_write_data(0xD7)

        self.epd_w21_write_cmd(0x61)  # 分辨率设置
        self.epd_w21_write_data(0xF0)  # 水平方向分辨率（HRES）
        self.epd_w21_write_data(0x01)  # 垂直方向分辨率高8位
        self.epd_w21_write_data(0xA0)  # 垂直方向分辨率低8位

        self.epd_w21_write_cmd(0x2A)  # Gate/Source起始位置设置
        self.epd_w21_write_data(0x80)
        self.epd_w21_write_data(0x00)
        self.epd_w21_write_data(0x00)
        self.epd_w21_write_data(0xFF)
        self.epd_w21_write_data(0x00)

        self.epd_w21_write_cmd(0x82)  # VCOM直流电压设置
        self.epd_w21_write_data(0x0F)

        self.epd_lut()  # 写入LUT波形表

    def pic_display_clear(self, poweroff: bool = False) -> None:
        """Clear the display using async SPI communication."""

        # Queue the clear sequence for async execution
        def clear_sequence():
            # Transfer old data
            self.epd_w21_write_cmd(0x10)
            lgpio.gpio_write(self.lgpio_handle, self.DC_PIN, 1)  # Data mode

        self.queue_command(clear_sequence)
        self.safe_writebytes(self.oldData)

        def clear_sequence2():
            # Transfer new data, setting all to 0x00 (white or clear)
            self.epd_w21_write_cmd(0x13)
            lgpio.gpio_write(self.lgpio_handle, self.DC_PIN, 1)  # Data mode

        self.queue_command(clear_sequence2)
        self.safe_writebytes([0] * 12480)

        # Update old data
        self.oldData = [0] * 12480

        def refresh_and_poweroff_sequence():
            # Refresh the display
            self.epd_w21_write_cmd(0x12)
            self.delay_xms(1)  # Ensure a small delay for the display to process
            self.lcd_chkstatus()  # Check the display status

            if poweroff:
                self.epd_sleep()  # Power off the display

        self.queue_command(refresh_and_poweroff_sequence)
