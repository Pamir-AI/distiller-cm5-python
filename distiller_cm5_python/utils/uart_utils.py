"""
UART communication utilities for the Pamir AI SAM (Signal Aggregation Module) protocol.

This module implements the SAM UART Protocol for communication between
the CM5 host and RP2040 microcontroller. The protocol uses 4-byte packets with
CRC8 error detection for reliable hardware control.
"""

import os
import struct
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

UART_DEVICE = "/dev/pamir-sam"

# Protocol constants
PACKET_SIZE = 4

# Message type masks (bits 7-5)
TYPE_BUTTON = 0x00  # 0b000xxxxx
TYPE_LED = 0x20  # 0b001xxxxx
TYPE_POWER = 0x40  # 0b010xxxxx
TYPE_DISPLAY = 0x60  # 0b011xxxxx
TYPE_DEBUG_CODE = 0x80  # 0b100xxxxx
TYPE_DEBUG_TEXT = 0xA0  # 0b101xxxxx
TYPE_SYSTEM = 0xC0  # 0b110xxxxx
TYPE_EXTENDED = 0xE0  # 0b111xxxxx

# Power command definitions
POWER_CMD_QUERY = 0x00
POWER_CMD_SET = 0x01
POWER_CMD_SLEEP = 0x02
POWER_CMD_SHUTDOWN = 0x03
POWER_CMD_REQUEST_METRICS = 0x0F

# Power states
POWER_STATE_OFF = 0x00
POWER_STATE_RUNNING = 0x01
POWER_STATE_SUSPEND = 0x02
POWER_STATE_SLEEP = 0x03

# Button masks for BTN_POWER
BUTTON_UP = 0x01
BUTTON_DOWN = 0x02
BUTTON_SELECT = 0x04
BUTTON_POWER = 0x08


def calculate_crc8(data: bytes) -> int:
    """
    Calculate CRC8 checksum using polynomial 0x07.

    Args:
        data: Bytes to calculate CRC for

    Returns:
        CRC8 checksum value
    """
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x07
            else:
                crc <<= 1
            crc &= 0xFF
    return crc


def create_packet(type_flags: int, data0: int, data1: int) -> bytes:
    """
    Create a SAM protocol packet with CRC8 checksum.

    Args:
        type_flags: Message type and flags byte
        data0: First data byte
        data1: Second data byte

    Returns:
        4-byte packet with checksum
    """
    packet_data = bytes([type_flags, data0, data1])
    checksum = calculate_crc8(packet_data)
    return packet_data + bytes([checksum])


def validate_packet(packet: bytes) -> bool:
    """
    Validate a SAM protocol packet checksum.

    Args:
        packet: 4-byte packet to validate

    Returns:
        True if checksum is valid, False otherwise
    """
    if len(packet) != PACKET_SIZE:
        return False

    calculated_crc = calculate_crc8(packet[:3])
    return calculated_crc == packet[3]


def parse_packet(packet: bytes) -> Optional[Tuple[int, int, int]]:
    """
    Parse and validate a SAM protocol packet.

    Args:
        packet: 4-byte packet to parse

    Returns:
        Tuple of (type_flags, data0, data1) if valid, None otherwise
    """
    if not validate_packet(packet):
        logger.error("Invalid packet checksum")
        return None

    return struct.unpack("BBB", packet[:3])


def send_packet(packet: bytes) -> bool:
    """
    Send a SAM protocol packet to the UART device.

    Args:
        packet: 4-byte packet to send

    Returns:
        True if successful, False otherwise
    """
    try:
        if not os.path.exists(UART_DEVICE):
            logger.warning(f"UART device {UART_DEVICE} not found")
            return False

        with open(UART_DEVICE, "wb") as uart:
            uart.write(packet)
            logger.debug(f"Sent packet: {packet.hex()}")
        return True

    except Exception as e:
        logger.error(f"Error sending packet to UART: {e}")
        return False


def send_power_status(status: int) -> bool:
    """
    Send power status using the new SAM protocol.

    Args:
        status: 1 for application startup, 0 for application shutdown

    Returns:
        True if successful, False otherwise
    """
    power_state = POWER_STATE_RUNNING if status else POWER_STATE_OFF
    packet = create_packet(
        TYPE_POWER | POWER_CMD_SET, power_state, 0x00  # Flags (reserved)
    )

    success = send_packet(packet)
    if success:
        logger.info(f"Sent power state {power_state} to SAM")
    return success


def send_btn_power_packet() -> bool:
    """
    Send BTN_POWER packet for system shutdown.

    This sends a button press event for the POWER button to trigger
    coordinated system shutdown through the SAM protocol.

    Returns:
        True if successful, False otherwise
    """
    packet = create_packet(
        TYPE_BUTTON | BUTTON_POWER, 0x00, 0x00  # Reserved  # Reserved
    )

    success = send_packet(packet)
    if success:
        logger.info("Sent BTN_POWER packet for shutdown")
    return success


def send_shutdown_notification(reason_code: int = 0x05) -> bool:
    """
    Send shutdown notification to SAM before system poweroff.

    Args:
        reason_code: Reason for shutdown (0x05 = user initiated)

    Returns:
        True if successful, False otherwise
    """
    packet = create_packet(
        TYPE_POWER | POWER_CMD_SHUTDOWN,
        0x00,  # Normal shutdown (0x01 = emergency, 0x02 = reboot)
        reason_code,  # Reason code
    )

    success = send_packet(packet)
    if success:
        logger.info(f"Sent shutdown notification with reason {reason_code}")
    return success


def request_power_metrics() -> bool:
    """
    Request all power metrics from SAM.

    Returns:
        True if successful, False otherwise
    """
    packet = create_packet(
        TYPE_POWER | POWER_CMD_REQUEST_METRICS,
        0x00,  # Metric mask (0x00 = all metrics)
        0x00,  # Reserved
    )

    success = send_packet(packet)
    if success:
        logger.debug("Requested power metrics from SAM")
    return success


def send_display_release() -> bool:
    """
    Send display release command during boot handover.

    Returns:
        True if successful, False otherwise
    """
    DISPLAY_CMD_RELEASE = 0x07
    packet = create_packet(
        TYPE_DISPLAY | DISPLAY_CMD_RELEASE,
        0xFF,  # Release signal (special value)
        0x00,  # Flags (reserved)
    )

    success = send_packet(packet)
    if success:
        logger.info("Sent display release command to SAM")
    return success


def signal_app_start() -> bool:
    """Signal that the application is starting."""
    return send_power_status(1)


def signal_app_shutdown() -> bool:
    # """Signal that the application is shutting down."""
    # success = send_power_status(0)
    # if not success:
    #     logger.error("Failed to send power status during shutdown")
    #     return False

    # # Also send shutdown notification
    # send_shutdown_notification()

    # success = send_btn_power_packet()
    # if not success:
    #     logger.error("Failed to send BTN_POWER packet during shutdown")
    #     return False
    # return success
    return 0
