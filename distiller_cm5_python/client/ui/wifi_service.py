"""
Distiller WiFi Service

Handles single-radio WiFi hardware limitation with proper state management,
web server coordination, and seamless user experience during transitions.
Provides persistent WiFi management and setup service.
"""

import argparse
import asyncio
import logging
import signal
import sys
import time
import threading
import socket
import subprocess
import psutil
from pathlib import Path
from typing import Optional
from enum import Enum
from flask import Flask, render_template, request, jsonify, redirect, url_for

from .network.wifi_manager import WiFiManager
from .network.device_config import get_device_config


class ServiceState(Enum):
    """Service state definitions"""

    INITIALIZING = "initializing"
    HOTSPOT_MODE = "hotspot_mode"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class DistillerWiFiService:
    """WiFi Setup Service with proper state transitions"""

    def __init__(
        self,
        hotspot_ssid: Optional[str] = None,
        hotspot_password: Optional[str] = None,
        device_name: Optional[str] = None,
        web_port: Optional[int] = None,
    ):
        # Initialize device configuration
        self.device_config = get_device_config()

        # Use device configuration with fallbacks to parameters
        self.hotspot_ssid = hotspot_ssid or self.device_config.get_hotspot_ssid()
        self.hotspot_password = (
            hotspot_password or self.device_config.get_hotspot_password()
        )
        self.device_name = device_name or self.device_config.get_friendly_name()
        self.web_port = web_port or self.device_config.get_web_port()

        # Service state
        self.current_state = ServiceState.INITIALIZING
        self.running = False
        self.target_ssid: Optional[str] = None
        self.target_password: Optional[str] = None
        self.connection_start_time: Optional[float] = None
        self._connection_in_progress = False  # Flag to prevent race conditions
        self.hotspot_ip: Optional[str] = None  # Store actual hotspot IP
        self._successful_connection_ip: Optional[str] = (
            None  # Track successful connection IP
        )
        self._successful_connection_ssid: Optional[str] = (
            None  # Track successful connection SSID
        )

        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)

        # Initialize WiFi manager
        self.wifi_manager = WiFiManager()

        # Flask app for web interface
        self.app = self._create_flask_app()
        self.web_server_thread: Optional[threading.Thread] = None
        self._web_server_shutdown = None  # For Flask shutdown
        self._connection_lock = threading.Lock()  # Prevent concurrent connections

        # Add custom template filters
        if self.app:
            self._add_template_filters()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.logger.info("WiFi Service initialized")
        self.logger.info(f"Device ID: {self.device_config.get_device_id()}")
        self.logger.info(f"Hostname: {self.device_config.get_hostname()}")
        self.logger.info(f"Hotspot SSID: {self.hotspot_ssid}")

    def setup_logging(self):
        """Configure logging"""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # Try to write to system log first, fallback to local
        log_paths = ["/var/log/distiller-wifi.log", "./distiller-wifi.log"]
        log_file = None

        for path in log_paths:
            try:
                Path(path).touch(exist_ok=True)
                log_file = path
                break
            except (PermissionError, OSError):
                continue

        handlers = [logging.StreamHandler(sys.stdout)]
        if log_file:
            handlers.append(logging.FileHandler(log_file))

        # Production logging level - only INFO and above
        logging.basicConfig(
            level=logging.INFO, format=log_format, handlers=handlers, force=True
        )

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals for service"""
        self.logger.info(f"Received signal {signum}, shutting down service...")
        self.running = False

    def _create_flask_app(self) -> Flask:
        """Create Flask web application"""
        # Get the correct paths for templates and static files
        import os

        current_dir = os.path.dirname(os.path.abspath(__file__))
        client_dir = os.path.dirname(current_dir)  # Go up from ui/ to client/
        template_folder = os.path.join(client_dir, "templates")
        static_folder = os.path.join(client_dir, "static")

        app = Flask(
            __name__, template_folder=template_folder, static_folder=static_folder
        )

        # Disable caching
        app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

        @app.after_request
        def add_no_cache_headers(response):
            response.cache_control.max_age = 0
            response.cache_control.no_cache = True
            response.cache_control.must_revalidate = True

            # Add security headers to handle HTTPS-Only mode and CSP
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"

            # Allow HTTP requests for local IoT device operation (no HTTPS upgrade)
            response.headers["Content-Security-Policy"] = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob: http: https:; "
                "connect-src 'self' http: https: ws: wss:; "
                "img-src 'self' data: blob: http: https:; "
                "font-src 'self' data: http: https:; "
                "frame-src 'none'; "
                "object-src 'none'"
            )

            # For local development and IoT devices, allow mixed content
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"

            return response

        # Routes
        @app.route("/")
        def index():
            return self._handle_index()

        @app.route("/confirm")
        def confirm():
            return self._handle_confirm()

        @app.route("/connect", methods=["POST"])
        def connect():
            return self._handle_connect()

        @app.route("/status")
        def status():
            return self._handle_status()

        @app.route("/api/status")
        def api_status():
            return self._handle_api_status()

        @app.route("/api/networks")
        def api_networks():
            return self._handle_api_networks()

        @app.route("/api/connect", methods=["POST"])
        def api_connect():
            return self._handle_connect()

        @app.route("/api/scan", methods=["GET"])
        def api_scan():
            """Manually trigger network scan"""
            try:
                networks = asyncio.run(self._scan_networks_properly())
                return jsonify(
                    {
                        "success": True,
                        "networks": [
                            {
                                "ssid": net.ssid,
                                "signal_strength": net.signal,
                                "security": net.security,
                                "frequency": net.frequency,
                            }
                            for net in networks
                        ],
                    }
                )
            except Exception as e:
                self.logger.error(f"Error in API scan: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @app.route("/restart-setup")
        def restart_setup():
            """Restart WiFi setup by disconnecting and entering hotspot mode"""
            return self._handle_restart_setup()

        # Catch-all for captive portal
        @app.route("/<path:path>")
        def catch_all(path):
            self.logger.info(f"Redirecting path: {path}")
            return redirect(url_for("index"))

        return app

    def _add_template_filters(self):
        """Add custom template filters"""

        @self.app.template_filter("timestamp_to_time")
        def timestamp_to_time(timestamp):
            """Convert timestamp to readable time format"""
            try:
                from datetime import datetime

                dt = datetime.fromtimestamp(float(timestamp))
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                return "Unknown time"

    def _handle_index(self):
        """Handle main index page"""
        try:
            if self.current_state == ServiceState.HOTSPOT_MODE:
                # Don't scan networks on page load - let JavaScript handle it
                # This prevents automatic hotspot restarts
                return render_template(
                    "index.html",
                    networks=[],  # Empty initially, will be loaded by JavaScript
                    device_name=self.device_name,
                    current_state=self.current_state.value,
                    web_port=self.web_port,
                )
            elif self.current_state == ServiceState.CONNECTED:
                # Show WiFi setup page even when connected to allow changing networks
                # Get current connection info to display
                current_status = self._get_current_status()
                return render_template(
                    "index.html",
                    networks=[],  # Empty initially, will be loaded by JavaScript
                    device_name=self.device_name,
                    current_state=self.current_state.value,
                    current_ssid=current_status.get("ssid"),
                    current_ip=current_status.get("ip_address"),
                    web_port=self.web_port,
                )
            elif self.current_state == ServiceState.INITIALIZING:
                # Service is transitioning (e.g., changing networks)
                # Redirect to status page to show progress
                return redirect(url_for("status"))
            else:
                # Show loading or error state
                return render_template(
                    "index.html",
                    networks=[],
                    device_name=self.device_name,
                    current_state=self.current_state.value,
                    message="Service initializing...",
                    web_port=self.web_port,
                )
        except Exception as e:
            self.logger.error(f"Error in index handler: {e}")
            return render_template(
                "index.html",
                networks=[],
                device_name=self.device_name,
                error="Failed to load networks",
                web_port=self.web_port,
            )

    def _handle_confirm(self):
        """Handle network confirmation page"""
        try:
            ssid = request.args.get("ssid", "")
            encrypted = request.args.get("encrypted", "unencrypted")

            if not ssid:
                return redirect(url_for("index"))

            return render_template(
                "confirm.html",
                ssid=ssid,
                encrypted=encrypted,
                device_name=self.device_name,
                web_port=self.web_port,
            )
        except Exception as e:
            self.logger.error(f"Error in confirm handler: {e}")
            return redirect(url_for("index"))

    def _handle_connect(self):
        """Handle connection request"""
        try:
            self.logger.debug(f"Raw request data: {request.data}")
            self.logger.debug(f"Request content type: {request.content_type}")
            self.logger.debug(f"Request is_json: {request.is_json}")
            self.logger.debug(f"Request form: {request.form}")
            self.logger.debug(f"Request args: {request.args}")

            # Handle both form data and JSON data
            if request.is_json:
                data = request.get_json()
                self.logger.debug(f"JSON data: {data}")
                ssid = data.get("ssid", "") if data else ""
                password = data.get("password", "") if data else ""
            else:
                ssid = request.form.get("ssid", "")
                password = request.form.get("password", "")

            self.logger.info(
                f"Connection request received: SSID='{ssid}', Password={'***' if password else 'None'}"
            )

            if not ssid:
                self.logger.warning("No SSID provided in connection request")
                if request.is_json:
                    return jsonify({"success": False, "error": "No SSID provided"}), 400
                return redirect(url_for("index"))

            # Store connection target
            self.target_ssid = ssid
            self.target_password = password
            self.connection_start_time = time.time()

            self.logger.info(f"Starting connection process to '{ssid}' in background")

            # Start connection in background
            self._start_connection_background()

            if request.is_json:
                return jsonify(
                    {
                        "success": True,
                        "message": "Connection started",
                    }
                )

            # Show a connecting page that directs users to check the eink display
            return render_template(
                "connecting.html",
                ssid=ssid,
                device_name=self.device_name,
                web_port=self.web_port,
                hotspot_ip=self.hotspot_ip or "192.168.4.1",
                device_id=self.device_config.get_device_id(),
            )

        except Exception as e:
            self.logger.error(f"Error in connect handler: {e}")
            if request.is_json:
                return jsonify({"success": False, "error": str(e)}), 500
            return redirect(url_for("index"))

    def _handle_status(self):
        """Handle status page"""
        try:
            # Get current status
            status_info = self._get_current_status()

            return render_template(
                "status.html",
                status=status_info,
                device_name=self.device_name,
                web_port=self.web_port,
            )
        except Exception as e:
            self.logger.error(f"Error in status handler: {e}")
            return render_template(
                "status.html",
                status={
                    "connected": False,
                    "connecting": False,
                    "error": "Status unavailable",
                },
                device_name=self.device_name,
                web_port=self.web_port,
            )

    def _handle_api_status(self):
        """Handle status API endpoint"""
        try:
            status_info = self._get_current_status()

            # Log response data for troubleshooting
            self.logger.info(
                f"API Status response: connected_to_target={status_info.get('connected_to_target')}, "
                f"current_state={status_info.get('current_state')}, "
                f"ssid={status_info.get('ssid')}, "
                f"ip={status_info.get('ip_address')}"
            )

            return jsonify({"success": True, **status_info})
        except Exception as e:
            self.logger.error(f"Error in API status: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    def _handle_api_networks(self):
        """Handle API request for available networks"""
        try:
            # Don't scan networks if we're in the middle of a connection
            if self.current_state == ServiceState.CONNECTING:
                self.logger.info(
                    "Connection in progress, returning cached/empty network list"
                )
                return jsonify(
                    {
                        "success": True,
                        "networks": [],
                        "message": "Connection in progress",
                    }
                )

            # Use cached or simplified scan for hotspot mode
            if self.current_state == ServiceState.HOTSPOT_MODE:
                # Don't stop hotspot for network scan - use a simpler approach
                try:
                    # Get a quick scan without stopping hotspot
                    networks = asyncio.run(self._get_networks_without_hotspot_restart())
                    return jsonify(
                        {
                            "success": True,
                            "networks": [
                                {
                                    "ssid": net.ssid,
                                    "signal_strength": net.signal,
                                    "security": net.security,
                                    "frequency": net.frequency,
                                }
                                for net in networks
                            ],
                        }
                    )
                except Exception as e:
                    self.logger.error(f"Error getting networks: {e}")
                    # Return some common networks as fallback
                    return jsonify(
                        {
                            "success": True,
                            "networks": [],
                            "message": "Scan temporarily unavailable",
                        }
                    )
            else:
                # Normal scan when not in hotspot mode
                networks = asyncio.run(self.wifi_manager.get_available_networks())
                return jsonify(
                    {
                        "success": True,
                        "networks": [
                            {
                                "ssid": net.ssid,
                                "signal_strength": net.signal,
                                "security": net.security,
                                "frequency": net.frequency,
                            }
                            for net in networks
                        ],
                    }
                )
        except Exception as e:
            self.logger.error(f"Error in API networks: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    def _handle_restart_setup(self):
        """Handle restart setup request - disconnect and enter hotspot mode"""
        try:
            self.logger.info("Restarting WiFi setup - user requested network change")

            # Run the restart process asynchronously
            asyncio.create_task(self._restart_setup_async())

            # Immediately redirect to main page
            return redirect(url_for("index"))

        except Exception as e:
            self.logger.error(f"Error restarting setup: {e}")
            return (
                render_template(
                    "error.html",
                    error="Failed to restart WiFi setup",
                    device_name=self.device_name,
                ),
                500,
            )

    def _get_current_status(self) -> dict:
        """Get current service status"""
        try:
            # Get WiFi connection status with timeout and error handling
            try:
                wifi_status = asyncio.run(self.wifi_manager.get_connection_status())
            except Exception as wifi_error:
                self.logger.warning(f"WiFi status check failed: {wifi_error}")
                # During network transition, if we're in CONNECTED state, trust that state
                if self.current_state == ServiceState.CONNECTED:
                    self.logger.info(
                        "WiFi status check failed but service state is CONNECTED - assuming successful connection"
                    )
                    # Use stored connection info if available
                    connection_ip = self._successful_connection_ip or "unknown"
                    connection_ssid = (
                        self._successful_connection_ssid or self.target_ssid
                    )
                    return {
                        "connected": True,
                        "connected_to_target": True,  # Trust the CONNECTED state
                        "connected_to_hotspot": False,
                        "connecting": False,
                        "ssid": connection_ssid,
                        "ip_address": connection_ip,
                        "interface": None,
                        "current_state": self.current_state.value,
                        "target_ssid": self.target_ssid,
                        "elapsed": 0,
                        "timestamp": int(time.time()),
                        "device_id": self.device_config.get_device_id(),
                        "hostname": self.device_config.get_hostname(),
                        "message": "Network transition in progress",
                    }
                # Return status based on service state when WiFi check fails
                return self._get_fallback_status()

            # Determine service state
            connecting = (
                self.current_state == ServiceState.CONNECTING
                and self.connection_start_time
                and time.time() - self.connection_start_time < 120
            )  # 2 min timeout

            # Check if we're connected to a target network (not hotspot)
            connected_to_target = (
                wifi_status.connected
                and self.current_state == ServiceState.CONNECTED
                and wifi_status.ssid
                and not wifi_status.ssid.startswith(
                    self.hotspot_ssid
                )  # Not connected to our hotspot
                and wifi_status.ip_address
                and wifi_status.ip_address != self.hotspot_ip  # Not using hotspot IP
                and self.target_ssid  # We have a target SSID
                and (
                    wifi_status.ssid == self.target_ssid
                    or wifi_status.ssid.startswith(self.target_ssid + " ")
                )  # Connected to target (handle NetworkManager numbering)
            )

            # ⚡ INSTANT WEB RESPONSE: Trust service state immediately (like QML does)
            if self.current_state == ServiceState.CONNECTED and not connected_to_target:
                self.logger.info(
                    f"🚀 INSTANT STATUS: Service is CONNECTED - providing immediate web response (like QML)"
                )
                self.logger.info(
                    f"  WiFi Status: connected={wifi_status.connected}, ssid='{wifi_status.ssid}', target_ssid='{self.target_ssid}'"
                )
                connected_to_target = True

            # Check if we're connected to hotspot
            connected_to_hotspot = (
                wifi_status.connected
                and wifi_status.ssid
                and (
                    wifi_status.ssid.startswith(self.hotspot_ssid)
                    or wifi_status.ip_address == self.hotspot_ip
                )
            )

            connected = connected_to_target or connected_to_hotspot

            # For CONNECTED state, ensure we have stable network info
            if self.current_state == ServiceState.CONNECTED:
                # Use cached connection info if current WiFi status is unreliable
                display_ssid = wifi_status.ssid or self._successful_connection_ssid
                display_ip = wifi_status.ip_address or self._successful_connection_ip
            else:
                display_ssid = wifi_status.ssid
                display_ip = wifi_status.ip_address

            return {
                "connected": connected,
                "connected_to_target": connected_to_target,  # New field to distinguish target vs hotspot
                "connected_to_hotspot": connected_to_hotspot,  # New field
                "connecting": connecting,
                "ssid": display_ssid,
                "ip_address": display_ip,
                "interface": wifi_status.interface,
                "current_state": self.current_state.value,
                "target_ssid": self.target_ssid,
                "elapsed": (
                    time.time() - self.connection_start_time
                    if self.connection_start_time
                    else 0
                ),
                "timestamp": int(time.time()),
                "device_id": self.device_config.get_device_id(),
                "hostname": self.device_config.get_hostname(),
                "transition_stable": self.current_state == ServiceState.CONNECTED
                and connected_to_target,
            }

        except Exception as e:
            self.logger.error(f"Error getting status: {e}")
            return self._get_fallback_status()

    def _get_fallback_status(self) -> dict:
        """Get fallback status when WiFi status check fails"""
        # Return status based on current service state
        if self.current_state == ServiceState.HOTSPOT_MODE:
            return {
                "connected": True,  # Connected to hotspot
                "connected_to_target": False,  # Not connected to target network
                "connected_to_hotspot": True,  # Connected to hotspot
                "connecting": False,
                "ssid": self.hotspot_ssid,  # Use hotspot SSID
                "ip_address": self.hotspot_ip or "192.168.4.1",  # Use actual hotspot IP
                "interface": None,
                "current_state": self.current_state.value,
                "target_ssid": self.target_ssid,
                "elapsed": 0,
                "timestamp": int(time.time()),
                "message": "Hotspot mode active",
                "device_id": self.device_config.get_device_id(),
                "hostname": self.device_config.get_hostname(),
                "transition_stable": False,
            }
        elif self.current_state == ServiceState.CONNECTING:
            return {
                "connected": False,
                "connected_to_target": False,
                "connected_to_hotspot": False,
                "connecting": True,
                "ssid": self.target_ssid,
                "ip_address": None,
                "interface": None,
                "current_state": self.current_state.value,
                "target_ssid": self.target_ssid,
                "elapsed": (
                    time.time() - self.connection_start_time
                    if self.connection_start_time
                    else 0
                ),
                "timestamp": int(time.time()),
                "message": "Connection in progress",
                "device_id": self.device_config.get_device_id(),
                "transition_stable": False,
                "hostname": self.device_config.get_hostname(),
            }
        elif self.current_state == ServiceState.CONNECTED:
            # When in CONNECTED state, trust the service state
            return {
                "connected": True,
                "connected_to_target": True,  # Trust the CONNECTED state
                "connected_to_hotspot": False,
                "connecting": False,
                "ssid": self._successful_connection_ssid or self.target_ssid,
                "ip_address": self._successful_connection_ip or "unknown",
                "interface": None,
                "current_state": self.current_state.value,
                "target_ssid": self.target_ssid,
                "elapsed": 0,
                "timestamp": int(time.time()),
                "message": "Connected to target network",
                "device_id": self.device_config.get_device_id(),
                "hostname": self.device_config.get_hostname(),
            }
        else:
            # Default disconnected state
            return {
                "connected": False,
                "connected_to_target": False,
                "connected_to_hotspot": False,
                "connecting": False,
                "ssid": None,
                "ip_address": None,
                "interface": None,
                "current_state": self.current_state.value,
                "target_ssid": self.target_ssid,
                "elapsed": 0,
                "timestamp": int(time.time()),
                "message": "Disconnected",
                "device_id": self.device_config.get_device_id(),
                "hostname": self.device_config.get_hostname(),
            }

    def _start_connection_background(self):
        """Start connection process in background thread"""

        def connection_worker():
            try:
                self._connection_in_progress = True
                self.logger.info("Background connection thread started")
                asyncio.run(self._perform_connection())
            except Exception as e:
                self.logger.error(f"Connection background thread error: {e}")
            finally:
                self._connection_in_progress = False
                self.logger.info("Connection background thread finished")

        thread = threading.Thread(target=connection_worker, daemon=True)
        thread.start()
        self.logger.info("Connection background thread launched")

    async def _cleanup_existing_connections(self):
        """Clean up any existing NetworkManager connections to prevent race conditions"""
        try:
            self.logger.info(
                "Cleaning up existing connections to prevent race conditions"
            )

            # Step 1: Cancel any pending NetworkManager operations
            try:
                result = subprocess.run(
                    ["nmcli", "device", "disconnect", "wlan0"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    self.logger.info("Disconnected wlan0 interface")
                else:
                    self.logger.debug(f"Interface disconnect result: {result.stderr}")
            except subprocess.TimeoutExpired:
                self.logger.warning("Timeout during interface disconnect")
            except Exception as e:
                self.logger.debug(f"Interface disconnect: {e}")

            # Step 2: Wait for NetworkManager to settle and clear any enqueued operations
            await asyncio.sleep(3)

            # Step 3: Force cleanup of any stuck connections
            try:
                # Get all active connections and forcefully disconnect them
                result = subprocess.run(
                    [
                        "nmcli",
                        "-t",
                        "-f",
                        "NAME,DEVICE",
                        "connection",
                        "show",
                        "--active",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        if line and ":" in line:
                            name, device = line.split(":", 1)
                            if device and device != "--":  # Has active device
                                try:
                                    subprocess.run(
                                        ["nmcli", "connection", "down", name],
                                        capture_output=True,
                                        text=True,
                                        timeout=5,
                                    )
                                    self.logger.debug(f"Forced down connection: {name}")
                                except:
                                    pass
            except Exception as e:
                self.logger.debug(f"Connection cleanup: {e}")

            # Step 4: Final settling period
            await asyncio.sleep(2)

        except Exception as e:
            self.logger.error(f"Error cleaning up connections: {e}")

    async def _perform_connection(self):
        """Perform WiFi connection with proper state management"""
        # Use thread lock to prevent concurrent connections
        if not self._connection_lock.acquire(blocking=False):
            self.logger.warning("Connection already in progress, skipping")
            return

        # Remember if we were already connected to WiFi (not hotspot)
        was_wifi_connected = False
        original_connection = None

        try:
            if not self.target_ssid:
                return

            # Check if we're switching from WiFi-to-WiFi or hotspot-to-WiFi
            current_status = await self.wifi_manager.get_connection_status()
            if current_status.connected and not self.wifi_manager.is_hotspot_active():
                was_wifi_connected = True
                original_connection = current_status.ssid
                self.logger.info(
                    f"WiFi-to-WiFi switch: {original_connection} → {self.target_ssid}"
                )
            else:
                self.logger.info(f"Hotspot-to-WiFi switch: → {self.target_ssid}")

            self.logger.info(f"Starting connection to {self.target_ssid}")
            self.current_state = ServiceState.CONNECTING

            # Only stop hotspot if it's active - don't mess with WiFi connections yet
            if self.wifi_manager.is_hotspot_active():
                self.logger.info("Stopping hotspot before connecting to target network")
                await self.wifi_manager.stop_hotspot()
                await asyncio.sleep(
                    1
                )  # Shorter wait since we're not switching from WiFi

            # For WiFi-to-WiFi switches, use lighter cleanup
            if was_wifi_connected:
                self.logger.info("Light cleanup for WiFi-to-WiFi switch")
                await asyncio.sleep(1)  # Just let NetworkManager settle briefly
            else:
                # Full cleanup only when coming from hotspot
                await self._cleanup_existing_connections()

            # Perform the connection
            password = self.target_password or ""
            success = await self.wifi_manager.connect_to_network(
                self.target_ssid, password
            )

            if success:
                self.logger.info(f"Successfully connected to {self.target_ssid}")

                # Quick verification for WiFi switches
                await asyncio.sleep(1)
                final_status = await self.wifi_manager.get_connection_status()

                if final_status.connected and final_status.ip_address:
                    # Connection successful
                    self.current_state = ServiceState.CONNECTED
                    self.logger.info(
                        f"Connection to {self.target_ssid} established at {final_status.ip_address}"
                    )

                    # Store connection info
                    self._successful_connection_ip = final_status.ip_address
                    self._successful_connection_ssid = self.target_ssid

                    # Handle network transition
                    await self._handle_network_transition()
                else:
                    # Connection verification failed
                    raise ConnectionError("Connection verification failed")

            else:
                raise ConnectionError(f"Failed to connect to {self.target_ssid}")

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")

            # Smart recovery based on original state
            if was_wifi_connected and original_connection:
                self.logger.info(
                    f"Attempting to restore original WiFi connection: {original_connection}"
                )
                try:
                    # Try to reconnect to original network
                    restore_success = (
                        await self.wifi_manager.restore_original_connection()
                    )
                    if restore_success:
                        self.logger.info(
                            f"Successfully restored connection to {original_connection}"
                        )
                        self.current_state = ServiceState.CONNECTED
                        return
                    else:
                        self.logger.warning("Failed to restore original connection")
                except Exception as restore_error:
                    self.logger.error(
                        f"Error restoring original connection: {restore_error}"
                    )

            # Only fall back to hotspot if we can't restore WiFi or we were originally in hotspot mode
            self.logger.info("Starting hotspot mode as fallback")
            await self._start_hotspot_mode()

        finally:
            # Release the connection lock
            try:
                self._connection_lock.release()
            except Exception:
                pass  # Lock might not be held if we got here via exception

            self.target_ssid = None
            self.target_password = None
            self.connection_start_time = None

    async def _handle_network_transition(self):
        """Handle transition from hotspot to client network"""
        try:
            # Get new network status
            status = await self.wifi_manager.get_connection_status()

            if status.connected and status.ip_address:
                self.logger.info(f"Network transition: now at {status.ip_address}")

                # Log success
                self.logger.info(f"WiFi setup completed successfully")
                self.logger.info(
                    f"Device accessible at: http://{status.ip_address}:{self.web_port}"
                )

                self.logger.info("WiFi connection established successfully")

        except Exception as e:
            self.logger.error(f"Error handling network transition: {e}")

    async def check_initial_state(self) -> ServiceState:
        """Check initial state and determine startup mode"""
        try:
            self.logger.info("Checking initial WiFi state...")

            # Always start in hotspot mode for consistent WiFi setup experience
            # This ensures users always see the QR code setup flow
            self.logger.info("Starting in hotspot mode for WiFi setup")
            return ServiceState.HOTSPOT_MODE

        except Exception as e:
            self.logger.error(f"Error checking initial state: {e}")
            return ServiceState.HOTSPOT_MODE

    async def _start_hotspot_mode(self):
        """Start hotspot mode with improved reliability and fallback strategies"""
        try:
            self.logger.info("Starting hotspot mode")
            self.current_state = ServiceState.HOTSPOT_MODE

            # Clean up NetworkManager state before starting hotspot
            await self._cleanup_networkmanager_state()

            # Try to start hotspot with multiple attempts
            success, hotspot_ip = await self._start_hotspot_with_retry()

            if success:
                self.hotspot_ip = hotspot_ip
                self.logger.info(f"Hotspot started: {self.hotspot_ssid}")
                self.logger.info(f"Web interface: http://{hotspot_ip}:{self.web_port}")
            else:
                self.logger.error("Failed to start hotspot after all attempts")
                # Try fallback approach
                if await self._try_fallback_hotspot():
                    self.logger.info("Fallback hotspot method succeeded")
                else:
                    self.current_state = ServiceState.ERROR

        except Exception as e:
            self.logger.error(f"Error starting hotspot: {e}")
            self.current_state = ServiceState.ERROR

    async def _cleanup_networkmanager_state(self):
        """Clean up NetworkManager state before starting hotspot"""
        try:
            self.logger.info("Cleaning up NetworkManager state")

            # Stop any active connections
            try:
                subprocess.run(
                    ["nmcli", "connection", "down", "id", self.hotspot_ssid],
                    capture_output=True,
                    timeout=10,
                )
            except Exception:
                pass  # Connection might not exist

            # Delete any existing hotspot connection profiles
            try:
                subprocess.run(
                    ["nmcli", "connection", "delete", "id", self.hotspot_ssid],
                    capture_output=True,
                    timeout=10,
                )
            except Exception:
                pass  # Profile might not exist

            # Wait for NetworkManager to settle
            await asyncio.sleep(1)

        except Exception as e:
            self.logger.warning(f"Error cleaning NetworkManager state: {e}")

    async def _start_hotspot_with_retry(self):
        """Start hotspot with retry logic"""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                self.logger.info(f"Hotspot start attempt {attempt + 1}/{max_attempts}")

                success, hotspot_ip = await self.wifi_manager.start_hotspot(
                    self.hotspot_ssid, self.hotspot_password
                )

                if success:
                    return success, hotspot_ip

                if attempt < max_attempts - 1:
                    self.logger.warning(
                        f"Hotspot attempt {attempt + 1} failed, retrying..."
                    )
                    await asyncio.sleep(2**attempt)  # Exponential backoff

            except Exception as e:
                self.logger.error(f"Hotspot attempt {attempt + 1} error: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2**attempt)

        return False, None

    async def _try_fallback_hotspot(self):
        """Try fallback hotspot configuration"""
        try:
            self.logger.info("Attempting fallback hotspot configuration")

            # Use a simpler hotspot configuration
            fallback_ssid = f"Setup-{self.device_config.get_device_id()[-4:]}"
            fallback_password = "password123"

            success, hotspot_ip = await self.wifi_manager.start_hotspot(
                fallback_ssid, fallback_password
            )

            if success:
                self.hotspot_ssid = fallback_ssid
                self.hotspot_password = fallback_password
                self.hotspot_ip = hotspot_ip
                self.logger.info(f"Fallback hotspot started: {fallback_ssid}")
                return True

        except Exception as e:
            self.logger.error(f"Fallback hotspot failed: {e}")

        return False

    async def _transition_to_hotspot(self):
        """Transition from connected state back to hotspot mode"""
        try:
            self.logger.info("Transitioning to hotspot mode for network change")

            # Get current connection status
            current_status = await self.wifi_manager.get_connection_status()
            if current_status.connected:
                self.logger.info(
                    f"Disconnecting from current network: {current_status.ssid}"
                )

                # Stop current connection - this will automatically disconnect
                # We don't need to explicitly disconnect since starting hotspot will handle it

            # Start hotspot mode
            await self._start_hotspot_mode()

            self.logger.info("Successfully transitioned to hotspot mode")

        except Exception as e:
            self.logger.error(f"Error transitioning to hotspot: {e}")
            # Try to ensure we end up in some usable state
            try:
                await self._start_hotspot_mode()
            except Exception as fallback_error:
                self.logger.error(f"Fallback hotspot start failed: {fallback_error}")
                self.current_state = ServiceState.ERROR

    async def _restart_setup_async(self):
        """Restart WiFi setup by disconnecting from current network and starting hotspot"""
        try:
            self.logger.info("Executing async restart setup process")

            # Disconnect from current WiFi connection
            disconnect_success = await self.wifi_manager.disconnect_current_wifi()
            if disconnect_success:
                self.logger.info("Successfully disconnected from current WiFi")
            else:
                self.logger.warning(
                    "Failed to disconnect from current WiFi, continuing anyway"
                )

            # Reset service state and restart hotspot mode
            self.current_state = ServiceState.INITIALIZING
            await self._start_hotspot_mode()

            self.logger.info("WiFi setup restart completed successfully")

        except Exception as e:
            self.logger.error(f"Error during restart setup: {e}")
            # Try to ensure we end up in hotspot mode
            try:
                self.current_state = ServiceState.INITIALIZING
                await self._start_hotspot_mode()
            except Exception as fallback_error:
                self.logger.error(f"Fallback restart failed: {fallback_error}")
                self.current_state = ServiceState.ERROR

    def _stop_web_server(self):
        """Stop the web server gracefully"""
        try:
            # Stop the web server thread if it exists
            if self.web_server_thread and self.web_server_thread.is_alive():
                self.logger.info("Stopping web server...")

                # Wait for thread to finish
                self.web_server_thread.join(timeout=5)

                if self.web_server_thread.is_alive():
                    self.logger.warning("Web server thread did not stop gracefully")

                self.web_server_thread = None
                self.logger.info("Web server stopped")

        except Exception as e:
            self.logger.error(f"Error stopping web server: {e}")

    def _start_web_server(self):
        """Start web server in background thread"""
        if not self.app:
            self.logger.error("Cannot start web server...")
            return

        # Stop any existing server first
        self._stop_web_server()

        def run_server():
            accessible_ip = self.hotspot_ip or "0.0.0.0"
            self.logger.info(f"Starting web server on {accessible_ip}:{self.web_port}")
            try:
                if self.app:  # Additional None check for type safety
                    self.app.run(
                        host="0.0.0.0",
                        port=self.web_port,
                        debug=False,
                        use_reloader=False,
                        threaded=True,
                    )
            except Exception as e:
                if "Address already in use" in str(e):
                    self.logger.error(
                        f"Port {self.web_port} still in use, attempting cleanup..."
                    )
                    time.sleep(2)  # Wait for cleanup
                    if self.app:
                        self.app.run(
                            host="0.0.0.0",
                            port=self.web_port,
                            debug=False,
                            use_reloader=False,
                            threaded=True,
                        )
                else:
                    self.logger.error(f"Error starting web server: {e}")

        self.web_server_thread = threading.Thread(target=run_server, daemon=True)
        self.web_server_thread.start()

    async def run(self):
        """Run the WiFi service as a persistent service"""
        self.logger.info("Starting Distiller WiFi Service")
        self.running = True

        try:
            # Check initial state - will always be HOTSPOT_MODE now
            initial_state = await self.check_initial_state()
            self.current_state = initial_state

            # Start hotspot mode for WiFi setup
            if initial_state == ServiceState.HOTSPOT_MODE:
                await self._start_hotspot_mode()

                # Start web server for user interaction
                self._start_web_server()

                self.logger.info(
                    "WiFi setup service ready - waiting for user configuration"
                )

                # Wait for user to configure and connect to WiFi
                # Monitor for connection success and then monitor ongoing connection
                max_setup_time = 1800  # 30 minutes maximum setup time
                start_time = time.time()

                while self.running and (time.time() - start_time) < max_setup_time:
                    try:
                        # Check if we've successfully connected
                        if self.current_state == ServiceState.CONNECTED:
                            self.logger.info(
                                "WiFi connection successful - starting connection monitoring"
                            )
                            # Small delay to ensure connection is stable (reduced from 5s to 2s)
                            await asyncio.sleep(2)
                            # Start monitoring connection instead of exiting
                            await self._monitor_connection()
                            return

                        # Handle connection timeout
                        if (
                            self.current_state == ServiceState.CONNECTING
                            and self.connection_start_time
                            and time.time() - self.connection_start_time > 120
                        ):
                            self.logger.warning(
                                "Connection timeout, returning to hotspot mode"
                            )
                            self.current_state = ServiceState.HOTSPOT_MODE
                            await self._start_hotspot_mode()

                        # Check every 5 seconds
                        await asyncio.sleep(5)

                    except Exception as e:
                        self.logger.error(f"Error in service loop: {e}")
                        await asyncio.sleep(5)

                # If we reach here, the setup time limit was exceeded
                self.logger.error(f"WiFi setup timeout after {max_setup_time} seconds")
                raise TimeoutError("WiFi setup timeout - manual intervention required")

        except Exception as e:
            self.logger.error(f"Service error: {e}")
            raise
        finally:
            await self.cleanup()

    async def _monitor_connection(self):
        """Monitor WiFi connection and handle disconnections"""
        self.logger.info("Starting connection monitoring...")

        while self.running:
            try:
                # Check connection status
                status = await self.wifi_manager.get_connection_status()

                if not status.connected:
                    self.logger.warning(
                        "WiFi connection lost, returning to hotspot mode"
                    )
                    self.current_state = ServiceState.HOTSPOT_MODE
                    # Reset handoff flag when connection is lost - we need to manage display again
                    await self._start_hotspot_mode()
                    self._start_web_server()

                    # Wait for user to reconfigure
                    await asyncio.sleep(30)
                    continue

                await asyncio.sleep(30)

            except Exception as e:
                self.logger.error(f"Error in connection monitoring: {e}")
                await asyncio.sleep(30)

        self.logger.info("Connection monitoring stopped")

    async def _scan_networks_properly(self):
        """Scan for networks with proper hotspot handling"""
        try:
            # Check if we're in the middle of a connection attempt
            if self.current_state == ServiceState.CONNECTING:
                self.logger.info("Connection in progress, skipping network scan")
                return []

            if self.current_state == ServiceState.HOTSPOT_MODE:

                # Temporarily stop hotspot to get proper network scan
                self.logger.info("Temporarily stopping hotspot for network scan")
                hotspot_was_active = self.wifi_manager.is_hotspot_active()

                if hotspot_was_active:
                    await self.wifi_manager.stop_hotspot()
                    await asyncio.sleep(3)  # Wait longer for interface to be ready

                # Perform scan
                networks = await self.wifi_manager.get_available_networks()

                # Filter out our own hotspot SSID
                filtered_networks = [
                    net for net in networks if net.ssid != self.hotspot_ssid
                ]

                # Only restart hotspot if we're still in hotspot mode (not connecting)
                if (
                    hotspot_was_active
                    and self.current_state == ServiceState.HOTSPOT_MODE
                ):
                    self.logger.info("Restarting hotspot after network scan")
                    # Add delay to prevent race conditions
                    await asyncio.sleep(2)
                    await self.wifi_manager.start_hotspot(
                        self.hotspot_ssid, self.hotspot_password
                    )

                return filtered_networks
            else:
                # Normal scan when not in hotspot mode
                return await self.wifi_manager.get_available_networks()

        except Exception as e:
            self.logger.error(f"Error in network scan: {e}")
            # Try to restore hotspot if we're supposed to be in hotspot mode
            if self.current_state == ServiceState.HOTSPOT_MODE:
                try:
                    await asyncio.sleep(3)  # Prevent race conditions
                    await self.wifi_manager.start_hotspot(
                        self.hotspot_ssid, self.hotspot_password
                    )
                except Exception as restore_error:
                    self.logger.error(f"Failed to restore hotspot: {restore_error}")
            return []

    async def cleanup(self):
        """Cleanup service resources"""
        self.logger.info("Cleaning up WiFi service")

        try:
            # Stop web server first
            self._stop_web_server()

            # Stop hotspot if running
            if self.wifi_manager.is_hotspot_active():
                await self.wifi_manager.stop_hotspot()

        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")

    async def _get_networks_without_hotspot_restart(self):
        """Get networks without stopping hotspot - use alternative method"""
        try:
            # Use a different approach that doesn't interfere with hotspot
            base_cmd = [
                "nmcli",
                "-t",
                "-f",
                "SSID,SIGNAL,SECURITY,FREQ",
                "device",
                "wifi",
                "list",
                "--rescan",
                "no",
            ]
            # Use WiFiManager's sudo handling for privileged commands
            cmd = self.wifi_manager._build_command(base_cmd)
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return []

            networks = []
            seen_ssids = set()

            for line in stdout.decode().strip().split("\n"):
                if not line:
                    continue

                parts = line.split(":")
                if len(parts) >= 4:
                    ssid = parts[0]
                    signal = int(parts[1]) if parts[1].isdigit() else 0
                    security = "encrypted" if parts[2] else "open"
                    frequency = parts[3]

                    # Skip empty SSIDs, our hotspot, and duplicates
                    if ssid and ssid != self.hotspot_ssid and ssid not in seen_ssids:
                        from .network.wifi_manager import NetworkInfo

                        networks.append(
                            NetworkInfo(
                                ssid=ssid,
                                signal=signal,
                                security=security,
                                frequency=frequency,
                                in_use=False,
                            )
                        )
                        seen_ssids.add(ssid)

            # Sort by signal strength
            networks.sort(key=lambda x: x.signal, reverse=True)
            # Networks found successfully
            return networks

        except Exception:
            return []


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Distiller WiFi Service")

    parser.add_argument(
        "--ssid",
        default=None,
        help="Hotspot SSID (default: auto-generated with random suffix)",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Hotspot password (default: from device config)",
    )
    parser.add_argument(
        "--device-name",
        default=None,
        help="Device name for display (default: auto-generated with random suffix)",
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Web server port (default: 8080)"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Service now runs as distiller user with proper sudo permissions
    try:
        service = DistillerWiFiService(
            hotspot_ssid=args.ssid,
            hotspot_password=args.password,
            device_name=args.device_name,
            web_port=args.port,
        )

        asyncio.run(service.run())

    except KeyboardInterrupt:
        print("\nService interrupted by user")
    except Exception as e:
        print(f"Service failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
