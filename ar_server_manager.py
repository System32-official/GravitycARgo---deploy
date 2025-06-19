"""
AR Server Manager for GravitycARgo
Manages the JSON server for AR visualization with Unity integration
"""

import os
import sys
import json
import time
import subprocess
import threading
import requests
from pathlib import Path

class ARServerManager:
    """
    Manages AR server functionality for Unity integration
    """
    
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.script_dir, "container_plans")
        self.server_url = None
        self.is_running = False
        
    def get_latest_container_plan(self):
        """Get the latest container plan JSON file"""
        try:
            json_files = list(Path(self.data_dir).glob("*.json"))
            if not json_files:
                return None
                
            # Sort by modification time, newest first
            latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading container plan: {e}")
            return None
    
    def start_ar_server(self):
        """Start the AR server for Unity visualization"""
        try:
            # Make request to Flask app to start JSON server
            response = requests.post('http://localhost:5000/start_json_server', timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.server_url = data.get('url')
                    self.is_running = True
                    print(f"AR server started successfully: {self.server_url}")
                    return True
                else:
                    print(f"Failed to start AR server: {data.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"HTTP error starting AR server: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            print(f"Connection error starting AR server: {e}")
            return False
        except Exception as e:
            print(f"Error starting AR server: {e}")
            return False
    
    def stop_ar_server(self):
        """Stop the AR server"""
        try:
            response = requests.post('http://localhost:5000/stop_json_server', timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.is_running = False
                    self.server_url = None
                    print("AR server stopped successfully")
                    return True
                else:
                    print("Failed to stop AR server")
                    return False
            else:
                print(f"HTTP error stopping AR server: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            print(f"Connection error stopping AR server: {e}")
            return False
        except Exception as e:
            print(f"Error stopping AR server: {e}")
            return False
    
    def check_server_status(self):
        """Check if the AR server is running"""
        try:
            response = requests.get('http://localhost:5000/check_json_server_status', timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                self.is_running = data.get('running', False)
                if self.is_running:
                    self.server_url = data.get('url')
                return self.is_running
            else:
                self.is_running = False
                return False
                
        except requests.RequestException:
            self.is_running = False
            return False
    
    def get_server_url(self):
        """Get the current server URL"""
        if self.check_server_status():
            return self.server_url
        return None
    
    def restart_server(self):
        """Restart the AR server"""
        print("Restarting AR server...")
        self.stop_ar_server()
        time.sleep(2)
        return self.start_ar_server()

# Global instance
ar_server = ARServerManager()

def main():
    """Command line interface for AR server management"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AR Server Manager for GravitycARgo')
    parser.add_argument('action', choices=['start', 'stop', 'status', 'restart', 'url'], 
                       help='Action to perform')
    
    args = parser.parse_args()
    
    if args.action == 'start':
        if ar_server.start_ar_server():
            print(f"AR server is running at: {ar_server.server_url}")
        else:
            print("Failed to start AR server")
            sys.exit(1)
            
    elif args.action == 'stop':
        if ar_server.stop_ar_server():
            print("AR server stopped")
        else:
            print("Failed to stop AR server")
            sys.exit(1)
            
    elif args.action == 'status':
        if ar_server.check_server_status():
            print(f"AR server is running at: {ar_server.server_url}")
        else:
            print("AR server is not running")
            
    elif args.action == 'restart':
        if ar_server.restart_server():
            print(f"AR server restarted at: {ar_server.server_url}")
        else:
            print("Failed to restart AR server")
            sys.exit(1)
            
    elif args.action == 'url':
        url = ar_server.get_server_url()
        if url:
            print(url)
        else:
            print("AR server is not running")
            sys.exit(1)

if __name__ == '__main__':
    main()
