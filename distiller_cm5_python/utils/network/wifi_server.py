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
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

from .wifi_manager import WiFiManager

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

# Initialize WiFi manager
wifi_manager = None

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
            
        return ActionResponse(
            success=True,
            message=f"Successfully connected to {credentials.ssid}",
            data={
                "previous_hotspot_active": is_hotspot_active,
                "ip_address": ip_address
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
            message="Networking services restarted successfully"
        )
    else:
        return ActionResponse(
            success=False,
            message="Failed to restart networking services"
        )

# Signal handlers and cleanup function
def cleanup():
    """
    Cleanup resources before exiting.
    Stop the hotspot if it's running.
    """
    global wifi_manager
    
    logger.info("Cleaning up resources...")
    
    if wifi_manager:
        if wifi_manager.is_hotspot_active():
            logger.info("Stopping hotspot before exit...")
            wifi_manager.stop_hotspot()
    
    logger.info("Cleanup complete")

def signal_handler(sig, frame):
    """
    Handle termination signals.
    """
    logger.info(f"Received signal {sig}, shutting down...")
    cleanup()
    sys.exit(0)

# Server functions
def get_server_ip() -> str:
    """
    Get the IP address of the server when in hotspot mode.
    """
    # Default IP when in hotspot mode
    return "10.42.0.1"

async def start_server(host: str = "0.0.0.0", port: int = 8080, hotspot_ssid: str = None, 
                       hotspot_password: str = None) -> None:
    """
    Start the WiFi configuration server.
    
    Args:
        host: Host to bind the server to
        port: Port to bind the server to
        hotspot_ssid: SSID for the hotspot
        hotspot_password: Password for the hotspot
    """
    global wifi_manager
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize WiFi manager with proper defaults
    wifi_manager = WiFiManager(
        hotspot_ssid=hotspot_ssid if hotspot_ssid is not None else WiFiManager.DEFAULT_HOTSPOT_SSID,
        hotspot_password=hotspot_password if hotspot_password is not None else WiFiManager.DEFAULT_HOTSPOT_PASSWORD
    )
    
    # Start hotspot
    if not wifi_manager.is_hotspot_active():
        # Create hotspot
        success = wifi_manager.create_hotspot()
        if not success:
            logger.error("Failed to start hotspot")
            return
    
    # Get server IP
    server_ip = get_server_ip()
    
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    logger.info(f"Starting WiFi configuration server at http://{server_ip}:{port}")
    logger.info(f"Hotspot SSID: {wifi_manager.hotspot_ssid}, Password: {wifi_manager.hotspot_password}")
    
    try:
        await server.serve()
    finally:
        # Ensure cleanup happens if the server stops
        cleanup()

def run_server(host: str = "0.0.0.0", port: int = 8080, hotspot_ssid: str = None, 
               hotspot_password: str = None) -> None:
    """
    Run the WiFi configuration server in the main thread.
    
    Args:
        host: Host to bind the server to
        port: Port to bind the server to
        hotspot_ssid: SSID for the hotspot
        hotspot_password: Password for the hotspot
    """
    try:
        asyncio.run(start_server(host, port, hotspot_ssid, hotspot_password))
    except KeyboardInterrupt:
        logger.info("Server stopped by keyboard interrupt")
    finally:
        # Ensure cleanup happens on normal exit
        cleanup()

async def start_server_background(host: str = "0.0.0.0", port: int = 8080, 
                                  hotspot_ssid: str = None, hotspot_password: str = None) -> asyncio.Task:
    """
    Start the WiFi configuration server in the background.
    
    Args:
        host: Host to bind the server to
        port: Port to bind the server to
        hotspot_ssid: SSID for the hotspot
        hotspot_password: Password for the hotspot
        
    Returns:
        asyncio.Task: The server task
    """
    global server_startup_task
    
    server_startup_task = asyncio.create_task(
        start_server(host, port, hotspot_ssid, hotspot_password)
    )
    
    # Register at-exit cleanup
    import atexit
    atexit.register(cleanup)
    
    return server_startup_task

# Main entry point
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    run_server() 