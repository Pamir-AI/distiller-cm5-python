import time
import spidev
import platform
import os
from typing import List
import numpy as np
from threading import Thread
import logging

logger = logging.getLogger(__name__)

# Check if we're on a Rockchip platform
_ROCK = "rockchip" in platform.release()

# Check if we're on Raspberry Pi - this works on Pi 5 which might not identify as 'raspberry'
_RPI = (not _ROCK) and (
    os.path.exists("/proc/device-tree/model")
    and "raspberry" in open("/proc/device-tree/model", "r").read().lower()
    or os.path.exists("/sys/firmware/devicetree/base/model")
    and "raspberry" in open("/sys/firmware/devicetree/base/model", "r").read().lower()
)

if _RPI:
    import lgpio
elif _ROCK:
    from gpiod.line import Direction, Value, Bias
    from .rock_gpio import RockGPIO


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
        0x01,0x0a,0x0a,0x0a,0x0a,0x01,0x01,
        0x02,0x0f,0x01,0x0f,0x01,0x01,0x01,
        0x01,0x0a,0x00,0x0a,0x00,0x01,0x01,
        0x01,0x00,0x00,0x00,0x00,0x01,0x01,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,				
        ];

        self.lut_ww = [
        0x01,0x4a,0x4a,0x0a,0x0a,0x01,0x01,
        0x02,0x8f,0x01,0x4f,0x01,0x01,0x01,
        0x01,0x8a,0x00,0x8a,0x00,0x01,0x01,
        0x01,0x80,0x00,0x80,0x00,0x01,0x01,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        ];

        self.lut_bw = [
        0x01,0x4a,0x4a,0x0a,0x0a,0x01,0x01,
        0x02,0x8f,0x01,0x4f,0x01,0x01,0x01,
        0x01,0x8a,0x00,0x8a,0x00,0x01,0x01,
        0x01,0x80,0x00,0x80,0x00,0x01,0x01,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        ];

        self.lut_wb = [
        0x01,0x0a,0x0a,0x8a,0x8a,0x01,0x01,
        0x02,0x8f,0x01,0x4f,0x01,0x01,0x01,
        0x01,0x4a,0x00,0x4a,0x00,0x01,0x01,
        0x01,0x40,0x00,0x40,0x00,0x01,0x01,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        ];

        self.lut_bb = [
        0x01,0x0a,0x0a,0x8a,0x8a,0x01,0x01,
        0x02,0x8f,0x01,0x4f,0x01,0x01,0x01,
        0x01,0x4a,0x00,0x4a,0x00,0x01,0x01,
        0x01,0x40,0x00,0x40,0x00,0x01,0x01,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        ];

        # Pin Def
        if _ROCK:
            self.RK_DC_PIN = "GPIO1_C6"
            self.RK_RST_PIN = "GPIO1_B1"
            self.RK_BUSY_PIN = "GPIO0_D3"
        else:
            self.DC_PIN = 7
            self.RST_PIN = 13
            self.BUSY_PIN = 9

        self.EPD_WIDTH = 240
        self.EPD_HEIGHT = 416

        if _ROCK:
            self.RockGPIO = RockGPIO()
        else:
            # Initialize lgpio
            self.chip = 0  # Default gpiochip number, adjust if needed
            self.lgpio_handle = lgpio.gpiochip_open(self.chip)

        self.spi = self.EPD_GPIO_Init()
        self.epd_w21_init_4g()
        self._write_thread = None

    def safe_writebytes(self, data, chunk_size=4096):
        if self._write_thread and self._write_thread.is_alive():
            return
        self._write_thread = Thread(target=self._write_chunks, args=(data, chunk_size))
        self._write_thread.start()

    def _write_chunks(self, data, chunk_size):
        data_np = np.array(data, dtype=np.uint8)
        for i in range(0, len(data), chunk_size):
            try:
                self.spi.writebytes(data_np[i : i + chunk_size].tolist())
            except Exception as e:
                logger.error(f"SPI write error at offset {i}: {e}")
                raise

    def cleanup(self) -> None:
        if _ROCK:
            self.RockGPIO.cleanup()
        elif hasattr(self, "lgpio_handle"):
            lgpio.gpiochip_close(self.lgpio_handle)

    def EPD_GPIO_Init(self) -> spidev.SpiDev:
        if _RPI:
            # Configure GPIO pins with lgpio
            lgpio.gpio_claim_output(self.lgpio_handle, self.DC_PIN, 0)
            lgpio.gpio_claim_output(self.lgpio_handle, self.RST_PIN, 0)
            # For input with pull-up, flags=1 means pull-up
            lgpio.gpio_claim_input(self.lgpio_handle, self.BUSY_PIN, lgpio.SET_PULL_UP)
        else:
            self.RockGPIO.setup(self.RK_DC_PIN, Direction.OUTPUT)
            self.RockGPIO.setup(self.RK_RST_PIN, Direction.OUTPUT)
            self.RockGPIO.setup(self.RK_BUSY_PIN, Direction.INPUT, bias=Bias.PULL_UP)

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
        if _ROCK:
            self.RockGPIO.output(self.RK_DC_PIN, Value.INACTIVE)  # Data mode
        else:
            lgpio.gpio_write(self.lgpio_handle, self.DC_PIN, 0)  # Low for command
        self.SPI_Write(command)

    def epd_w21_write_data(self, data: int) -> None:
        self.SPI_Delay()
        if _ROCK:
            self.RockGPIO.output(self.RK_DC_PIN, Value.ACTIVE)  # Data mode
        else:
            lgpio.gpio_write(self.lgpio_handle, self.DC_PIN, 1)  # High for data
        self.SPI_Write(data)

    def delay_xms(self, xms: int) -> None:
        time.sleep(xms / 1000.0)

    def epd_w21_init(self) -> None:
        self.delay_xms(100)
        if _ROCK:
            self.RockGPIO.output(self.RK_RST_PIN, Value.INACTIVE)
            self.delay_xms(20)
            self.RockGPIO.output(self.RK_RST_PIN, Value.ACTIVE)
            self.delay_xms(20)
        else:
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
        if _ROCK:
            # Assuming LOW means busy
            while self.RockGPIO.input(self.RK_BUSY_PIN) == Value.INACTIVE:
                time.sleep(0.01)
        else:
            # For lgpio, 0 means low which indicates busy
            while lgpio.gpio_read(self.lgpio_handle, self.BUSY_PIN) == 0:
                time.sleep(0.01)  # Wait 10ms before checking again

    def epd_sleep(self) -> None:
        self.epd_w21_write_cmd(0x02)  # Power off
        self.lcd_chkstatus()  # Implement this to check the display's busy status

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
        # Display 4-gray image on the e-ink display
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

        # Send old data (0x10)
        self.epd_w21_write_cmd(0x10)
        if _ROCK:
            self.RockGPIO.output(self.RK_DC_PIN, Value.ACTIVE)
        else:
            lgpio.gpio_write(self.lgpio_handle, self.DC_PIN, 1)  # Data mode
        self.safe_writebytes(packed_msbs.tolist())

        # Send new data (0x13)
        self.epd_w21_write_cmd(0x13)
        if _ROCK:
            self.RockGPIO.output(self.RK_DC_PIN, Value.ACTIVE)
        else:
            lgpio.gpio_write(self.lgpio_handle, self.DC_PIN, 1)  # Data mode
        self.safe_writebytes(packed_lsbs.tolist())

        # Refresh command
        self.epd_w21_write_cmd(0x12)
        self.delay_xms(1)  # Necessary delay for the display refresh
        self.lcd_chkstatus()  # Check the display status

    def pic_display(self, new_data: List[int]) -> None:
        """Display new data on the e-ink display

        Args:
            new_data: Flat list of 12480 integers representing pixel data
        """
        if len(new_data) != 12480:
            raise ValueError("new_data must be a flat list of 12480 integers")

        # Transfer old data
        self.epd_w21_write_cmd(0x10)
        if _ROCK:
            self.RockGPIO.output(self.RK_DC_PIN, Value.ACTIVE)
        else:
            lgpio.gpio_write(self.lgpio_handle, self.DC_PIN, 1)  # Data mode
        self.safe_writebytes(self.oldData)

        # Transfer new data
        self.epd_w21_write_cmd(0x13)
        if _ROCK:
            self.RockGPIO.output(self.RK_DC_PIN, Value.ACTIVE)
        else:
            lgpio.gpio_write(self.lgpio_handle, self.DC_PIN, 1)  # Data mode
        self.safe_writebytes(new_data)
        self.oldData = list(new_data)

        # Refresh display
        self.epd_w21_write_cmd(0x12)
        self.delay_xms(1)  # Necessary delay for the display refresh
        self.lcd_chkstatus()  # Check if the display is ready

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
        
        self.epd_w21_write_cmd(0x04)    # 开启电源
        self.lcd_chkstatus()            # 等待屏幕空闲
        
        self.epd_w21_write_cmd(0x00)    # 面板设置
        self.epd_w21_write_data(0xF7)
        
        self.epd_w21_write_cmd(0x09)    # 取消波形默认设置
        
        self.epd_w21_write_cmd(0x01)    # 电源设置
        self.epd_w21_write_data(0x03)
        self.epd_w21_write_data(0x10)
        self.epd_w21_write_data(0x3F)
        self.epd_w21_write_data(0x3F)
        self.epd_w21_write_data(0x3F)
        
        self.epd_w21_write_cmd(0x06)    # Booster soft start设置
        self.epd_w21_write_data(0xD7)
        self.epd_w21_write_data(0xD7)
        self.epd_w21_write_data(0x33)
        
        self.epd_w21_write_cmd(0x30)    # PLL控制（频率设置）
        self.epd_w21_write_data(0x09)
        
        self.epd_w21_write_cmd(0x50)    # VCOM和数据间隔设置
        self.epd_w21_write_data(0xD7)
        
        self.epd_w21_write_cmd(0x61)    # 分辨率设置
        self.epd_w21_write_data(0xF0)   # 水平方向分辨率（HRES）
        self.epd_w21_write_data(0x01)   # 垂直方向分辨率高8位
        self.epd_w21_write_data(0xA0)   # 垂直方向分辨率低8位

        self.epd_w21_write_cmd(0x2A)    # Gate/Source起始位置设置
        self.epd_w21_write_data(0x80)
        self.epd_w21_write_data(0x00)
        self.epd_w21_write_data(0x00)
        self.epd_w21_write_data(0xFF)
        self.epd_w21_write_data(0x00)

        self.epd_w21_write_cmd(0x82)    # VCOM直流电压设置
        self.epd_w21_write_data(0x0F)

        self.epd_lut()                  # 写入LUT波形表
    
    def pic_display_clear(self, poweroff: bool = False) -> None:
        # Clear the display by setting all pixels to white (0xFF)
        # Transfer old data
        self.epd_w21_write_cmd(0x10)
        if _ROCK:
            self.RockGPIO.output(self.RK_DC_PIN, Value.ACTIVE)
        else:
            lgpio.gpio_write(self.lgpio_handle, self.DC_PIN, 1)  # Data mode
        self.safe_writebytes(self.oldData)

        # Transfer new data, setting all to 0xFF (white or clear)
        self.epd_w21_write_cmd(0x13)
        if _ROCK:
            self.RockGPIO.output(self.RK_DC_PIN, Value.ACTIVE)
        else:
            lgpio.gpio_write(self.lgpio_handle, self.DC_PIN, 1)  # Data mode
        self.safe_writebytes([0] * 12480)
        self.oldData = [0] * 12480

        # Refresh the display
        self.epd_w21_write_cmd(0x12)
        self.delay_xms(1)  # Ensure a small delay for the display to process
        self.lcd_chkstatus()  # Check the display status

        if poweroff:
            self.power_off()  # Optionally power off the display after clearing
