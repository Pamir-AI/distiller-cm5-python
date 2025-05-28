#!/usr/bin/env python3
"""
Command-line interface for WiFi configuration.
"""

import os
import sys
import argparse
import logging
import signal
from pathlib import Path

# Add parent directory to path to allow importing wifi_server
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from distiller_cm5_python.utils.network.wifi_server import run_server
from distiller_cm5_python.utils.network.wifi_manager import WiFiManager

def setup_logging(verbose=False):
    """
    Set up logging.
    
    Args:
        verbose: Whether to enable verbose logging
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

def signal_handler(sig, frame):
    """
    Handle signals for graceful shutdown.
    """
    print("\nShutting down WiFi configuration server...")
    sys.exit(0)

def main():
    """
    Main entry point.
    """
    parser = argparse.ArgumentParser(description="WiFi Configuration Server")
    
    parser.add_argument(
        "--host", 
        type=str, 
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port", 
        type=int, 
        default=8080,
        help="Port to bind the server to (default: 8080)"
    )
    
    parser.add_argument(
        "--ssid", 
        type=str, 
        default=WiFiManager.DEFAULT_HOTSPOT_SSID,
        help=f"SSID for the hotspot (default: {WiFiManager.DEFAULT_HOTSPOT_SSID})"
    )
    
    parser.add_argument(
        "--password", 
        type=str, 
        default=WiFiManager.DEFAULT_HOTSPOT_PASSWORD,
        help=f"Password for the hotspot (default: {WiFiManager.DEFAULT_HOTSPOT_PASSWORD})"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the server
    print(f"Starting WiFi configuration server at http://{args.host}:{args.port}")
    print(f"Hotspot SSID: {args.ssid}, Password: {args.password}")
    print("Press Ctrl+C to stop the server")
    
    run_server(
        host=args.host,
        port=args.port,
        hotspot_ssid=args.ssid,
        hotspot_password=args.password
    )

if __name__ == "__main__":
    main() 