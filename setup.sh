#!/bin/bash

# Update package list
sudo apt update -y

# Install necessary system dependencies
sudo apt install -y python3 python3-pip python3-venv

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install required Python packages
pip install -r requirements.txt

# Make script executable
chmod +x setup.sh

echo "Setup complete! To run the server, activate the virtual environment and run app.py:"
echo "source venv/bin/activate && python app.py"
