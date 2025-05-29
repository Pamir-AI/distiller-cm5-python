#!/usr/bin/env python3
"""
WiFi Configuration Web Server module.
Provides a web interface for WiFi configuration.
"""

import os
import json
import asyncio
import logging
import uvicorn
import ipaddress
import signal
import sys
import socket
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

from .wifi_manager import WiFiManager
from .mdns_service import MDNSService

logger = logging.getLogger(__name__)

# Define API models
class WiFiNetwork(BaseModel):
    ssid: str
    signal: int
    security: str

class WiFiCredentials(BaseModel):
    ssid: str
    password: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, password, values):
        ssid = values.get('ssid')
        if not ssid:
            raise ValueError("SSID is required")
            
        # If security requires a password but none provided
        # This is just a placeholder for more detailed validation
        return password

class WiFiStatus(BaseModel):
    connected: bool
    current_connection: Optional[Dict[str, Any]] = None
    is_hotspot_active: bool

class ActionResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

# Define the FastAPI app
app = FastAPI(
    title="WiFi Configuration API",
    description="API for configuring WiFi on the device",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Initialize WiFi manager and mDNS service
wifi_manager = None
mdns_service = None

# Store the server startup task
server_startup_task = None

# Current web directory
current_dir = Path(__file__).parent
static_dir = current_dir / "static"

# Make sure static directory exists
os.makedirs(static_dir, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# API endpoints
@app.get("/", response_class=HTMLResponse)
async def get_index() -> HTMLResponse:
    """
    Serve the main HTML page for WiFi configuration.
    """
    html_path = static_dir / "index.html"
    
    # Serve the index.html file
    return FileResponse(html_path)

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard() -> HTMLResponse:
    """
    Serve the dashboard HTML page after successful WiFi connection.
    """
    html_path = static_dir / "dashboard.html"
    
    # Serve the dashboard.html file
    return FileResponse(html_path)

@app.get("/api/networks", response_model=List[WiFiNetwork])
async def get_networks() -> List[WiFiNetwork]:
    """
    Get list of available WiFi networks.
    """
    if not wifi_manager:
        raise HTTPException(status_code=503, detail="WiFi manager not initialized")
        
    networks = wifi_manager.scan_networks()
    return networks

@app.get("/api/status", response_model=WiFiStatus)
async def get_status() -> WiFiStatus:
    """
    Get current WiFi connection status.
    """
    if not wifi_manager:
        raise HTTPException(status_code=503, detail="WiFi manager not initialized")
        
    current_connection = wifi_manager.get_current_connection()
    is_hotspot_active = wifi_manager.is_hotspot_active()
    
    return WiFiStatus(
        connected=current_connection is not None,
        current_connection=current_connection,
        is_hotspot_active=is_hotspot_active
    )

@app.post("/api/connect", response_model=ActionResponse)
async def connect_to_network(credentials: WiFiCredentials) -> ActionResponse:
    """
    Connect to a WiFi network.
    """
    if not wifi_manager:
        raise HTTPException(status_code=503, detail="WiFi manager not initialized")
        
    logger.info(f"Connecting to network: {credentials.ssid}")
    
    # Check if we're in hotspot mode
    is_hotspot_active = wifi_manager.is_hotspot_active()
    
    # Attempt to connect with password if provided
    if credentials.password:
        success, error = await wifi_manager.connect_to_network_async(credentials.ssid, credentials.password)
    else:
        success, error = await wifi_manager.connect_to_network_async(credentials.ssid)
        
    if success:
        # Wait for connection to stabilize and get IP
        await asyncio.sleep(2)
        connection = wifi_manager.get_current_connection()
        
        if connection and "ip_address" in connection:
            ip_address = connection.get("ip_address", "Unknown")
        else:
            ip_address = "Unknown"
            
        # Include redirect URL to dashboard
        redirect_url = "/dashboard"
            
        return ActionResponse(
            success=True,
            message=f"Successfully connected to {credentials.ssid}",
            data={
                "previous_hotspot_active": is_hotspot_active,
                "ip_address": ip_address,
                "redirect_url": redirect_url
            }
        )
    else:
        return ActionResponse(
            success=False,
            message=f"Failed to connect: {error}" if error else "Failed to connect",
            data={
                "previous_hotspot_active": is_hotspot_active,
                "error_details": error,
                "ssid": credentials.ssid
            }
        )

@app.post("/api/forget", response_model=ActionResponse)
async def forget_network(credentials: WiFiCredentials) -> ActionResponse:
    """
    Forget a saved WiFi network.
    """
    if not wifi_manager:
        raise HTTPException(status_code=503, detail="WiFi manager not initialized")
        
    success = wifi_manager.forget_network(credentials.ssid)
    
    if success:
        return ActionResponse(
            success=True,
            message=f"Network {credentials.ssid} forgotten"
        )
    else:
        return ActionResponse(
            success=False,
            message=f"Failed to forget network {credentials.ssid}"
        )

@app.post("/api/hotspot/start", response_model=ActionResponse)
async def start_hotspot() -> ActionResponse:
    """
    Start the WiFi hotspot.
    """
    if not wifi_manager:
        raise HTTPException(status_code=503, detail="WiFi manager not initialized")
        
    success = wifi_manager.create_hotspot()
    
    if success:
        return ActionResponse(
            success=True,
            message="Hotspot started successfully"
        )
    else:
        return ActionResponse(
            success=False,
            message="Failed to start hotspot"
        )

@app.post("/api/hotspot/stop", response_model=ActionResponse)
async def stop_hotspot() -> ActionResponse:
    """
    Stop the WiFi hotspot.
    """
    if not wifi_manager:
        raise HTTPException(status_code=503, detail="WiFi manager not initialized")
        
    success = wifi_manager.stop_hotspot()
    
    if success:
        return ActionResponse(
            success=True,
            message="Hotspot stopped successfully"
        )
    else:
        return ActionResponse(
            success=False,
            message="Failed to stop hotspot"
        )

@app.post("/api/restart", response_model=ActionResponse)
async def restart_networking() -> ActionResponse:
    """
    Restart networking services.
    """
    if not wifi_manager:
        raise HTTPException(status_code=503, detail="WiFi manager not initialized")
        
    success = wifi_manager.restart_networking()
    
    if success:
        return ActionResponse(
            success=True,
            message="Networking restarted successfully"
        )
    else:
        return ActionResponse(
            success=False,
            message="Failed to restart networking"
        )

def cleanup():
    """
    Clean up resources before shutting down.
    """
    logger.info("Cleaning up resources...")
    
    # Stop WiFi manager tasks if needed
    # This is a placeholder for any WiFi manager cleanup
    
    # Stop server task if running
    global server_startup_task
    if server_startup_task:
        server_startup_task.cancel()
        
    logger.info("Cleanup complete")

def signal_handler(sig, frame):
    """
    Handle signals to gracefully shutdown.
    """
    logger.info(f"Received signal {sig}, shutting down...")
    cleanup()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def get_server_ip() -> str:
    """
    Get the server's IP address.
    """
    # Get the IP from WiFi manager if possible
    if wifi_manager:
        connection = wifi_manager.get_current_connection()
        if connection and "ip_address" in connection:
            return connection["ip_address"]
    return "0.0.0.0"  # Fallback

async def start_server(host: str = "0.0.0.0", port: int = 8080, hotspot_ssid: str = None, 
                       hotspot_password: str = None, enable_mdns: bool = True, service_name: str = None) -> None:
    """
    Start the WiFi configuration web server.
    
    Args:
        host: Host to bind the server to
        port: Port to bind the server to
        hotspot_ssid: SSID for the hotspot (optional)
        hotspot_password: Password for the hotspot (optional)
        enable_mdns: Enable mDNS service advertisement
        service_name: mDNS service name (optional, auto-generated if None)
    """
    global wifi_manager, mdns_service
    
    # Initialize WiFi manager
    wifi_manager = WiFiManager(
        hotspot_ssid=hotspot_ssid if hotspot_ssid else WiFiManager.DEFAULT_HOTSPOT_SSID,
        hotspot_password=hotspot_password if hotspot_password else WiFiManager.DEFAULT_HOTSPOT_PASSWORD
    )
    
    # Get device IP address for better logging
    device_ip = None
    connection = wifi_manager.get_current_connection()
    if connection and "ip_address" in connection:
        device_ip = connection["ip_address"]
    
    # If no IP found via WiFi connection, try to get local IP
    if not device_ip or device_ip == "Unknown":
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            device_ip = s.getsockname()[0]
            s.close()
        except:
            device_ip = "Unknown"
    
    # Prepare the config
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info"
    )
    
    # Create the server
    server = uvicorn.Server(config)
    
    # Start the mDNS service if enabled
    if enable_mdns:
        mdns_service = MDNSService(service_name=service_name)
        mdns_success = await mdns_service.start_service(port=port)
        
        if mdns_success:
            logger.info(f"Device accessible via: http://{mdns_service.service_name}.{mdns_service.domain}:{port}")
    
    # Log the server URLs
    if device_ip and device_ip != "Unknown":
        logger.info(f"Server accessible via: http://{device_ip}:{port}")
    else:
        logger.info(f"Server running on port {port}, but device IP address unknown")
        
    # Log if we're binding to all interfaces
    if host == "0.0.0.0":
        logger.info(f"Server bound to all network interfaces")
    
    # Run the server
    logger.info(f"Starting WiFi configuration server...")
    await server.serve()
    
    # Cleanup
    if mdns_service:
        await mdns_service.stop_service()

def run_server(host: str = "0.0.0.0", port: int = 8080, hotspot_ssid: str = None, 
               hotspot_password: str = None, enable_mdns: bool = True, service_name: str = "distiller") -> None:
    """
    Run the server in the main thread (blocking).
    
    Args:
        host: Host to bind the server to
        port: Port to bind the server to
        hotspot_ssid: SSID for the hotspot (optional)
        hotspot_password: Password for the hotspot (optional)
        enable_mdns: Enable mDNS service advertisement
        service_name: mDNS service name
    """
    asyncio.run(start_server(
        host=host, 
        port=port, 
        hotspot_ssid=hotspot_ssid, 
        hotspot_password=hotspot_password,
        enable_mdns=enable_mdns,
        service_name=service_name
    ))

async def start_server_background(host: str = "0.0.0.0", port: int = 8080, 
                                  hotspot_ssid: str = None, hotspot_password: str = None,
                                  enable_mdns: bool = True, service_name: str = "distiller") -> asyncio.Task:
    """
    Start the server in the background.
    
    Args:
        host: Host to bind the server to
        port: Port to bind the server to
        hotspot_ssid: SSID for the hotspot (optional)
        hotspot_password: Password for the hotspot (optional)
        enable_mdns: Enable mDNS service advertisement
        service_name: mDNS service name
        
    Returns:
        asyncio.Task: The server task
    """
    global server_startup_task
    
    # Create and start the task
    server_startup_task = asyncio.create_task(
        start_server(
            host=host, 
            port=port, 
            hotspot_ssid=hotspot_ssid, 
            hotspot_password=hotspot_password,
            enable_mdns=enable_mdns,
            service_name=service_name
        )
    )
    
    return server_startup_task

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run the server
    run_server() 