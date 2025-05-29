# WiFi Configuration Server

This module provides a web interface for configuring WiFi connections on the Distiller CM5 device. It includes mDNS (Multicast DNS) support for accessing the device using a `.local` domain name instead of an IP address.

## Features

- WiFi network scanning and connection
- Hotspot creation for initial setup
- mDNS service advertisement (`distiller.local`)
- Dashboard web UI for device interaction
- Support for Linux and macOS platforms

## Requirements

Required Python libraries:
- fastapi
- uvicorn
- pydantic
- zeroconf (for mDNS support)

## Usage

### Starting the WiFi Configuration Server

```python
from distiller_cm5_python.utils.network.wifi_server import run_server

# Start the server with default settings
run_server()

# Or with custom settings
run_server(
    host="0.0.0.0",
    port=8080,
    hotspot_ssid="DistillerSetup",
    hotspot_password="distiller123",
    enable_mdns=True,
    service_name="distiller"
)
```

### Command Line Interface

You can also run the server using the provided command-line script:

```bash
python -m distiller_cm5_python.utils.network.run_wifi_server --port 8080 --enable-mdns --service-name distiller
```

### Accessing the Web Interface

Once the server is running, you can access the web interface using:

- IP address: `http://<device-ip>:8080`
- mDNS domain (if supported): `http://distiller.local:8080`

## mDNS Support

The mDNS service advertises the web server as `distiller.local` on your local network. This allows users to access the device without knowing its IP address.

For clients to connect using the `.local` domain, they need mDNS support:

- Windows: Install Bonjour or iTunes (includes Bonjour)
- macOS: Built-in support
- Linux: Avahi daemon (installed by default on most distributions)
- iOS: Built-in support
- Android: Limited support, may require additional apps

## Dashboard UI

After connecting to a WiFi network, users will be redirected to the dashboard UI, which provides:

- Device information
- WiFi connection status
- Voice assistant interface
- System status

The dashboard UI is designed to mimic the look and feel of the QML-based UI on the Distiller CM5 device.

## API Endpoints

- `GET /`: WiFi configuration page
- `GET /dashboard`: Dashboard UI after successful connection
- `GET /api/networks`: List available WiFi networks
- `GET /api/status`: Get current WiFi connection status
- `POST /api/connect`: Connect to a WiFi network
- `POST /api/forget`: Forget a saved WiFi network
- `POST /api/hotspot/start`: Start the WiFi hotspot
- `POST /api/hotspot/stop`: Stop the WiFi hotspot
- `POST /api/restart`: Restart networking services 