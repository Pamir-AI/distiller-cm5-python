#!/bin/bash

# Script Name: build-deb.sh
# Description: Build the distiller-cm5-python Debian package
# Usage: ./build-deb.sh [clean]

set -e

# Configuration
PACKAGE_NAME="distiller-cm5-python"
DIST_DIR="dist"
TARGET_ARCHITECTURES="arm64"

# Function to check if command exists
command_exists() {
	command -v "$1" >/dev/null 2>&1
}

# Parse arguments
CLEAN_BUILD=false

for arg in "$@"; do
	case $arg in
	clean)
		CLEAN_BUILD=true
		shift
		;;
	*)
		echo "Unknown option: $arg"
		echo "Usage: $0 [clean]"
		exit 1
		;;
	esac
done

echo "[INFO] Building distiller-cm5-python Debian package..."

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] || [ ! -d "debian" ]; then
	echo "[ERROR] This script must be run from the distiller-cm5-python root directory"
	exit 1
fi

# Check for required tools
check_command() {
	if ! command -v "$1" &>/dev/null; then
		echo "[ERROR] Required command '$1' not found. Please install it first."
		exit 1
	fi
}

echo "[INFO] Checking build dependencies..."
check_command "dpkg-buildpackage"

# Clean previous builds if requested
if [ "$CLEAN_BUILD" = true ]; then
	echo "[INFO] Cleaning previous builds..."
	sudo rm -rf build/ dist/ *.egg-info/ .venv/
	sudo rm -f ../distiller-cm5-python_*.deb ../distiller-cm5-python_*.dsc ../distiller-cm5-python_*.tar.gz ../distiller-cm5-python_*.changes ../distiller-cm5-python_*.buildinfo
	sudo rm -f distiller-cm5-python_*.deb distiller-cm5-python_*.dsc distiller-cm5-python_*.tar.gz distiller-cm5-python_*.changes
	sudo rm -f distiller_cm5_python-*.whl distiller_cm5_python-*.tar.gz
	sudo debian/rules clean || true
	echo "[INFO] Clean complete."
	exit 0
fi

# Temporarily move model files to avoid including them in the package
echo "[INFO] Temporarily moving model files to avoid packaging..."
MODEL_BACKUP_DIR=$(mktemp -d)
find distiller_cm5_python/llm_server/models -name "*.gguf" -exec mv {} "$MODEL_BACKUP_DIR/" \; 2>/dev/null || true
echo "[INFO] Model files moved to: $MODEL_BACKUP_DIR"

# Generate uv.lock file for the package (if uv is available)
if command -v uv >/dev/null 2>&1; then
	echo "[INFO] Generating uv.lock file..."
	uv lock --python python3.11
	echo "[INFO] uv.lock file generated successfully"
else
	echo "[INFO] uv not available, skipping lockfile generation (using existing uv.lock if present)"
fi

# Build Debian package
print_status() {
	echo -e "[INFO] $1"
}

print_success() {
	echo -e "[SUCCESS] $1"
}

print_warning() {
	echo -e "[WARNING] $1"
}

print_error() {
	echo -e "[ERROR] $1"
}

print_status "Building Debian package for $PACKAGE_NAME"

export DEB_BUILD_OPTIONS="parallel=$(nproc)"

# Build for ARM64 architecture
for arch in $TARGET_ARCHITECTURES; do
	print_status "Building for architecture: $arch ..."

	# Use -d flag to skip dependency checks (cross-compilation)
	dpkg-buildpackage -us -uc -b -d -a$arch
done

# Organize build artifacts
mkdir -p "$DIST_DIR"
for arch in $TARGET_ARCHITECTURES; do
	for file in ../${PACKAGE_NAME}_*_${arch}.deb; do
		if [ -f "$file" ]; then
			mv -f "$file" "$DIST_DIR/"
			DEB_BASENAME=$(basename "$file")
			print_status "Package moved: $DIST_DIR/$DEB_BASENAME"
			# Show package info
			print_status "Package contents ($DEB_BASENAME):"
			dpkg -c "$DIST_DIR/$DEB_BASENAME" | head -20
			echo "..."
			print_status "Package information ($DEB_BASENAME):"
			dpkg -I "$DIST_DIR/$DEB_BASENAME"
		fi
	done
done

# Clean up any other .deb files in parent directory
for file in ../${PACKAGE_NAME}_*.deb; do
	if [[ "$file" != *"_all.deb" && "$file" != *"_arm64.deb" ]]; then
		rm -f "$file"
	fi
done

# Restore model files after packaging
echo "[INFO] Restoring model files..."
find "$MODEL_BACKUP_DIR" -name "*.gguf" -exec mv {} distiller_cm5_python/llm_server/models/ \; 2>/dev/null || true
rm -rf "$MODEL_BACKUP_DIR"
echo "[INFO] Model files restored"

print_success "Build process completed successfully!"

# Show final status
if [ -d "$DIST_DIR" ] && [ "$(ls -A "$DIST_DIR" 2>/dev/null)" ]; then
	echo
	print_status "Generated packages:"
	ls -la "$DIST_DIR/"
	echo
	print_status "To install the package, run:"
	echo "  sudo dpkg -i $DIST_DIR/${PACKAGE_NAME}_*_arm64.deb"
	echo "  sudo apt-get install -f  # Fix any dependency issues"
fi