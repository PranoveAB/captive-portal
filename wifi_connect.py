#!/usr/bin/env python3
"""
WiFi Captive Portal Application
A tool to create a captive portal for easy WiFi setup on Linux devices.
"""

import os
import sys
import time
import json
import subprocess
import threading
from flask import Flask, render_template, request, jsonify, redirect
import socket
import random
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WiFiConnect:
    def __init__(self):
        self.app = Flask(__name__)
        self.hotspot_name = f"Setup-Robot-WiFi"
        self.hotspot_password = ""  # Open network
        self.interface = "wlan0"
        self.ap_ip = "10.42.0.1"
        self.is_hotspot_active = False
        self.connection_status = "disconnected"
        
        # Setup Flask routes
        self.setup_routes()
    
    def setup_routes(self):
        """Setup Flask web routes"""
        
        @self.app.route('/')
        def index():
            return self.render_portal_page()
        
        @self.app.route('/portal')
        def portal():
            return self.render_portal_page()
        
        @self.app.route('/scan')
        def scan_networks():
            """API endpoint to scan for available networks"""
            try:
                networks = self.scan_wifi_networks()
                return jsonify({"success": True, "networks": networks})
            except Exception as e:
                logger.error(f"Failed to scan networks: {e}")
                return jsonify({"success": False, "error": str(e)})
        
        @self.app.route('/connect', methods=['POST'])
        def connect_wifi():
            """API endpoint to connect to a WiFi network"""
            try:
                data = request.get_json()
                ssid = data.get('ssid')
                password = data.get('password', '')
                
                if not ssid:
                    return jsonify({"success": False, "error": "SSID is required"})
                
                logger.info(f"Attempting to connect to network: {ssid}")
                
                # Attempt to connect
                success = self.connect_to_network(ssid, password)
                
                if success:
                    logger.info(f"Successfully connected to {ssid}")
                    # Start shutdown sequence in background after a brief delay
                    threading.Thread(target=self.shutdown_hotspot_delayed, daemon=True).start()
                    return jsonify({
                        "success": True, 
                        "message": f"Successfully connected to {ssid}! Portal will shut down in a few seconds.",
                        "connected": True,
                        "ssid": ssid
                    })
                else:
                    logger.warning(f"Failed to connect to {ssid}")
                    return jsonify({
                        "success": False, 
                        "error": "Failed to connect to network. Please check your credentials and try again."
                    })
                    
            except Exception as e:
                logger.error(f"Connection error: {e}")
                return jsonify({"success": False, "error": str(e)})
        
        @self.app.route('/status')
        def get_status():
            """Get current connection status"""
            return jsonify({
                "hotspot_active": self.is_hotspot_active,
                "connection_status": self.connection_status,
                "hotspot_name": self.hotspot_name
            })
    
    def render_portal_page(self):
        """Render the captive portal page"""
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WiFi Setup Portal</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            max-width: 500px;
            width: 100%;
            padding: 40px;
            text-align: center;
        }
        
        .logo {
            width: 80px;
            height: 80px;
            margin: 0 auto 20px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            color: white;
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        
        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }
        
        .network-list {
            margin: 20px 0;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .network-item {
            display: flex;
            align-items: center;
            padding: 15px;
            border: 2px solid #f0f0f0;
            border-radius: 12px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .network-item:hover {
            border-color: #667eea;
            background: #f8f9ff;
        }
        
        .network-item.selected {
            border-color: #667eea;
            background: #f0f4ff;
        }
        
        .network-info {
            flex-grow: 1;
            text-align: left;
        }
        
        .network-name {
            font-weight: bold;
            color: #333;
        }
        
        .network-security {
            font-size: 12px;
            color: #666;
        }
        
        .signal-strength {
            width: 20px;
            height: 20px;
            margin-left: 10px;
        }
        
        .form-group {
            margin: 20px 0;
            text-align: left;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #333;
        }
        
        input[type="password"], input[type="text"] {
            width: 100%;
            padding: 15px;
            border: 2px solid #e1e5e9;
            border-radius: 12px;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }
        
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            width: 100%;
            margin-top: 20px;
            transition: transform 0.3s ease;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .status-message {
            padding: 15px;
            border-radius: 12px;
            margin: 20px 0;
            font-weight: 500;
        }
        
        .status-success {
            background: #d4edda;
            color: #155724;
            border: 2px solid #c3e6cb;
        }
        
        .status-error {
            background: #f8d7da;
            color: #721c24;
            border: 2px solid #f5c6cb;
        }
        
        .loading {
            display: none;
            margin: 20px 0;
        }
        
        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .instructions {
            background: #f8f9fa;
            border: 2px solid #e9ecef;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .instructions h3 {
            color: #495057;
            margin-bottom: 10px;
        }
        
        .instructions p {
            color: #6c757d;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">📶</div>
        <h1>WiFi Setup</h1>
        <p class="subtitle">Connect your device to a WiFi network</p>
        
        <div class="instructions">
            <h3>How to Access</h3>
            <p>Open your web browser and go to: <strong>http://10.42.0.1:5000</strong></p>
            <p>Or just bookmark this page!</p>
        </div>
        
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Scanning for networks...</p>
        </div>
        
        <div id="networks" class="network-list"></div>
        
        <div id="connectionForm" style="display: none;">
            <div class="form-group">
                <label for="selectedNetwork">Selected Network:</label>
                <input type="text" id="selectedNetwork" readonly>
            </div>
            
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" placeholder="Enter WiFi password">
            </div>
            
            <button id="connectBtn" class="btn">Connect</button>
        </div>
        
        <div id="statusMessage" class="status-message" style="display: none;"></div>
    </div>

    <script>
        let selectedNetwork = null;
        
        // Load available networks on page load
        window.addEventListener('load', function() {
            scanNetworks();
        });
        
        function showLoading() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('networks').style.display = 'none';
        }
        
        function hideLoading() {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('networks').style.display = 'block';
        }
        
        function scanNetworks() {
            showLoading();
            
            fetch('/scan')
                .then(response => response.json())
                .then(data => {
                    hideLoading();
                    if (data.success) {
                        displayNetworks(data.networks);
                    } else {
                        showStatus('Failed to scan networks: ' + data.error, 'error');
                    }
                })
                .catch(error => {
                    hideLoading();
                    showStatus('Error scanning networks: ' + error, 'error');
                });
        }
        
        function displayNetworks(networks) {
            const container = document.getElementById('networks');
            container.innerHTML = '';
            
            if (networks.length === 0) {
                container.innerHTML = '<p>No networks found. <a href="#" onclick="scanNetworks()">Scan again</a></p>';
                return;
            }
            
            networks.forEach(network => {
                const item = document.createElement('div');
                item.className = 'network-item';
                item.onclick = () => selectNetwork(network, item);
                
                const strength = getSignalStrengthIcon(network.signal);
                const security = network.security || 'Open';
                
                item.innerHTML = `
                    <div class="network-info">
                        <div class="network-name">${network.ssid}</div>
                        <div class="network-security">${security}</div>
                    </div>
                    <div class="signal-strength">${strength}</div>
                `;
                
                container.appendChild(item);
            });
        }
        
        function getSignalStrengthIcon(signal) {
            if (signal > -50) return '📶';
            if (signal > -60) return '📶';
            if (signal > -70) return '📵';
            return '📵';
        }
        
        function selectNetwork(network, element) {
            // Remove previous selection
            document.querySelectorAll('.network-item').forEach(item => {
                item.classList.remove('selected');
            });
            
            // Select current network
            element.classList.add('selected');
            selectedNetwork = network;
            
            // Show connection form
            document.getElementById('selectedNetwork').value = network.ssid;
            document.getElementById('connectionForm').style.display = 'block';
            
            // Focus password field if network is secured
            if (network.security && network.security !== 'Open') {
                document.getElementById('password').focus();
            }
        }
        
        function showStatus(message, type) {
            const statusDiv = document.getElementById('statusMessage');
            statusDiv.textContent = message;
            statusDiv.className = `status-message status-${type}`;
            statusDiv.style.display = 'block';
        }
        
        // Connect button handler
        document.getElementById('connectBtn').addEventListener('click', function() {
            if (!selectedNetwork) {
                showStatus('Please select a network first', 'error');
                return;
            }
            
            const password = document.getElementById('password').value;
            const connectBtn = document.getElementById('connectBtn');
            
            // Disable button and show loading
            connectBtn.disabled = true;
            connectBtn.textContent = 'Connecting...';
            
            fetch('/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ssid: selectedNetwork.ssid,
                    password: password
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.connected) {
                    showStatus(data.message, 'success');
                    
                    // Show success page immediately
                    setTimeout(() => {
                        document.getElementById('connectionForm').style.display = 'none';
                        document.querySelector('.container').innerHTML = `
                            <div class="logo">✅</div>
                            <h1>Connected!</h1>
                            <p class="subtitle">Successfully connected to ${data.ssid}</p>
                            <p style="margin: 20px 0; color: #28a745; font-weight: bold;">You now have internet access!</p>
                            <div style="background: #f8f9fa; padding: 20px; border-radius: 12px; margin: 20px 0;">
                                <p style="color: #6c757d; font-size: 14px; margin-bottom: 15px;">
                                    The WiFi setup portal will shut down automatically, but you can close it now if you'd like.
                                </p>
                                <button onclick="shutdownPortal()" style="
                                    background: #dc3545; color: white; border: none; padding: 10px 20px; 
                                    border-radius: 8px; cursor: pointer; font-size: 14px;
                                ">Shut Down Portal Now</button>
                            </div>
                        `;
                    }, 1000);
                } else {
                    showStatus(data.error || 'Connection failed', 'error');
                }
            })
            .catch(error => {
                showStatus('Connection failed: ' + error, 'error');
            })
            .finally(() => {
                connectBtn.disabled = false;
                connectBtn.textContent = 'Connect';
            });
        });
        
        // Function to manually shut down portal
        function shutdownPortal() {
            fetch('/shutdown', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.querySelector('.container').innerHTML = `
                        <div class="logo">👋</div>
                        <h1>Goodbye!</h1>
                        <p class="subtitle">Portal is shutting down...</p>
                        <p style="color: #6c757d; margin-top: 20px;">You can close this page now.</p>
                    `;
                }
            })
            .catch(error => {
                console.log('Portal is shutting down');
                document.querySelector('.container').innerHTML = `
                    <div class="logo">👋</div>
                    <h1>Goodbye!</h1>
                    <p class="subtitle">Portal is shutting down...</p>
                    <p style="color: #6c757d; margin-top: 20px;">You can close this page now.</p>
                `;
            });
        }
    </script>
</body>
</html>
        """
        return html_content
    
    def scan_wifi_networks(self):
        """Scan for available WiFi networks using nmcli"""
        try:
            # Use NetworkManager to scan for networks
            result = subprocess.run([
                'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY', 'device', 'wifi', 'list'
            ], capture_output=True, text=True, check=True)
            
            networks = []
            seen_ssids = set()
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                parts = line.split(':')
                if len(parts) >= 3:
                    ssid = parts[0].strip()
                    signal = int(parts[1]) if parts[1].isdigit() else -100
                    security = parts[2].strip() if parts[2] else 'Open'
                    
                    # Skip empty SSIDs and duplicates
                    if ssid and ssid not in seen_ssids:
                        networks.append({
                            'ssid': ssid,
                            'signal': signal,
                            'security': security
                        })
                        seen_ssids.add(ssid)
            
            # Sort by signal strength (strongest first)
            networks.sort(key=lambda x: x['signal'], reverse=True)
            return networks
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to scan networks: {e}")
            return []
    
    def connect_to_network(self, ssid, password):
        """Connect to a WiFi network using NetworkManager"""
        try:
            # First, try to delete any existing connection with the same SSID to avoid conflicts
            logger.info(f"Cleaning up any existing connection for {ssid}")
            subprocess.run([
                'nmcli', 'connection', 'delete', f'id', ssid
            ], capture_output=True, text=True)
            
            # Small delay to ensure cleanup is complete
            time.sleep(1)
            
            if password:
                # WPA/WPA2 network - create new connection
                logger.info(f"Creating new connection for {ssid} with password")
                cmd = [
                    'nmcli', 'device', 'wifi', 'connect', ssid,
                    'password', password
                ]
            else:
                # Open network
                logger.info(f"Creating new connection for {ssid} (open network)")
                cmd = [
                    'nmcli', 'device', 'wifi', 'connect', ssid
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Successfully connected to {ssid}")
                self.connection_status = "connected"
                
                # Verify connection by checking if we can get an IP
                time.sleep(2)
                ip_check = subprocess.run([
                    'nmcli', 'device', 'show', self.interface
                ], capture_output=True, text=True)
                
                if "IP4.ADDRESS" in ip_check.stdout:
                    logger.info(f"Connection to {ssid} verified with IP address")
                    return True
                else:
                    logger.warning(f"Connected to {ssid} but no IP address assigned yet")
                    return True  # Still return True as connection command succeeded
            else:
                logger.error(f"Failed to connect to {ssid}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Connection to {ssid} timed out after 30 seconds")
            return False
        except Exception as e:
            logger.error(f"Exception during connection: {e}")
            return False
    
    def create_hotspot(self):
        """Create WiFi hotspot using NetworkManager"""
        try:
            logger.info(f"Creating hotspot: {self.hotspot_name}")
            
            # Delete existing hotspot connection if it exists
            subprocess.run([
                'nmcli', 'connection', 'delete', 'Hotspot'
            ], capture_output=True)
            
            # Create new hotspot connection
            cmd = [
                'nmcli', 'connection', 'add',
                'type', 'wifi',
                'ifname', self.interface,
                'con-name', 'Hotspot',
                'autoconnect', 'yes',
                'ssid', self.hotspot_name
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Failed to create hotspot connection: {result.stderr}")
            
            # Configure as access point
            subprocess.run([
                'nmcli', 'connection', 'modify', 'Hotspot',
                '802-11-wireless.mode', 'ap',
                '802-11-wireless.band', 'bg',
                'ipv4.method', 'shared'
            ], check=True)
        
            # Open network - no security
            logger.info("Creating open network (no password required)")
            
            # Activate the hotspot
            result = subprocess.run([
                'nmcli', 'connection', 'up', 'Hotspot'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.is_hotspot_active = True
                logger.info(f"Hotspot '{self.hotspot_name}' created successfully")
                return True
            else:
                raise Exception(f"Failed to activate hotspot: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Failed to create hotspot: {e}")
            return False
    
    def shutdown_hotspot(self):
        """Shutdown the WiFi hotspot"""
        try:
            logger.info("Shutting down hotspot")
            subprocess.run([
                'nmcli', 'connection', 'down', 'Hotspot'
            ], capture_output=True)
            
            subprocess.run([
                'nmcli', 'connection', 'delete', 'Hotspot'
            ], capture_output=True)
            
            self.is_hotspot_active = False
            logger.info("Hotspot shut down successfully")
            
        except Exception as e:
            logger.error(f"Failed to shutdown hotspot: {e}")
    
    def shutdown_hotspot_delayed(self):
        """Shutdown hotspot after a delay"""
        time.sleep(5)  # Reduced from 10 seconds
        self.shutdown_hotspot()
        logger.info("Exiting application")
        os._exit(0)
    
    def run(self):
        """Main application entry point"""
        try:
            logger.info("Starting WiFi Connect Portal")
            
            # Create hotspot
            if not self.create_hotspot():
                logger.error("Failed to create hotspot. Exiting.")
                return
            
            # Start Flask application on port 5000
            logger.info(f"Starting web portal on {self.ap_ip}:5000")
            logger.info(f"Connect to WiFi network: {self.hotspot_name}")
            logger.info(f"Then open browser to: http://{self.ap_ip}:5000")
            
            self.app.run(host='0.0.0.0', port=5000, debug=False)
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Application error: {e}")
        finally:
            self.shutdown_hotspot()

if __name__ == "__main__":
    # Check if running as root
    if os.geteuid() != 0:
        print("This application requires root privileges to manage network interfaces.")
        print("Please run with sudo:")
        print(f"sudo python3 {sys.argv[0]}")
        sys.exit(1)
    
    # Create and run the application
    wifi_connect = WiFiConnect()
    wifi_connect.run()