# pyright: reportArgumentType=false
from PyQt6.QtCore import QUrl, QTimer, Qt, QObject, pyqtSignal, pyqtSlot
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QApplication
from contextlib import AsyncExitStack
import logging  # Import standard logging
import sys  # Import sys
from distiller_cm5_python.client.ui.display_config import config
from distiller_cm5_python.client.ui.AppInfoManager import AppInfoManager
from distiller_cm5_python.client.ui.bridge.MCPClientBridge import MCPClientBridge
from distiller_cm5_python.client.ui.InputMonitor import InputMonitor
from distiller_cm5_sdk.parakeet import Parakeet as asr_provider
from qasync import QEventLoop
import asyncio
import os
import signal
from concurrent.futures import ThreadPoolExecutor
import atexit


# --- Setup Logging EARLY ---
logger = logging.getLogger(__name__)


# quick display check
if not sys.platform.startswith("linux"):
    config["display"]["eink_enabled"] = False


if config["display"]["eink_enabled"]:
    from distiller_cm5_python.client.ui.bridge.EInkRenderer import EInkRenderer


class App(QObject):  # Inherit from QObject to support signals/slots
    # --- Signals ---
    transcriptionUpdate = pyqtSignal(str)
    transcriptionComplete = pyqtSignal(str)
    recordingStateChanged = pyqtSignal(bool)
    recordingError = pyqtSignal(str)  # New signal for errors
    # --- End Signals ---

    def __init__(self):
        QObject.__init__(self)
        """Initialize the Qt application and QML engine."""
        # Register a global exit handler at process exit
        atexit.register(self._emergency_exit_handler)

        # Set platform to offscreen before creating QApplication if E-Ink is enabled
        # TODO: Make this conditional based on configuration
        if config["display"]["eink_enabled"]:
            # Import E-Ink Renderer and Bridge
            os.environ["QT_QPA_PLATFORM"] = "offscreen"

        self.app = QApplication(sys.argv)
        self.app_info = AppInfoManager()
        self.app.setApplicationName(self.app_info._app_name)
        self.app.setOrganizationName(self.app_info._company_name)

        # Set up the event loop
        self.loop = QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)

        # For executing blocking operations
        self.executor = ThreadPoolExecutor(max_workers=3)

        # Create QML engine
        self.engine = QQmlApplicationEngine()

        # Create the MCP client bridge and app info manager
        self.bridge = MCPClientBridge()

        # E-Ink Initialization
        self.eink_renderer = None

        # Shutdown control
        self._shutdown_in_progress = False
        self._shutdown_timeout = 5000  # milliseconds
        self._shutdown_timer = QTimer(self.app)
        self._shutdown_timer.setSingleShot(True)
        self._shutdown_timer.timeout.connect(self._force_quit)

        # Exit stack for managed resource cleanup
        self.exit_stack = AsyncExitStack()

        self._eink_initialized = False

        # Connect signal to handle application quit
        self.app.aboutToQuit.connect(self._on_about_to_quit)

        # Set up signal handlers for graceful shutdown on system signals
        self._setup_signal_handlers()

        # --- ASR Initialization ---
        # TODO: Load model path/size from config if needed
        self.asr_provider = asr_provider(audio_config={"rate": 48000})
        self._is_actively_recording = False  # Separate state for UI feedback
        self._transcription_task = None
        # --- End ASR Initialization ---

        # Add main_window attribute initialization
        self.main_window = None

        # Create input monitor instance
        self.input_monitor = InputMonitor()

    async def initialize(self):
        """Initialize the application."""
        # Register the bridge object with QML
        root_context = self.engine.rootContext()
        if root_context is None:
            logger.error("Failed to get QML root context")
            raise RuntimeError("Failed to get QML root context")

        # Initialize the bridge first
        logger.info("Initializing bridge...")
        await self.bridge.initialize()

        # Set a reference to this App instance in the bridge
        self.bridge.set_app_instance(self)

        logger.info("Bridge initialized successfully")

        # Now register the initialized bridge with QML
        root_context.setContextProperty("bridge", self.bridge)
        root_context.setContextProperty("AppInfo", self.app_info)
        # Expose App instance to QML for signals/slots
        root_context.setContextProperty("AppController", self)

        # Set display dimensions from config
        self._set_display_dimensions()

        # Get the directory containing the QML files
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Set import paths for QML modules
        qml_path = os.path.join(current_dir)
        self.engine.addImportPath(qml_path)

        # Find the main.qml file
        qml_file = os.path.join(current_dir, "main.qml")

        if not os.path.exists(qml_file):
            logger.error(f"QML file not found: {qml_file}")
            raise FileNotFoundError(f"QML file not found: {qml_file}")

        # Make sure Qt can find its resources
        qt_conf_path = os.path.join(current_dir, "qt.conf")
        if not os.path.exists(qt_conf_path):
            # Create a minimal qt.conf if it doesn't exist
            with open(qt_conf_path, "w") as f:
                f.write("[Paths]\\nPrefix=.\\n")

        # Signal to QML that the bridge is ready
        self.bridge.setReady(True)

        # Load the QML file
        url = QUrl.fromLocalFile(qml_file)
        self.engine.load(url)

        # Wait for the QML to load
        await asyncio.sleep(0.1)

        # Check if the QML was loaded successfully and get the main window
        root_objects = self.engine.rootObjects()
        if not root_objects:
            logger.error("Failed to load QML or find root objects")
            raise RuntimeError("Failed to load QML")
        else:
            self.main_window = root_objects[0]  # Assign main_window HERE
            logger.info(f"QML loaded successfully. Main window: {self.main_window}")

        if config["display"]["eink_enabled"] and sys.platform.startswith("linux"):
            # Apply fixed size constraints to the root window after loading
            self._apply_window_constraints()
            # E-Ink Initialization Call
            success = self._init_eink_renderer()
            self._eink_initialized = success

            if success:
                # Add a small delay to allow QML/FocusManager to potentially settle
                await asyncio.sleep(0.2)  # Wait 200ms
                logger.info("Proceeding to start input monitor after short delay.")

                # Set the target window for the input monitor
                self.input_monitor.set_target_window(self.main_window)
                # Start the input monitor with default device name
                self.input_monitor.start()
            else:
                logger.warning("E-Ink initialization failed, continuing without E-Ink display")

        logger.info("Application initialized successfully")

    async def run(self):
        """Run the application with async event loop."""
        try:
            # Initialize the application
            await self.initialize()

            # Prepare exit stack for resource management
            await self.exit_stack.enter_async_context(
                self
            )  # Use this class as an async context manager

            # Run the event loop
            return self.loop.run_forever()

        except Exception as e:
            logger.error(f"Error running application: {e}", exc_info=True)
            await self._cleanup()
            return 1  # Return error code

    async def __aenter__(self):
        """Enter the async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager, ensuring cleanup."""
        await self._cleanup()
        return False  # Don't suppress exceptions

    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        for sig in (signal.SIGINT, signal.SIGTERM):
            self.loop.add_signal_handler(
                sig, lambda sig=sig: asyncio.create_task(self._handle_signal(sig))
            )

    async def _handle_signal(self, sig):
        """Handle system signal gracefully."""
        logger.info(f"Received signal {sig.name}, shutting down gracefully")
        await self._initiate_shutdown()

    def _on_about_to_quit(self):
        """Handle Qt's aboutToQuit signal."""
        # Force quit immediately - this is the most reliable approach
        os._exit(0)

    def _cleanup_eink(self):
        """Cleanup E-Ink resources."""
        try:
            if self.eink_renderer:
                self.eink_renderer.cleanup()
                logger.info("E-Ink renderer cleaned up.")
                self.eink_renderer = None

            self._eink_initialized = False
        except Exception as e:
            logger.error(f"Error during E-Ink cleanup: {e}", exc_info=True)
            self.eink_renderer = None

    async def _initiate_shutdown(self):
        """Initiate the shutdown sequence."""
        if self._shutdown_in_progress:
            logger.debug("Shutdown already in progress, ignoring additional request")
            return

        self._shutdown_in_progress = True
        logger.info("Initiating application shutdown")

        # Let the bridge know about the shutdown first
        try:
            if self.bridge:
                self.bridge.shutdown()

            # E-Ink Cleanup
            display_config = config.get("display")
            if display_config and display_config.get("eink_enabled"):
                self._cleanup_eink()

        except Exception as e:
            logger.error(f"Error during bridge shutdown notification: {e}", exc_info=True)

        # Start the full cleanup
        await self._cleanup()

        # Force application exit after cleanup
        # This is a guaranteed exit mechanism
        os._exit(0)

    async def _cleanup(self):
        """Clean up all resources."""
        if not hasattr(self, "loop") or not self.loop:
            return  # Already cleaned up or not initialized

        logger.info("Performing application cleanup")

        try:
            self.input_monitor.stop()

            # Clean up the bridge
            if self.bridge:
                try:
                    # Set a timeout for bridge cleanup
                    await asyncio.wait_for(self.bridge.cleanup(), timeout=3.0)
                except asyncio.TimeoutError:
                    logger.warning("Bridge cleanup timed out")
                except Exception as e:
                    logger.error(f"Error during bridge cleanup: {e}", exc_info=True)

            # Clean up E-Ink resources
            self._cleanup_eink()

            # Shut down the thread pool
            self.executor.shutdown(wait=False)

            # Cancel all running tasks
            tasks = [t for t in asyncio.all_tasks(self.loop) if t is not asyncio.current_task()]
            if tasks:
                logger.info(f"Cancelling {len(tasks)} pending tasks")
                for task in tasks:
                    task.cancel()

                # Wait for tasks to acknowledge cancellation
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True), timeout=2.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("Some tasks did not cancel in time")

        except Exception as e:
            logger.error(f"Error during application cleanup: {e}", exc_info=True)
        finally:
            # Make sure we stop the force quit timer if it's running
            if self._shutdown_timer.isActive():
                self._shutdown_timer.stop()

            # Exit the application properly
            if self.app:
                # Use the executor to call quit() to avoid potential deadlocks
                try:
                    asyncio.run_coroutine_threadsafe(
                        self.loop.run_in_executor(None, self.app.quit), self.loop
                    )
                except Exception:
                    # If that fails, try to quit directly
                    try:
                        self.app.quit()
                    except Exception as e:
                        logger.error(f"Error quitting application: {e}", exc_info=True)

            # Close the event loop if it exists and is open
            if self.loop and not self.loop.is_closed():
                try:
                    self.loop.close()
                except Exception as e:
                    logger.error(f"Error closing event loop: {e}", exc_info=True)

    def _force_quit(self):
        """Force quit the application if normal shutdown takes too long."""
        logger.warning("Shutdown timeout reached, forcing application to exit")
        # Try to do minimal cleanup
        try:
            self.executor.shutdown(wait=False)
        except Exception:
            pass

        # Force exit with no delay
        os._exit(0)

    def handle_quit(self):
        """Handle application quit signal."""
        logger.info("Application quit requested")
        # Stop the asyncio event loop when the Qt application quits
        if hasattr(self, "loop") and self.loop.is_running():
            self.loop.stop()

        # Clean up the E-Ink renderer if it exists
        display_config = config.get("display")
        if display_config and display_config.get("eink_enabled"):
            self._cleanup_eink()

        # Disconnect SAM
        if self.sam:
            self.sam.disconnect()
            self.sam = None

        # Schedule bridge shutdown
        try:
            self.bridge.shutdown()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)

    def _set_display_dimensions(self):
        """Set display dimensions from the config file as context properties for QML."""
        # Get width and height from config or use defaults
        display_config = config.get("display")
        width = int((display_config.get("width") if display_config else None) or 240)
        height = int((display_config.get("height") if display_config else None) or 416)

        # Set as context properties for QML
        rc = self.engine.rootContext()
        if rc:
            rc.setContextProperty("configWidth", width)
            rc.setContextProperty("configHeight", height)

        logger.info(f"Set display dimensions from config: {width}x{height}")

    def _apply_window_constraints(self):
        """Apply fixed size constraints to the main window after QML is loaded."""
        # Get display dimensions from config
        display_config = config.get("display")
        width = int((display_config.get("width") if display_config else None) or 240)
        height = int((display_config.get("height") if display_config else None) or 416)

        # Find the root window object - use self.main_window if already assigned
        main_window = self.main_window
        if not main_window:
            root_objects = self.engine.rootObjects()
            if not root_objects:
                logger.error("No root objects found to apply size constraints")
                return
            main_window = root_objects[0]  # Assign here if not already done

        if not main_window:
            logger.error("Main window object is still None, cannot apply constraints")
            return

        try:
            # Set fixed size - use QML properties for ApplicationWindow
            main_window.setProperty("width", width)
            main_window.setProperty("height", height)

            # These may or may not be available, depending on the window type
            try:
                main_window.setProperty("minimumWidth", width)
                main_window.setProperty("maximumWidth", width)
                main_window.setProperty("minimumHeight", height)
                main_window.setProperty("maximumHeight", height)

                # For ApplicationWindow, we set the flag in QML directly
                # So we don't need to do main_window.setFlags() here
            except Exception as e:
                logger.warning(f"Could not set all window constraints: {e}")

            logger.info(f"Applied fixed size constraints: {width}x{height}")
        except Exception as e:
            logger.error(f"Error applying window constraints: {e}", exc_info=True)

    # E-Ink Methods
    def _init_eink_renderer(self):
        """Initialize the simplified E-Ink renderer."""
        display_config = config.get("display")
        if not (display_config and display_config.get("eink_enabled")):
            logger.warning("E-Ink display mode disabled in configuration")
            return False

        logger.info("E-Ink display mode enabled")

        try:
            # Import EInkRenderer dynamically to avoid unbound variable issues
            from distiller_cm5_python.client.ui.bridge.EInkRenderer import EInkRenderer
            
            # Create the E-Ink renderer
            self.eink_renderer = EInkRenderer(parent=self.app)

            # Initialize the hardware
            if not self.eink_renderer.initialize():
                logger.error("Failed to initialize E-Ink renderer")
                self.eink_renderer = None
                return False

            # Set the target window for rendering
            if self.main_window:
                self.eink_renderer.set_target_window(self.main_window)
            else:
                logger.warning("Main window not available for E-Ink rendering")

            # Start rendering
            if not self.eink_renderer.start():
                logger.error("Failed to start E-Ink renderer")
                self.eink_renderer.cleanup()
                self.eink_renderer = None
                return False

            # Register the renderer with the bridge for text streaming notifications
            if hasattr(self.bridge, "set_eink_renderer"):
                self.bridge.set_eink_renderer(self.eink_renderer)

            # Get config for logging
            capture_interval = config["display"]["eink_refresh_interval"]
            adaptive_capture = config["display"]["eink_adaptive_capture"]
            threshold = config["display"]["eink_threshold"]
            gamma_value = config["display"]["eink_bw_conversion"]["gamma_value"]

            logger.info(
                f"EInkRenderer initialized with {capture_interval}ms interval, "
                f"adaptive_capture={'enabled' if adaptive_capture else 'disabled'}, "
                f"threshold={threshold}, gamma={gamma_value}"
            )

            return True

        except Exception as e:
            logger.error(f"Error initializing E-Ink renderer: {e}", exc_info=True)
            if self.eink_renderer:
                try:
                    self.eink_renderer.cleanup()
                except:
                    pass
                self.eink_renderer = None
            return False

    # _handle_eink_frame method removed - now handled internally by SimplifiedEInkRenderer

    def _emergency_exit_handler(self):
        """Emergency exit handler registered with atexit.
        This ensures we exit even if all other mechanisms fail."""
        logger.warning("Emergency exit handler called - forcing process exit")

        try:
            # Disconnect SAM if possible
            if self.sam:
                self.sam.disconnect()
        except Exception:
            pass  # Ignore errors during emergency exit
        try:
            # Make one final attempt to flush logs
            import logging

            logging.shutdown()
        except:
            pass

        # Force exit at the process level
        os._exit(0)

    # --- ASR Slots ---
    @pyqtSlot()
    def startRecording(self):
        if self._is_actively_recording:
            logger.warning("Already recording.")
            return
        if self.asr_provider.start_recording():
            self._is_actively_recording = True
            self.recordingStateChanged.emit(True)
            # Also forward to the bridge if it exists
            if hasattr(self, "bridge") and self.bridge:
                self.bridge.recordingStateChanged.emit(True)
            logger.info("UI Recording Started")
        else:
            logger.error("Failed to start ASR recording")

    MIN_AUDIO_BYTES_THRESHOLD = 8000  # 0.25s at 16kHz/16bit/mono

    @pyqtSlot()
    def stopAndTranscribe(self):
        if not self._is_actively_recording:
            logger.warning("Not recording.")
            return

        audio_data = self.asr_provider.stop_recording()
        self._is_actively_recording = False
        self.recordingStateChanged.emit(False)
        # Also forward to the bridge if it exists
        if hasattr(self, "bridge") and self.bridge:
            self.bridge.recordingStateChanged.emit(False)
        logger.info("UI Recording Stopped")

        # Check if audio data is long enough
        if not audio_data or len(audio_data) < self.MIN_AUDIO_BYTES_THRESHOLD:
            logger.warning(
                f"Audio data too short ({len(audio_data) if audio_data else 0} bytes). Minimum required: {self.MIN_AUDIO_BYTES_THRESHOLD}. Skipping transcription."
            )
            self.recordingError.emit("Audio too short")  # Emit error signal
            # Also forward to the bridge if it exists
            if hasattr(self, "bridge") and self.bridge:
                self.bridge.recordingError.emit("Audio too short")
            return  # Stop processing here

        # If audio is long enough, proceed with transcription
        logger.info("Scheduling transcription...")
        # Run transcription in a separate thread to avoid blocking UI
        if self._transcription_task and not self._transcription_task.done():
            logger.warning("Previous transcription task still running. Skipping new one.")
            return

        self._transcription_task = asyncio.create_task(self._transcribe_audio_async(audio_data))

    async def _transcribe_audio_async(self, audio_data):
        """Run transcription in a separate thread and emit signals."""
        try:
            logger.info("Transcription task started.")
            # Use asyncio.to_thread for blocking I/O or CPU-bound tasks
            transcription_generator = await asyncio.to_thread(
                self.asr_provider.transcribe_buffer, audio_data
            )

            full_transcription = []
            for segment in transcription_generator:
                self.transcriptionUpdate.emit(segment)
                # Also forward to the bridge if it exists
                if hasattr(self, "bridge") and self.bridge:
                    self.bridge.transcriptionUpdate.emit(segment)
                full_transcription.append(segment)
                await asyncio.sleep(0)  # Yield control briefly

            complete_text = " ".join(full_transcription)
            self.transcriptionComplete.emit(complete_text)
            # Also forward to the bridge if it exists
            if hasattr(self, "bridge") and self.bridge:
                self.bridge.transcriptionComplete.emit(complete_text)
            logger.info(f"Transcription task finished. Full text: {complete_text}")

        except Exception as e:
            logger.error(f"Error during transcription: {e}", exc_info=True)
            self.recordingError.emit("[Transcription Error]")  # Use the new error signal
            # Also forward to the bridge if it exists
            if hasattr(self, "bridge") and self.bridge:
                self.bridge.recordingError.emit("[Transcription Error]")  # Forward error signal
        finally:
            self._transcription_task = None  # Clear task handle

    # --- E-Ink Trigger Slot ---
    @pyqtSlot()
    def triggerEinkUpdate(self):
        """Slot callable from QML to force an e-ink render update."""
        if self.eink_renderer and self._eink_initialized:
            logger.debug("QML triggered E-Ink update")
            self.eink_renderer.force_update()
        else:
            logger.warning("Attempted to trigger E-Ink update, but renderer is not ready.")


if __name__ == "__main__":
    # Add signal handler for more immediate termination
    def force_exit_handler(signum):
        logger.warning(f"Received signal {signum}, forcing immediate exit")
        os._exit(0)

    signal.signal(signal.SIGINT, force_exit_handler)
    signal.signal(signal.SIGTERM, force_exit_handler)

    try:
        app = App()
        exit_code = asyncio.run(app.run())
        # Ensure we exit with the right code
        sys.exit(exit_code)
    except Exception as e:
        logger.critical(f"Fatal error in app: {e}", exc_info=True)
        # Force exit on unhandled exceptions
        os._exit(1)
    finally:
        # Ultimate fallback - force exit if we somehow reach here
        os._exit(0)
