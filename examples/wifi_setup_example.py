#!/usr/bin/env python3
"""
WiFi Setup Example
This example demonstrates how to use the WiFi configuration server with mDNS support.
"""

import argparse
import logging
import asyncio
import sys
import signal
import os
from pathlib import Path

# Add the parent directory to the Python path
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from distiller_cm5_python.utils.network.wifi_server import run_server, start_server_background
from distiller_cm5_python.utils.network.wifi_manager import WiFiManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

async def run_async_example():
    """
    Run an async example that starts the server in the background
    and performs some other operations.
    """
    logger.info("Starting WiFi setup server in the background...")
    
    # Start server in the background
    server_task = await start_server_background(
        port=8080,
        enable_mdns=True,
        # Using auto-generated service name based on device hostname
        service_name=None
    )
    
    try:
        # Create a WiFi manager instance
        wifi_manager = WiFiManager()
        
        # Example: Get current connection
        connection = wifi_manager.get_current_connection()
        if connection:
            logger.info(f"Currently connected to: {connection['ssid']}")
            logger.info(f"IP address: {connection['ip_address']}")
        else:
            logger.info("Not connected to any WiFi network")
        
        # Example: Scan networks
        logger.info("Scanning for WiFi networks...")
        networks = wifi_manager.scan_networks()
        
        if networks:
            logger.info(f"Found {len(networks)} WiFi networks:")
            for i, network in enumerate(networks[:5]):  # Show top 5 networks
                logger.info(f"  {i+1}. {network['ssid']} (Signal: {network['signal']}%)")
            
            if len(networks) > 5:
                logger.info(f"  ... and {len(networks) - 5} more networks")
        else:
            logger.info("No WiFi networks found")
        
        # Keep running until interrupted
        logger.info("WiFi setup server is running. Press Ctrl+C to stop.")
        
        while True:
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        logger.info("Example was cancelled")
    except Exception as e:
        logger.error(f"Error in async example: {e}")
    finally:
        # Cancel the server task if it's still running
        if not server_task.done():
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
        logger.info("Server stopped")

def signal_handler(sig, frame):
    """
    Handle termination signals.
    """
    logger.info("Received signal to terminate, stopping...")
    sys.exit(0)

def main():
    """
    Main entry point.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="WiFi Setup Example")
    parser.add_argument("--server", action="store_true", help="Run only the server")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind the server to")
    parser.add_argument("--no-mdns", action="store_true", help="Disable mDNS service advertisement")
    parser.add_argument("--service-name", default=None, help="mDNS service name (default: auto-generated from hostname)")
    
    args = parser.parse_args()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if args.server:
        # Run only the server
        logger.info("Starting WiFi setup server...")
        run_server(
            port=args.port,
            enable_mdns=not args.no_mdns,
            service_name=args.service_name
        )
    else:
        # Run the async example
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(run_async_example())
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            loop.close()

if __name__ == "__main__":
    main() 