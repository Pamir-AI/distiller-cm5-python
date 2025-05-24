import logging
import sys
from typing import Optional, IO
from distiller_cm5_python.utils.config import LOGGING_LEVEL

# Define the standard log format
DEFAULT_LOG_FORMAT = (
    "%(asctime)s - %(name)s - %(module)s.%(funcName)s - %(levelname)s - %(message)s"
)


def setup_logging(log_level: int = LOGGING_LEVEL, stream: IO = sys.stdout):
    """Setup root logging configuration.

    Args:
        log_level: The logging level to use (e.g., logging.DEBUG, logging.INFO).
                   Defaults to LOGGING_LEVEL.
        stream: The output stream to use (e.g., sys.stdout, sys.stderr).
                Defaults to sys.stdout.
    """
    # Create a formatter
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)

    # Setup stream handler
    stream_handler = logging.StreamHandler(stream)
    stream_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates if setup_logging is called multiple times
    # (though it should ideally be called only once at the application start)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add our handler
    root_logger.addHandler(stream_handler)

    # Optionally quiet overly verbose libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("qasync").setLevel(logging.WARNING)

    return root_logger


# # Create a default logger instance that can be imported by other modules
# # This maintains backward compatibility with code that expects to import logger directly
# logger = logging.getLogger('distiller_cm5_python')
# logger.setLevel(LOGGING_LEVEL)
#
# # Ensure the logger has at least one handler if not already configured
# if not logger.handlers:
#     # Create a formatter
#     formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
#
#     # Setup stream handler
#     stream_handler = logging.StreamHandler(sys.stdout)
#     stream_handler.setFormatter(formatter)
#
#     # Add our handler
#     logger.addHandler(stream_handler)

# Example usage in other modules:
# from distiller_cm5_python.utils.logger import logger
# logger.info("This is an info message")
# logger.error("This is an error message")

# For configuring the root logger, modules can still use setup_logging:
# from distiller_cm5_python.utils.logger import setup_logging
# setup_logging(log_level=logging.INFO, stream=sys.stderr)
