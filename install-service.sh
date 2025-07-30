#!/bin/bash

# Install script for distiller-cm5-python-gui systemd service

set -e

SERVICE_NAME="distiller-cm5-python-gui.service"
SERVICE_FILE="/opt/distiller-cm5-python/debian/${SERVICE_NAME}"
SYSTEMD_DIR="/etc/systemd/system"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Check if service file exists
if [ ! -f "${SERVICE_FILE}" ]; then
    echo "Error: Service file not found at ${SERVICE_FILE}"
    exit 1
fi

echo "Installing ${SERVICE_NAME}..."

# Copy service file to systemd directory
cp "${SERVICE_FILE}" "${SYSTEMD_DIR}/"

# Reload systemd daemon
systemctl daemon-reload

# Enable service to start on boot
systemctl enable "${SERVICE_NAME}"

# Start the service
systemctl start "${SERVICE_NAME}"

# Check service status
if systemctl is-active --quiet "${SERVICE_NAME}"; then
    echo "✓ Service installed and started successfully"
    echo ""
    echo "Useful commands:"
    echo "  systemctl status ${SERVICE_NAME}  # Check service status"
    echo "  systemctl stop ${SERVICE_NAME}    # Stop service"
    echo "  systemctl restart ${SERVICE_NAME} # Restart service"
    echo "  journalctl -u ${SERVICE_NAME} -f  # View logs"
else
    echo "⚠ Service installed but failed to start"
    echo "Check logs with: journalctl -u ${SERVICE_NAME} -n 50"
    exit 1
fi