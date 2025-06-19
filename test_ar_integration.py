#!/usr/bin/env python3
"""
Test AR Server Start Script
This script starts the Flask application and tests the AR server endpoints
"""
import sys
import os
import subprocess
import time
import requests
from threading import Thread

def start_flask_app():
    """Start the Flask application in a subprocess"""
    try:
        print("Starting Flask application...")
        cmd = [sys.executable, "app_modular.py"]
        
        # Start Flask app in background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        
        print(f"Flask app started with PID: {process.pid}")
        return process
        
    except Exception as e:
        print(f"Error starting Flask app: {e}")
        return None

def test_ar_endpoints():
    """Test AR server endpoints"""
    print("Waiting for Flask app to start...")
    time.sleep(5)  # Give Flask time to start
    
    try:
        # Test health endpoint
        print("Testing health endpoint...")
        response = requests.get('http://localhost:5000/health', timeout=5)
        if response.status_code == 200:
            print("✓ Flask app is running")
        else:
            print(f"⚠ Health check returned {response.status_code}")
            return False
        
        # Test JSON server status
        print("Testing JSON server status...")
        response = requests.get('http://localhost:5000/check_json_server_status', timeout=5)
        if response.status_code == 200:
            print("✓ JSON server status endpoint working")
            data = response.json()
            print(f"   Server running: {data.get('running', False)}")
        else:
            print(f"⚠ JSON server status returned {response.status_code}")
        
        # Test starting JSON server
        print("Testing JSON server start...")
        response = requests.post('http://localhost:5000/start_json_server', timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✓ JSON server started successfully")
                print(f"   URL: {data.get('url')}")
                return True
            else:
                print(f"⚠ JSON server start failed: {data.get('error')}")
                return False
        else:
            print(f"⚠ JSON server start returned {response.status_code}")
            return False
            
    except requests.ConnectionError:
        print("❌ Cannot connect to Flask app - check if it's running")
        return False
    except Exception as e:
        print(f"❌ Error testing endpoints: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("AR Server Integration Test")
    print("=" * 60)
    
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Start Flask app
    flask_process = start_flask_app()
    
    if not flask_process:
        print("❌ Failed to start Flask app")
        return
    
    try:
        # Test endpoints
        success = test_ar_endpoints()
        
        if success:
            print("\n🎉 AR Server test PASSED!")
        else:
            print("\n❌ AR Server test FAILED!")
        
    finally:
        # Clean up - terminate Flask process
        print("\nCleaning up...")
        try:
            flask_process.terminate()
            flask_process.wait(timeout=5)
            print("✓ Flask app terminated")
        except:
            flask_process.kill()
            print("✓ Flask app killed")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
