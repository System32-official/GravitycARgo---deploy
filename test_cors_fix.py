#!/usr/bin/env python3
"""
Test CORS Fix for AR Visualization
This script tests that the CORS issue is resolved and the AR visualization can connect to Flask
"""
import subprocess
import time
import requests
import webbrowser
import os
import sys
from threading import Thread

def start_flask_app():
    """Start the Flask application"""
    try:
        print("Starting Flask application...")
        cmd = [sys.executable, "app_modular.py"]
        
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

def test_cors_headers():
    """Test that CORS headers are properly set"""
    print("Waiting for Flask app to start...")
    time.sleep(3)
    
    try:
        # Test preflight OPTIONS request
        print("Testing OPTIONS request (CORS preflight)...")
        response = requests.options('http://localhost:5000/start_json_server', 
                                   headers={'Origin': 'file://', 'Access-Control-Request-Method': 'POST'})
        print(f"OPTIONS response status: {response.status_code}")
        print(f"CORS headers: {dict(response.headers)}")
        
        # Test actual endpoint
        print("Testing POST request to start_json_server...")
        response = requests.post('http://localhost:5000/start_json_server',
                                headers={'Origin': 'file://'})
        print(f"POST response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ CORS appears to be working correctly!")
            return True
        else:
            print(f"⚠ Unexpected status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.ConnectionError:
        print("❌ Cannot connect to Flask app - make sure it's running")
        return False
    except Exception as e:
        print(f"❌ Error testing CORS: {e}")
        return False

def open_visualization():
    """Open the container visualization in browser"""
    html_file = os.path.join("templates", "container_visualization.html")
    if os.path.exists(html_file):
        print(f"Opening visualization: {html_file}")
        webbrowser.open(f'file://{os.path.abspath(html_file)}')
        print("Click the 'AR View' button to test the CORS fix!")
    else:
        print("❌ Visualization HTML file not found")

def main():
    """Main test function"""
    print("=" * 60)
    print("CORS Fix Test for AR Visualization")
    print("=" * 60)
    
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Start Flask app
    flask_process = start_flask_app()
    
    if not flask_process:
        print("❌ Failed to start Flask app")
        return
    
    try:
        # Test CORS
        cors_working = test_cors_headers()
        
        if cors_working:
            print("\n🎉 CORS test PASSED!")
            print("\nTo test the full AR visualization:")
            print("1. The Flask server is running")
            print("2. Opening the visualization in your browser...")
            print("3. Click the 'AR View' button to test")
            print("4. You should no longer see the CORS error!")
            
            # Open the visualization
            open_visualization()
            
            print("\nPress Enter to stop the Flask server...")
            input()
        else:
            print("\n❌ CORS test FAILED!")
        
    finally:
        # Clean up - terminate Flask process
        print("\nStopping Flask server...")
        try:
            flask_process.terminate()
            flask_process.wait(timeout=5)
            print("✓ Flask server stopped")
        except:
            flask_process.kill()
            print("✓ Flask server killed")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
