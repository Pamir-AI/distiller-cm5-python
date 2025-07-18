#!/bin/bash

# Function to show usage
show_usage() {
    echo "Usage: ./run.sh [options]"
    echo "Options:"
    echo "  --gui    Launch the GUI interface instead of CLI"
    echo "  -h, --help    Display this help message"
    echo ""
    echo "All other options are passed directly to main.py"
}

# Check for help flag
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    show_usage
    exit 0
fi

# Activate the virtual environment
source .venv/bin/activate

# Check if activation was successful
if [ $? -ne 0 ]; then
  echo "Failed to activate virtual environment."
  exit 1
fi

# Add the current directory to PYTHONPATH
export PYTHONPATH="$PWD:$PYTHONPATH"

# Run the main Python script
echo "Running main.py..."
python main.py --gui "$@"

# Deactivate the virtual environment (optional, runs when script exits)
# deactivate 
