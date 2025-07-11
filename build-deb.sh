#!/bin/bash

# Debian Package Builder for distiller-cm5-python
# This script builds a Debian package for the Distiller CM5 Python AI Assistant

set -e

# Configuration
PACKAGE_NAME="distiller-cm5-python"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
DIST_DIR="$SCRIPT_DIR/dist"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# Function to display script usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -c, --clean             Clean build directory and artifacts before building"
    echo "  --clean-only            Clean build directory and artifacts, then exit"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -a, --architecture ARCH Set target architecture (default: any)"
    echo "  --no-sign               Skip package signing"
    echo "  --source-only           Build source package only"
    echo "  --binary-only           Build binary package only"
    echo ""
    echo "Examples:"
    echo "  $0                      Build package with default settings"
    echo "  $0 --clean              Clean build directory and build package"
    echo "  $0 --clean-only         Clean build directory and exit"
    echo "  $0 --verbose            Build with verbose output"
    echo "  $0 --architecture all   Build for all architectures"
    echo ""
}

# Function to check system requirements
check_requirements() {
    log_step "Checking system requirements..."
    
    # Check if we're on a Debian-based system
    if ! command -v dpkg &> /dev/null; then
        log_error "This script requires a Debian-based system with dpkg."
        exit 1
    fi
    
    # Check for required packages
    local required_packages=(
        "debhelper"
        "dh-python"
        "python3-setuptools"
        "python3-dev"
        "build-essential"
        "devscripts"
        "lintian"
    )
    
    local missing_packages=()
    for package in "${required_packages[@]}"; do
        if ! dpkg -l | grep -q "^ii.*$package"; then
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        log_error "Missing required packages: ${missing_packages[*]}"
        log_info "Install them with: sudo apt install ${missing_packages[*]}"
        exit 1
    fi
    
    # Check for Python 3.12+
    if ! python3 --version | grep -q "3\.\(1[2-9]\|[2-9][0-9]\)"; then
        log_error "Python 3.12 or higher is required."
        exit 1
    fi
    
    log_success "System requirements check passed."
}

# Function to validate project structure
validate_project() {
    log_step "Validating project structure..."
    
    local required_files=(
        "main.py"
        "pyproject.toml"
        "requirements.txt"
        "README.md"
        "CLAUDE.md"
        "distiller_cm5_python/__init__.py"
        "debian/control"
        "debian/rules"
        "debian/changelog"
        "debian/copyright"
    )
    
    local missing_files=()
    for file in "${required_files[@]}"; do
        if [ ! -f "$SCRIPT_DIR/$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        log_error "Missing required files: ${missing_files[*]}"
        exit 1
    fi
    
    log_success "Project structure validation passed."
}

# Function to clean build directory and artifacts
clean_build() {
    log_step "Cleaning build directory and artifacts..."
    
    # Clean build and dist directories
    if [ -d "$BUILD_DIR" ]; then
        rm -rf "$BUILD_DIR"
        log_success "Build directory cleaned."
    else
        log_info "Build directory doesn't exist, nothing to clean."
    fi
    
    if [ -d "$DIST_DIR" ]; then
        rm -rf "$DIST_DIR"
        log_success "Distribution directory cleaned."
    fi
    
    # Clean Python cache files
    find "$SCRIPT_DIR" -name "*.pyc" -delete 2>/dev/null || true
    find "$SCRIPT_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    log_info "Python cache files cleaned."
    
    # Clean uv cache
    rm -rf "$SCRIPT_DIR/.uv_cache" 2>/dev/null || true
    log_info "UV cache cleaned."
    
    # Clean debian build artifacts
    rm -rf "$SCRIPT_DIR/debian/.debhelper" 2>/dev/null || true
    rm -f "$SCRIPT_DIR/debian/debhelper-build-stamp" 2>/dev/null || true
    rm -f "$SCRIPT_DIR/debian/files" 2>/dev/null || true
    rm -rf "$SCRIPT_DIR/debian/distiller-cm5-python" 2>/dev/null || true
    rm -rf "$SCRIPT_DIR/debian/tmp" 2>/dev/null || true
    rm -f "$SCRIPT_DIR/debian"/*.substvars 2>/dev/null || true
    rm -f "$SCRIPT_DIR/debian"/*.debhelper 2>/dev/null || true
    rm -f "$SCRIPT_DIR/debian"/*.debhelper.log 2>/dev/null || true
    log_info "Debian build artifacts cleaned."
    
    # Clean generated package files in root directory
    rm -f "$SCRIPT_DIR"/*.deb "$SCRIPT_DIR"/*.changes "$SCRIPT_DIR"/*.buildinfo "$SCRIPT_DIR"/*.dsc "$SCRIPT_DIR"/*.tar.* 2>/dev/null || true
    log_info "Generated package files cleaned."
    
    log_success "All build artifacts and temporary files cleaned."
}

# Function to prepare build environment
prepare_build() {
    log_step "Preparing build environment..."
    
    # Create build and dist directories
    mkdir -p "$BUILD_DIR" "$DIST_DIR"
    
    # Ensure proper permissions on debian files
    chmod +x "$SCRIPT_DIR/debian/rules"
    chmod +x "$SCRIPT_DIR/debian/postinst"
    chmod +x "$SCRIPT_DIR/debian/prerm"
    chmod +x "$SCRIPT_DIR/debian/postrm"
    
    log_success "Build environment prepared."
}

# Function to build the package
build_package() {
    log_step "Building Debian package..."
    
    cd "$SCRIPT_DIR"
    
    # Build package based on options
    local build_cmd="dpkg-buildpackage"
    
    if [ "$ARCHITECTURE" != "any" ]; then
        build_cmd="$build_cmd -a$ARCHITECTURE"
    fi
    
    if [ "$NO_SIGN" = "true" ]; then
        build_cmd="$build_cmd -us -uc"
    fi
    
    # Skip dependency checks for cross-building
    build_cmd="$build_cmd -d"
    
    if [ "$SOURCE_ONLY" = "true" ]; then
        build_cmd="$build_cmd -S"
    elif [ "$BINARY_ONLY" = "true" ]; then
        build_cmd="$build_cmd -b"
    fi
    
    if [ "$VERBOSE" = "true" ]; then
        build_cmd="$build_cmd -v"
    fi
    
    log_info "Executing: $build_cmd"
    
    # Execute build command
    if $build_cmd; then
        log_success "Package built successfully."
    else
        log_error "Package build failed."
        exit 1
    fi
    
    # Move generated files to dist directory
    mv ../*.deb "$DIST_DIR/" 2>/dev/null || true
    mv ../*.changes "$DIST_DIR/" 2>/dev/null || true
    mv ../*.buildinfo "$DIST_DIR/" 2>/dev/null || true
    mv ../*.tar.* "$DIST_DIR/" 2>/dev/null || true
    mv ../*.dsc "$DIST_DIR/" 2>/dev/null || true
    
    log_success "Package files moved to $DIST_DIR/"
}

# Function to run package linting
lint_package() {
    log_step "Running package linting..."
    
    local deb_file=$(find "$DIST_DIR" -name "*.deb" -type f | head -n 1)
    
    if [ -f "$deb_file" ]; then
        log_info "Linting package: $(basename "$deb_file")"
        
        if lintian "$deb_file"; then
            log_success "Package linting passed."
        else
            log_warning "Package linting found issues. Check the output above."
        fi
    else
        log_warning "No .deb file found for linting."
    fi
}

# Function to display build summary
show_build_summary() {
    log_step "Build Summary"
    
    echo ""
    echo "Package: $PACKAGE_NAME"
    echo "Architecture: $ARCHITECTURE"
    echo "Build Directory: $BUILD_DIR"
    echo "Distribution Directory: $DIST_DIR"
    echo ""
    
    if [ -d "$DIST_DIR" ]; then
        echo "Generated Files:"
        ls -la "$DIST_DIR/"
        echo ""
        
        local deb_file=$(find "$DIST_DIR" -name "*.deb" -type f | head -n 1)
        if [ -f "$deb_file" ]; then
            echo "Package Information:"
            dpkg-deb --info "$deb_file"
            echo ""
            echo "Package Contents:"
            dpkg-deb --contents "$deb_file"
            echo ""
        fi
    fi
    
    log_success "Build completed successfully!"
    echo ""
    echo "To install the package, run:"
    echo "  sudo dpkg -i $DIST_DIR/*.deb"
    echo "  sudo apt-get install -f  # Fix any dependency issues"
    echo ""
}

# Parse command line arguments
CLEAN=false
CLEAN_ONLY=false
VERBOSE=false
ARCHITECTURE="any"
NO_SIGN=true
SOURCE_ONLY=false
BINARY_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -c|--clean)
            CLEAN=true
            shift
            ;;
        --clean-only)
            CLEAN_ONLY=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -a|--architecture)
            ARCHITECTURE="$2"
            shift 2
            ;;
        --no-sign)
            NO_SIGN=true
            shift
            ;;
        --source-only)
            SOURCE_ONLY=true
            shift
            ;;
        --binary-only)
            BINARY_ONLY=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    log_info "Starting Debian package build for $PACKAGE_NAME..."
    echo ""
    
    # Handle clean-only mode
    if [ "$CLEAN_ONLY" = "true" ]; then
        clean_build
        log_success "Clean-only operation completed successfully!"
        return 0
    fi
    
    # Run build steps
    check_requirements
    validate_project
    
    if [ "$CLEAN" = "true" ]; then
        clean_build
    fi
    
    prepare_build
    build_package
    lint_package
    show_build_summary
    
    log_success "Build script completed successfully!"
}

# Execute main function
main "$@"
