#!/bin/bash
# Google Coral TPU Setup Script
# Installs Edge TPU runtime and libraries

echo "==========================================="
echo "Robot PK - Google Coral TPU Setup"
echo "==========================================="

# Add Coral repository
echo "Adding Coral repository..."
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list

# Add GPG key
echo "Adding GPG key..."
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -

# Update package list
echo "Updating package list..."
sudo apt update

# Install Edge TPU runtime
echo "Installing Edge TPU runtime..."
sudo apt install -y libedgetpu1-std

# Install Python bindings
echo "Installing Python bindings..."
sudo apt install -y python3-pycoral
pip3 install --upgrade pycoral

echo ""
echo "TPU setup complete!"
echo "Download model with: ./scripts/download_models.sh"
