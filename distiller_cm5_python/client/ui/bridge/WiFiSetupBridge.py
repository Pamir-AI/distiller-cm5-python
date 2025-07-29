"""
WiFi Setup Bridge

Manages WiFi setup process by running Flask web server in background
and providing QML interface for status monitoring and user guidance.
"""

import asyncio
import logging
import threading
import time
import io
import base64
from typing import Optional, Dict, Any
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, pyqtProperty, QTimer, QMetaObject, Qt
from PyQt6.QtWidgets import QApplication

from ..wifi_service import DistillerWiFiService, ServiceState

logger = logging.getLogger(__name__)


class WiFiSetupState(Enum):
    """WiFi Setup UI States"""

    IDLE = "idle"
    INITIALIZING = "initializing"
    HOTSPOT_ACTIVE = "hotspot_active"
    USER_CONNECTED = "user_connected"
    SCANNING = "scanning"
    NETWORK_SELECTION = "network_selection"
    CONNECTING = "connecting"
    SUCCESS = "success"
    ERROR = "error"


class WiFiSetupBridge(QObject):
    """Bridge class for WiFi setup functionality"""

    # Signals for QML
    setupStateChanged = pyqtSignal(str)
    setupMessageChanged = pyqtSignal(str)
    hotspotInfoChanged = pyqtSignal(str, str, str)  # ssid, password, ip
    qrCodeChanged = pyqtSignal(str)  # base64 encoded QR code image
    networkConnected = pyqtSignal(str, str)  # ssid, ip
    errorOccurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Setup state
        self._setup_state = WiFiSetupState.IDLE
        self._setup_message = ""
        self._hotspot_ssid = ""
        self._hotspot_password = ""
        self._hotspot_ip = ""
        self._qr_code_data = ""
        self._connected_network = ""
        self._connected_ip = ""
        self._error_message = ""

        # WiFi service instance
        self._wifi_service: Optional[DistillerWiFiService] = None
        self._service_thread: Optional[threading.Thread] = None
        self._running = False

        # State monitoring timer
        self._monitor_timer = QTimer()
        self._monitor_timer.timeout.connect(self._monitor_service_state)
        self._monitor_timer.setInterval(1000)  # Check every second

        logger.info("WiFiSetupBridge initialized")

    # Properties for QML
    @pyqtProperty(str, notify=setupStateChanged)
    def setupState(self) -> str:
        return self._setup_state.value

    @pyqtProperty(str, notify=setupMessageChanged)
    def setupMessage(self) -> str:
        return self._setup_message

    @pyqtProperty(str, notify=hotspotInfoChanged)
    def hotspotSSID(self) -> str:
        return self._hotspot_ssid

    @pyqtProperty(str, notify=hotspotInfoChanged)
    def hotspotPassword(self) -> str:
        return self._hotspot_password

    @pyqtProperty(str, notify=hotspotInfoChanged)
    def hotspotIP(self) -> str:
        return self._hotspot_ip

    @pyqtProperty(str, notify=qrCodeChanged)
    def qrCodeData(self) -> str:
        return self._qr_code_data

    @pyqtProperty(str, notify=networkConnected)
    def connectedNetwork(self) -> str:
        return self._connected_network

    @pyqtProperty(str, notify=networkConnected)
    def connectedIP(self) -> str:
        return self._connected_ip

    @pyqtProperty(str, notify=errorOccurred)
    def errorMessage(self) -> str:
        return self._error_message

    @pyqtSlot()
    def startWiFiSetup(self):
        """Start the WiFi setup process"""
        if self._running:
            logger.warning("WiFi setup already running")
            return

        logger.info("Starting WiFi setup process")
        self._set_state(WiFiSetupState.INITIALIZING, "Starting WiFi setup...")

        try:
            # Regenerate password for new setup session
            self._regenerate_hotspot_password()

            # Initialize WiFi service
            self._wifi_service = DistillerWiFiService(
                enable_eink=False  # We're using GUI instead
            )

            # Start service in background thread
            self._service_thread = threading.Thread(target=self._run_wifi_service_sync, daemon=True)
            self._running = True
            self._service_thread.start()

            # Start monitoring
            self._monitor_timer.start()

        except Exception as e:
            logger.error(f"Failed to start WiFi setup: {e}")
            self._set_error(f"Failed to start WiFi setup: {str(e)}")

    @pyqtSlot()
    def stopWiFiSetup(self):
        """Stop the WiFi setup process"""
        if not self._running:
            return

        logger.info("Stopping WiFi setup process")
        self._running = False

        # Stop monitoring
        self._monitor_timer.stop()

        if self._wifi_service:
            try:
                self._wifi_service.running = False
                # Give service time to cleanup
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error stopping WiFi service: {e}")

        self._wifi_service = None
        self._service_thread = None

        self._set_state(WiFiSetupState.IDLE, "Setup stopped")

    @pyqtSlot(result=bool)
    def isSetupRunning(self) -> bool:
        """Check if setup is currently running"""
        return self._running

    def _run_wifi_service_sync(self):
        """Run the WiFi service in background thread (synchronous wrapper)"""
        try:
            if self._wifi_service:
                # Create a new event loop for this thread
                asyncio.run(self._wifi_service.run())
        except Exception as e:
            logger.error(f"WiFi service error: {e}")
            # Use Qt's thread-safe signal to update UI
            self.errorOccurred.emit(f"Service error: {str(e)}")

    def _monitor_service_state(self):
        """Monitor WiFi service state and update UI accordingly"""
        if not self._wifi_service or not self._running:
            return

        try:
            service_state = self._wifi_service.current_state

            # Map service state to UI state
            if service_state == ServiceState.INITIALIZING:
                self._set_state(WiFiSetupState.INITIALIZING, "Initializing WiFi setup...")

            elif service_state == ServiceState.HOTSPOT_MODE:
                # Update hotspot information
                hotspot_ssid = self._wifi_service.hotspot_ssid
                hotspot_password = self._wifi_service.hotspot_password
                hotspot_ip = getattr(self._wifi_service, "hotspot_ip", "192.168.4.1")

                self._set_hotspot_info(hotspot_ssid, hotspot_password, hotspot_ip)
                self._set_state(WiFiSetupState.HOTSPOT_ACTIVE, f"Hotspot active: {hotspot_ssid}")

            elif service_state == ServiceState.CONNECTING:
                target_ssid = getattr(self._wifi_service, "target_ssid", "network")
                self._set_state(WiFiSetupState.CONNECTING, f"Connecting to {target_ssid}...")

            elif service_state == ServiceState.CONNECTED:
                # Get connection details
                ssid = getattr(self._wifi_service, "_successful_connection_ssid", "Unknown")
                ip = getattr(self._wifi_service, "_successful_connection_ip", "Unknown")

                # Check if this was a new connection or already connected
                was_connecting = (
                    hasattr(self._wifi_service, "target_ssid") and self._wifi_service.target_ssid
                )

                self._set_network_connected(ssid, ip)

                if was_connecting:
                    self._set_state(WiFiSetupState.SUCCESS, f"Successfully connected to {ssid}")
                else:
                    self._set_state(
                        WiFiSetupState.SUCCESS,
                        f"Already connected to {ssid} - Web interface available",
                    )

            elif service_state == ServiceState.ERROR:
                error_msg = "Connection failed"
                self._set_state(WiFiSetupState.ERROR, error_msg)

        except Exception as e:
            logger.error(f"Error monitoring service state: {e}")

    def _regenerate_hotspot_password(self):
        """Regenerate hotspot password for new setup session"""
        try:
            from ..network.device_config import get_device_config

            device_config = get_device_config()
            new_password = device_config.regenerate_hotspot_password()
            logger.info(f"Regenerated hotspot password for setup session")
        except Exception as e:
            logger.error(f"Failed to regenerate hotspot password: {e}")

    def _generate_wifi_qr_code(self, ssid: str, password: str) -> str:
        """Generate QR code for WiFi connection as base64 encoded PNG"""
        try:
            import qrcode
            from PIL import Image

            # Create WiFi QR code content in standard format
            # WIFI:T:WPA;S:SSID;P:password;H:false;;
            wifi_content = f"WIFI:T:WPA;S:{ssid};P:{password};H:false;;"

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,  # Small size
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=4,
                border=2,
            )
            qr.add_data(wifi_content)
            qr.make(fit=True)

            # Create monochrome image (for e-ink compatibility)
            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to base64 for QML display
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_data = buffer.getvalue()
            base64_encoded = base64.b64encode(img_data).decode("utf-8")

            logger.info(f"Generated QR code for WiFi: {ssid}")
            return f"data:image/png;base64,{base64_encoded}"

        except Exception as e:
            logger.error(f"Failed to generate QR code: {e}")
            return ""

    def _set_state(self, state: WiFiSetupState, message: str):
        """Update setup state and message"""
        if self._setup_state != state or self._setup_message != message:
            self._setup_state = state
            self._setup_message = message
            self.setupStateChanged.emit(state.value)
            self.setupMessageChanged.emit(message)
            logger.info(f"Setup state: {state.value} - {message}")

    def _set_hotspot_info(self, ssid: str, password: str, ip: str):
        """Update hotspot information and generate QR code"""
        changed = (
            self._hotspot_ssid != ssid
            or self._hotspot_password != password
            or self._hotspot_ip != ip
        )

        if changed:
            self._hotspot_ssid = ssid
            self._hotspot_password = password
            self._hotspot_ip = ip

            # Generate QR code for WiFi connection
            qr_data = self._generate_wifi_qr_code(ssid, password)
            if qr_data != self._qr_code_data:
                self._qr_code_data = qr_data
                self.qrCodeChanged.emit(qr_data)

            self.hotspotInfoChanged.emit(ssid, password, ip)

    def _set_network_connected(self, ssid: str, ip: str):
        """Update connected network information"""
        if self._connected_network != ssid or self._connected_ip != ip:
            self._connected_network = ssid
            self._connected_ip = ip
            self.networkConnected.emit(ssid, ip)

    @pyqtSlot(str)
    def _set_error(self, error: str):
        """Set error state"""
        self._error_message = error
        self._set_state(WiFiSetupState.ERROR, error)
        self.errorOccurred.emit(error)

    def cleanup(self):
        """Cleanup resources"""
        self.stopWiFiSetup()
        logger.info("WiFiSetupBridge cleanup completed")
