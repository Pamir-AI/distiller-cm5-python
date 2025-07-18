from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication
import threading
import logging
import errno
import select
import sys 

# Only import evdev on Linux
if sys.platform == 'linux':
    import evdev
else:
    # Define a dummy evdev or raise an error if needed on other platforms
    # For now, we'll assume it's only used on Linux where InputMonitor is active
    evdev = None

# Setup Logging
logger = logging.getLogger(__name__)


class InputMonitor(QObject):
    """
    Handles monitoring of hardware input devices and converting their events to Qt key events.
    This class is responsible for detecting keypresses from physical buttons and forwarding them
    to the Qt application.
    """

    def __init__(self, target_window=None):
        """
        Initialize the InputMonitor.

        Args:
            target_window: The Qt window to send key events to
        """
        QObject.__init__(self)
        self.target_window = target_window
        self._input_device_path = (
            "/dev/input/event2"  # Default, will be dynamically found
        )
        self._input_thread = None
        self._stop_input_thread = threading.Event()

    def set_target_window(self, window):
        """Set the target window that will receive key events."""
        self.target_window = window

    def _find_input_device_path(self, device_name: str) -> str | None:
        """
        Find the event device path for a given device name.

        Args:
            device_name: The name of the input device to find

        Returns:
            The device path or None if not found
        """
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for device in devices:
            logger.debug(f"Checking device: {device.path}, Name: {device.name}")
            if device.name == device_name:
                logger.info(f"Found device '{device_name}' at path: {device.path}")
                return device.path

        logger.warning(f"Could not find input device with name: '{device_name}'")
        return None

    def start(self, device_name="Pamir AI Signal Aggregation Module"):
        """
        Finds the input device and starts the monitoring thread.

        Args:
            device_name: The name of the input device to monitor
        """
        if self._input_thread and self._input_thread.is_alive():
            logger.warning("Input monitor thread already running.")
            return

        # Find the device path dynamically
        device_path = self._find_input_device_path(device_name)

        if not device_path:
            logger.error(
                f"Failed to find input device '{device_name}'. Cannot start monitor."
            )
            return

        if not self.target_window:
            logger.error("No target window set. Cannot start monitor.")
            return

        self._stop_input_thread.clear()
        self._input_thread = threading.Thread(
            target=self._monitor_input_device,
            args=(device_path, self.target_window),  # Pass the found path
            daemon=True,  # Allow app to exit even if this thread is stuck
        )
        self._input_thread.start()
        logger.info(f"Started input device monitor thread for {device_path}")

    def _monitor_input_device(self, device_path, target_window):
        """
        Monitors the specified input device and posts key events to the target window.

        Args:
            device_path: The path to the input device
            target_window: The Qt window to send key events to
        """
        dev = None
        try:
            logger.info(f"Attempting to open input device: {device_path}")
            dev = evdev.InputDevice(device_path)
            # dev.grab()  # Grab the device to prevent events going elsewhere
            logger.info(f"Successfully opened input device: {dev.name}")

            key_map = {
                evdev.ecodes.KEY_UP: Qt.Key.Key_Up,
                evdev.ecodes.KEY_DOWN: Qt.Key.Key_Down,
                evdev.ecodes.KEY_ENTER: Qt.Key.Key_Enter,  # Or Qt.Key_Return if needed
            }

            logger.info("Starting event read loop...")
            while not self._stop_input_thread.is_set():
                # Use blocking read with a timeout to allow checking the stop flag
                # Use standard select module on the device's file descriptor
                try:
                    r, w, x = select.select([dev.fd], [], [], 0.1)  # 100ms timeout
                except select.error as e:
                    # Handle interrupted system call, e.g., by signals
                    if e.args[0] == errno.EINTR:
                        continue
                    else:
                        logger.error(
                            f"Select error on input device {device_path}: {e}",
                            exc_info=True,
                        )
                        break  # Exit loop on other select errors

                if not r:  # Timeout occurred, check stop flag and continue
                    continue

                # Check if the file descriptor is the one we are waiting for
                if dev.fd in r:
                    try:
                        for event in dev.read():  # Read available events
                            if event.type == evdev.ecodes.EV_KEY:
                                # Only process key down events (value=1) for simplicity
                                if event.value == 1:  # Key press
                                    qt_key = key_map.get(event.code)
                                    if qt_key and target_window:
                                        logger.debug(
                                            f"Input Event: Code={event.code}, Mapped Qt Key={qt_key}"
                                        )
                                        press_event = QKeyEvent(
                                            QKeyEvent.Type.KeyPress,
                                            qt_key,
                                            Qt.KeyboardModifier.NoModifier,
                                        )
                                        QApplication.postEvent(
                                            target_window, press_event
                                        )
                                        logger.debug(
                                            f"Posted KeyPress {qt_key} to {target_window}"
                                        )
                    except BlockingIOError:
                        # This can happen if select() returns but read() has no data yet
                        continue
                    except OSError as e:
                        if e.errno == errno.ENODEV:
                            logger.error(
                                f"Input device {device_path} disconnected. Stopping monitor."
                            )
                            break  # Exit the loop if device disconnects
                        else:
                            logger.error(
                                f"Error reading from input device {device_path}: {e}",
                                exc_info=True,
                            )
                            # Optionally add a delay before retrying
                            self._stop_input_thread.wait(1.0)
                    except Exception as e:
                        logger.error(
                            f"Unexpected error in input monitor loop: {e}",
                            exc_info=True,
                        )
                        # Add a delay before retrying to avoid tight loops on errors
                        self._stop_input_thread.wait(1.0)

        except FileNotFoundError:
            logger.error(f"Input device not found: {device_path}")
        except PermissionError:
            logger.error(
                f"Permission denied for input device: {device_path}. Ensure user is in 'input' group."
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize or monitor input device {device_path}: {e}",
                exc_info=True,
            )
        finally:
            if dev:
                try:
                    # dev.ungrab()  # Release the device if it was grabbed
                    dev.close()
                    logger.info(f"Closed input device: {device_path}")
                except Exception as e:
                    logger.error(f"Error closing input device {device_path}: {e}")
            logger.info("Input device monitor thread finished.")

    def stop(self):
        """Signals the input monitoring thread to stop and waits for it."""
        if self._input_thread and self._input_thread.is_alive():
            logger.info("Stopping input device monitor thread...")
            self._stop_input_thread.set()
            try:
                # Wait for the thread to finish, with a timeout
                self._input_thread.join(timeout=1.0)
                if self._input_thread.is_alive():
                    logger.warning(
                        "Input monitor thread did not stop gracefully within timeout."
                    )
                else:
                    logger.info("Input monitor thread stopped.")
            except Exception as e:
                logger.error(f"Error stopping input monitor thread: {e}", exc_info=True)
        self._input_thread = None
        self._stop_input_thread.clear()  # Reset event for potential restarts
