#!/usr/bin/env python3
"""
WiFi Setup Launcher
-------------------
This script launches the WiFi setup web interface.
It creates a WiFi hotspot and starts a web server for configuring WiFi.
"""

import os
import sys
from pathlib import Path

# Ensure the distiller_cm5_python package is in the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Import the WiFi configuration server
from distiller_cm5_python.utils.network.wifi_config_cli import main

if __name__ == "__main__":
    # Make the script executable
    if os.name != "nt":  # Not Windows
        try:
            os.chmod(__file__, 0o755)
        except:
            pass
    
    # Run the WiFi configuration server
    main() 