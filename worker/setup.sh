#!/bin/bash

# Setup script for the participant service agent

# Exit on error
set -e

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Create logs directory if it doesn't exist
mkdir -p logs

# Setup complete
echo "Setup complete! Activate the virtual environment with 'source venv/bin/activate'"
