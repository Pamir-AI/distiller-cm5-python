#!/bin/bash
# Install dependencies for WiFi setup functionality

# Exit on error
set -e

echo "Installing dependencies for WiFi setup functionality..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
	echo "Please run as root (sudo $0)"
	exit 1
fi

# Install NetworkManager if not already installed
if ! command -v nmcli &>/dev/null && command -v apt-get &>/dev/null; then
	echo "Installing NetworkManager..."
	apt-get update
	apt-get install -y network-manager
fi

# Install Python dependencies
echo "Installing Python dependencies..."

# Source the virtual environment if it exists
CUR_DIR=$(pwd)
if [ -d "$CUR_DIR/.venv" ]; then
	echo "Activating virtual environment..."
	source "$CUR_DIR/.venv/bin/activate"
else
	echo "No virtual environment found. Proceeding without it."
	exit 1
fi

uv pip install fastapi uvicorn pydantic

# Install the systemd service
echo "Installing systemd service..."
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$script_dir/distiller-wifi-setup.service" /etc/systemd/system/
# Update the path in the service file
sed -i "s|/home/utsav/dev/pamir-ai/distiller-cm5-python|$script_dir|g" /etc/systemd/system/distiller-wifi-setup.service

# Make wifi_setup.py executable
chmod +x "$script_dir/wifi_setup.py"

# Enable the service
echo "Enabling the service..."
systemctl daemon-reload
systemctl enable distiller-wifi-setup.service

echo "Installation complete!"
echo "You can start the service with: sudo systemctl start distiller-wifi-setup.service"
echo "You can check the status with: sudo systemctl status distiller-wifi-setup.service"
