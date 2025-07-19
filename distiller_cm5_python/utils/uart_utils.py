"""
Utility module for UART communication with Pamir hardware.
This module handles sending status signals via UART to indicate application state.
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

UART_DEVICE = "/dev/pamir-sam"

def send_power_status(status: int) -> bool:
    """
    Send power status to the UART device.
    
    Args:
        status: 1 for application startup, 0 for application shutdown
        
    Returns:
        bool: True if successful, False otherwise
    """
    message = {
        "Function": "SOM_POWER_STATUS",
        "value": status
    }
    
    try:
        # Convert message to JSON string
        json_data = json.dumps(message)
        
        # Check if the UART device exists
        if not os.path.exists(UART_DEVICE):
            logger.warning(f"UART device {UART_DEVICE} not found, skipping power status signal")
            return False
            
        # Open the UART device and write the JSON message
        with open(UART_DEVICE, "w") as uart:
            uart.write(json_data)
            logger.info(f"Sent power status {status} to UART device")
        return True
    except Exception as e:
        logger.error(f"Error sending power status to UART: {e}")
        return False
        
def signal_app_start() -> bool:
    """Signal that the application is starting."""
    return send_power_status(1)
    
def signal_app_shutdown() -> bool:
    """Signal that the application is shutting down."""
    return send_power_status(0) 