#!/usr/bin/env python3
"""
Example script demonstrating how to use the WiFi setup functionality.
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Add the parent directory to the Python path
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the WiFi manager and server
from distiller_cm5_python.utils.network import WiFiManager, run_server

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

def wifi_manager_example():
    """
    Example of using the WiFi manager directly.
    """
    print("==== WiFi Manager Example ====")
    
    # Create a WiFi manager instance
    wifi_manager = WiFiManager()
    
    # Get the WiFi interface
    interface = wifi_manager.get_wifi_interface()
    print(f"WiFi interface: {interface}")
    
    # Check if the hotspot is active
    is_active = wifi_manager.is_hotspot_active()
    print(f"Hotspot active: {is_active}")
    
    # Get the current connection
    connection = wifi_manager.get_current_connection()
    if connection:
        print(f"Connected to: {connection['ssid']}")
        print(f"IP address: {connection.get('ip_address', 'Unknown')}")
        print(f"Is hotspot: {connection.get('is_hotspot', False)}")
    else:
        print("Not connected to any network")
    
    # Scan for available networks
    print("\nScanning for networks...")
    networks = wifi_manager.scan_networks()
    
    print(f"Found {len(networks)} networks:")
    for i, network in enumerate(networks[:5], 1):  # Show only the first 5 networks
        print(f"{i}. {network['ssid']} (Signal: {network['signal']}, Security: {network['security']})")
    
    # Example of creating a hotspot (commented out to avoid disrupting existing connections)
    """
    print("\nCreating hotspot...")
    success = wifi_manager.create_hotspot()
    if success:
        print("Hotspot created successfully")
    else:
        print("Failed to create hotspot")
    """
    
    # Example of connecting to a network (commented out to avoid disrupting existing connections)
    """
    print("\nConnecting to a network...")
    ssid = "MyNetwork"
    password = "mypassword"
    success = wifi_manager.connect_to_network(ssid, password)
    if success:
        print(f"Connected to {ssid} successfully")
    else:
        print(f"Failed to connect to {ssid}")
    """

def main():
    """
    Main entry point.
    """
    parser = argparse.ArgumentParser(description="WiFi Setup Example")
    
    parser.add_argument(
        "--server",
        action="store_true",
        help="Run the WiFi setup server"
    )
    
    args = parser.parse_args()
    
    if args.server:
        # Run the WiFi setup server
        print("Starting WiFi setup server...")
        run_server()
    else:
        # Run the WiFi manager example
        wifi_manager_example()

if __name__ == "__main__":
    main() 