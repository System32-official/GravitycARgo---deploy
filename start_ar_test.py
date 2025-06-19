#!/usr/bin/env python3
"""
Quick AR Test Starter
This script helps you start the Flask server and test the AR visualization
"""
import os
import sys
import time
import subprocess
import requests
import webbrowser

def check_flask_running():
    """Check if Flask server is already running"""
    try:
        response = requests.get('http://localhost:5000/health', timeout=2)
        return response.status_code == 200
    except:
        return False

def start_flask_server():
    """Start the Flask server in a new process"""
    print("Starting Flask server...")
    try:
        # Start Flask in background
        process = subprocess.Popen([
            sys.executable, 'app_modular.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print(f"Flask server started with PID: {process.pid}")
        
        # Wait for server to start
        print("Waiting for Flask server to start...")
        for i in range(10):
            if check_flask_running():
                print("✅ Flask server is running!")
                return process
            time.sleep(1)
            print(f"  Waiting... {i+1}/10")
        
        print("⚠️ Flask server may not have started properly")
        return process
        
    except Exception as e:
        print(f"❌ Error starting Flask server: {e}")
        return None

def open_visualization():
    """Open the visualization"""
    print("Starting visualization...")
    try:
        subprocess.run([sys.executable, 'standalone_visualization.py'])
    except Exception as e:
        print(f"❌ Error starting visualization: {e}")

def main():
    """Main function"""
    print("=" * 60)
    print("🚀 AR Visualization Test Starter")
    print("=" * 60)
    
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Check if Flask is already running
    if check_flask_running():
        print("✅ Flask server is already running!")
    else:
        # Start Flask server
        flask_process = start_flask_server()
        if not flask_process:
            print("❌ Failed to start Flask server")
            return
    
    print("\n📋 Next Steps:")
    print("1. Flask server is running at: http://localhost:5000")
    print("2. Opening the 3D visualization...")
    print("3. Click the 'AR View' button to test AR functionality")
    print("4. The AR server URL will be displayed for Unity integration")
    
    print("\n🔧 If you see connection errors:")
    print("   - Make sure Flask server is running (check terminal output)")
    print("   - Try refreshing the visualization page")
    print("   - Check that port 5000 is not blocked by firewall")
    
    # Open visualization
    time.sleep(2)
    open_visualization()

if __name__ == "__main__":
    main()
