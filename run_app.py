#!/bin/bash
# Navigate to the project directory (adjust if needed)
cd "$(dirname "$0")"
# Activate the virtual environment
source powdercoatenv/bin/activate
# Run the app using the virtual environment's Python interpreter with sudo and preserve environment variables.
sudo -E ./powdercoatenv/bin/python3 app.py
