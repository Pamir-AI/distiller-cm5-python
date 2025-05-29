#!/usr/bin/env python3
"""
Run WiFi Configuration Web Server with mDNS support.
"""

import argparse
import logging
import sys
from .wifi_server import run_server

def main():
    """
    Run the WiFi configuration web server.
    """
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run WiFi Configuration Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind the server to")
    parser.add_argument("--hotspot-ssid", help="SSID for the hotspot")
    parser.add_argument("--hotspot-password", help="Password for the hotspot")
    parser.add_argument("--enable-mdns", action="store_true", default=True, help="Enable mDNS service advertisement")
    parser.add_argument("--service-name", default="distiller", help="mDNS service name")
    parser.add_argument("--start-hotspot", action="store_true", help="Start hotspot when server starts")
    
    args = parser.parse_args()
    
    logger.info(f"Starting WiFi configuration server on {args.host}:{args.port}")
    
    try:
        # Run the server
        run_server(
            host=args.host,
            port=args.port,
            hotspot_ssid=args.hotspot_ssid,
            hotspot_password=args.hotspot_password,
            enable_mdns=args.enable_mdns,
            service_name=args.service_name
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by keyboard interrupt")
    except Exception as e:
        logger.error(f"Error running server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 