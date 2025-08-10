#!/bin/bash
# Simple WiFi Captive Portal Setup Script
# Back to basics - port 5000, no complex DNS/captive detection

set -e

echo "================================="
echo "Simple WiFi Captive Portal Setup"
echo "================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root (use sudo)"
    exit 1
fi

# Update system packages
echo "Updating system packages..."
apt update

# Install required system packages
echo "Installing required packages..."
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    network-manager \
    iptables \
    iw \
    net-tools

# Check if NetworkManager is running
echo "Checking NetworkManager status..."
systemctl enable NetworkManager
systemctl start NetworkManager

# Stop and disable conflicting services that might interfere
echo "Stopping conflicting services..."
systemctl stop hostapd || true
systemctl disable hostapd || true
systemctl stop dnsmasq || true
systemctl disable dnsmasq || true

# Create application directory
APP_DIR="/opt/wifi-captive-portal"
echo "Creating application directory at $APP_DIR..."
mkdir -p "$APP_DIR"

# Create Python virtual environment
echo "Creating Python virtual environment..."
python3 -m venv "$APP_DIR/venv"

# Activate virtual environment and install Python packages
echo "Installing Python dependencies..."
source "$APP_DIR/venv/bin/activate"
pip install --upgrade pip
pip install Flask==2.3.3 Werkzeug==2.3.7

# Check if wifi_connect.py exists in current directory
if [ -f "wifi_connect.py" ]; then
    echo "Copying wifi_connect.py to $APP_DIR..."
    cp wifi_connect.py "$APP_DIR/"
else
    echo "ERROR: wifi_connect.py not found in current directory!"
    echo "Please make sure wifi_connect.py is in the same directory as this setup script."
    exit 1
fi

# Make the application executable
chmod +x "$APP_DIR/wifi_connect.py"

# Create simple systemd service file
echo "Creating systemd service..."
cat > "/etc/systemd/system/wifi-captive-portal.service" << EOF
[Unit]
Description=Simple WiFi Captive Portal
After=network.target NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/wifi_connect.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Create a simple launcher script
cat > "$APP_DIR/start_portal.sh" << EOF
#!/bin/bash
echo "Starting Simple WiFi Captive Portal..."
cd "$APP_DIR"
source venv/bin/activate
python3 wifi_connect.py
EOF
chmod +x "$APP_DIR/start_portal.sh"

# Configure NetworkManager
echo "Configuring NetworkManager..."
cat > "/etc/NetworkManager/conf.d/wifi-captive-portal.conf" << EOF
[device]
wifi.scan-rand-mac-address=no

[connection]
wifi.powersave=2
EOF

# Enable IP forwarding
echo "Enabling IP forwarding..."
if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf; then
    echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
fi
sysctl -p

# Detect the main internet interface
INTERNET_IFACE=$(ip route | grep default | head -n1 | awk '{print $5}')
if [ -z "$INTERNET_IFACE" ]; then
    INTERNET_IFACE="eth0"  # fallback
fi

echo "Detected internet interface: $INTERNET_IFACE"

# Create simple status check script
cat > "$APP_DIR/check_status.sh" << 'EOF'
#!/bin/bash
echo "=== Simple WiFi Captive Portal Status ==="
echo

echo "Service status:"
systemctl status wifi-captive-portal --no-pager --lines=5

echo
echo "Hotspot connection:"
nmcli connection show | grep Hotspot || echo "No hotspot connection found"

echo
echo "WiFi interface status:"
nmcli device status | grep wifi

echo
echo "Network interfaces:"
ip addr show | grep -E "(wlan0|eth0)" -A 2

echo
echo "To access portal:"
echo "1. Connect to 'Setup-Robot-WiFi' network"
echo "2. Open browser to: http://10.42.0.1:5000"
EOF
chmod +x "$APP_DIR/check_status.sh"

# Create simple start/stop scripts
cat > "$APP_DIR/stop_portal.sh" << 'EOF'
#!/bin/bash
echo "Stopping WiFi Captive Portal..."
sudo systemctl stop wifi-captive-portal
echo "Portal stopped."
EOF
chmod +x "$APP_DIR/stop_portal.sh"

# Reload systemd
systemctl daemon-reload

# Restart NetworkManager to apply configuration
echo "Restarting NetworkManager..."
systemctl restart NetworkManager
sleep 2

echo "================================="
echo "Setup completed successfully!"
echo "================================="
echo
echo "Simple WiFi Captive Portal is ready!"
echo
echo "To start the portal:"
echo "  sudo systemctl start wifi-captive-portal"
echo "  (or sudo $APP_DIR/start_portal.sh)"
echo
echo "To enable auto-start on boot:"
echo "  sudo systemctl enable wifi-captive-portal"
echo
echo "How it works:"
echo "1. The portal creates a WiFi hotspot named 'Setup-Robot-WiFi'"
echo "2. Users connect to this open network"  
echo "3. Users open a browser and go to: http://10.42.0.1:5000"
echo "4. Users can then select and connect to their home WiFi"
echo "5. The hotspot shuts down after successful connection"
echo
echo "Useful commands:"
echo "  Check status: sudo $APP_DIR/check_status.sh"
echo "  View logs: sudo journalctl -u wifi-captive-portal -f"
echo "  Stop portal: sudo $APP_DIR/stop_portal.sh"
echo
echo "Internet interface detected: $INTERNET_IFACE"
echo "NetworkManager configured for WiFi hotspot mode"