import logging
import sys
from typing import Optional

def setup_logging(log_level=None, verbose=False):
    """Setup logging with specified log level
    
    Args:
        log_level: The logging level to use (e.g., logging.DEBUG, logging.INFO)
                  If None, defaults to DEBUG if verbose=True, otherwise INFO
        verbose: Backward compatibility parameter - if True and log_level is None, 
                sets level to DEBUG
    
    Returns:
        A configured logger instance
    """
    # Set default level based on parameters
    if log_level is None:
        log_level = logging.DEBUG if verbose else logging.INFO
    
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(module)s.%(funcName)s - %(levelname)s - %(message)s')
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our handler
    root_logger.addHandler(console_handler)
    
    # Get client logger
    logger = logging.getLogger("mcp")
    logger.setLevel(log_level)
    
    # Quiet other loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    return logger

# Initialize with default level, can be updated later
logger = setup_logging() 