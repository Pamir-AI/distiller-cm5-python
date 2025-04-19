# pyright: reportArgumentType=false
from PyQt6.QtCore import QUrl
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QApplication
from distiller_cm5_python.client.ui.AppInfoManager import AppInfoManager
from distiller_cm5_python.client.ui.bridge.MCPClientBridge import MCPClientBridge
from distiller_cm5_python.client.ui.bridge.EInkRenderer import EInkRenderer, config
from distiller_cm5_python.client.ui.bridge.EInkRendererBridge import EInkRendererBridge
from contextlib import AsyncExitStack
from qasync import QEventLoop
from distiller_cm5_python.utils.logger import logger
import asyncio
import os
import sys


class App:
    def __init__(self):
        """Initialize the Qt application and QML engine."""
        # Set platform to offscreen before creating QApplication if E-Ink is enabled
        # TODO: Make this conditional based on configuration
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("PamirAI Assistant")
        self.app.setOrganizationName("PamirAI Inc")

        # Set up the event loop
        self.loop = QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)

        # Create QML engine
        self.engine = QQmlApplicationEngine()

        # Create the MCP client bridge and app info manager
        self.bridge = MCPClientBridge()
        self.app_info = AppInfoManager()

        # E-Ink Initialization
        self.eink_renderer = None
        self.eink_bridge = None

        # Connect signal to handle application quit
        self.app.aboutToQuit.connect(self.handle_quit)

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
        logger.info("Bridge initialized successfully")

        # Now register the initialized bridge with QML
        root_context.setContextProperty("bridge", self.bridge)
        root_context.setContextProperty("AppInfo", self.app_info)

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
                f.write("[Paths]\nPrefix=.\n")

        # Signal to QML that the bridge is ready
        self.bridge.setReady(True)
        
        # Load the QML file
        url = QUrl.fromLocalFile(qml_file)
        self.engine.load(url)

        # Wait for the QML to load
        await asyncio.sleep(0.1)

        # Check if the QML was loaded successfully
        if not self.engine.rootObjects():
            logger.error("Failed to load QML")
            raise RuntimeError("Failed to load QML")


        # Apply fixed size constraints to the root window after loading
        self._apply_window_constraints()


        # E-Ink Initialization Call
        self._init_eink_renderer()

        logger.info("Application initialized successfully")

    async def run(self):
        """Run the application with async event loop."""
        try:
            # Initialize the application
            await self.initialize()

            # Use AsyncExitStack for resource management
            async with AsyncExitStack() as exit_stack:
                # Register cleanup callbacks if needed
                exit_stack.push_async_callback(self._cleanup_resources)

                # Schedule application execution
                run_app_task = asyncio.create_task(self.loop.run_forever())

                # Wait for the application to exit
                try:
                    await run_app_task
                except asyncio.CancelledError:
                    logger.info("Application task cancelled")

                # The AsyncExitStack's context manager will handle cleanup
        except Exception as e:
            logger.error(f"Error running application: {e}", exc_info=True)
            raise
        finally:
            # Ensure we exit cleanly
            if hasattr(self, "app") and self.app:
                self.app.quit()

            # Return exit code
            logger.info("Application exited")
            return 0

    async def _cleanup_resources(self):
        """Cleanup resources registered with exit_stack."""
        logger.info("Cleaning up resources from exit stack")
        try:
            # Ensure the bridge is cleaned up
            if hasattr(self, "bridge") and self.bridge:
                await self.bridge.cleanup()

            # E-Ink Cleanup
            # Stop the E-Ink renderer if active
            if self.eink_renderer:
                self.eink_renderer.stop()
                logger.info("E-Ink renderer stopped.")
                self.eink_renderer = None

            # Clean up e-ink bridge if active
            if self.eink_bridge:
                self.eink_bridge.cleanup()
                logger.info("E-Ink bridge cleaned up.")
                self.eink_bridge = None

        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}", exc_info=True)
        finally:
            # Close the event loop if it exists and is open
            if hasattr(self, "loop") and self.loop and not self.loop.is_closed():
                self.loop.close()

    def handle_quit(self):
        """Handle application quit event."""
        logger.info("Application quit requested")

        # Stop the E-Ink renderer if active
        if self.eink_renderer:
            self.eink_renderer.stop()
            self.eink_renderer = None
            
        # Clean up e-ink bridge if active
        if self.eink_bridge:
            self.eink_bridge.cleanup()
            self.eink_bridge = None

        # Schedule bridge shutdown
        try:
            self.bridge.shutdown()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)

    def _set_display_dimensions(self):
        """Set display dimensions from the config file as context properties for QML."""
        # Get width and height from config or use defaults
        width = int(config.get("display").get("width") or 240)
        height = int(config.get("display").get("height") or 416)
        
        # Set as context properties for QML
        rc = self.engine.rootContext()
        rc.setContextProperty("configWidth", width)
        rc.setContextProperty("configHeight", height)
        logger.info(f"Set display dimensions from config: {width}x{height}")


    def _apply_window_constraints(self):
        """Apply fixed size constraints to the main window after QML is loaded."""
        # Get display dimensions from config
        width = int(config.get("display").get("width") or 240)
        height = int(config.get("display").get("height") or 416)
        
        # Find the root window object
        root_objects = self.engine.rootObjects()
        if not root_objects:
            logger.error("No root objects found to apply size constraints")
            return

        main_window = root_objects[0]
        
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
        """Initialize the E-Ink renderer."""
        # Check if e-ink mode is enabled in config
        eink_enabled = config.get("display").get("eink_enabled")
        
        if not eink_enabled:
            logger.info("E-Ink display mode not enabled")
            return

        logger.info("E-Ink display mode enabled")

        # Get configuration for e-ink renderer
        capture_interval = config.get("display").get("eink_refresh_interval")
        buffer_size = config.get("display").get("eink_buffer_size") 
        dithering_enabled = config.get("display").get("eink_dithering_enabled")

        try:
            # First initialize the e-ink bridge that connects to the hardware
            self.eink_bridge = EInkRendererBridge(parent=self.app)
            init_success = self.eink_bridge.initialize()

            if not init_success:
                logger.error("Failed to initialize e-ink bridge")
                self.eink_bridge = None
                return

            # Configure dithering
            self.eink_bridge.set_dithering(dithering_enabled)

            # Create the renderer instance
            self.eink_renderer = EInkRenderer(
                parent=self.app,
                capture_interval=capture_interval,
                buffer_size=buffer_size
            )

            # Create a lambda function to handle the signal instead of direct method connection
            # This avoids the null pointer issue
            self.eink_renderer.frameReady.connect(
                lambda data, w, h: self._handle_eink_frame(data, w, h)
            )
            
            # Start capturing frames
            self.eink_renderer.start()
            logger.info(f"E-Ink renderer initialized with {capture_interval}ms interval")
        except Exception as e:
            logger.error(f"Error initializing E-Ink renderer: {e}", exc_info=True)
            # Clean up resources on failure
            if self.eink_bridge:
                self.eink_bridge.cleanup()
                self.eink_bridge = None
            self.eink_renderer = None

    def _handle_eink_frame(self, frame_data, width, height):
        """
        Handle a new frame from the E-Ink renderer.
        This method forwards the frame to the e-ink bridge for display.
        
        Args:
            frame_data: The binary data for the frame
            width: The width of the frame
            height: The height of the frame
        """
        logger.debug(f"E-Ink frame ready: {width}x{height}, {len(frame_data)} bytes")
        
        # Forward the frame to the e-ink bridge if available
        if self.eink_bridge and self.eink_bridge.initialized:
            self.eink_bridge.handle_frame(frame_data, width, height)
        else:
            logger.warning("E-Ink bridge not available or not initialized")


if __name__ == "__main__":
    app = App()
    asyncio.run(app.run())
