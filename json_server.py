import http.server
import socketserver
import os
import subprocess
import threading
import time
import signal
import sys
import json
import glob
import shutil

# Configuration
PORT = 8000
DIRECTORY = "container_plans"  # The directory containing your JSON files
NGROK_DOMAIN = "destined-mammoth-flowing.ngrok-free.app"  # Fixed domain
STANDARD_JSON_FILENAME = "latest_container_plan.json"  # Standardized name for the JSON file

# Get absolute paths
print("Starting JSON server initialization...")
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, DIRECTORY)
staging_dir = os.path.join(script_dir, "serving")
json_path = os.path.join(staging_dir, STANDARD_JSON_FILENAME)

# Create staging directory if it doesn't exist
if not os.path.exists(staging_dir):
    os.makedirs(staging_dir)
    print(f"Created staging directory: {staging_dir}")

# Find the latest JSON file in the container_plans folder
def get_latest_json_file():
    print("Looking for JSON files...")
    json_files = glob.glob(os.path.join(data_dir, "*.json"))
    if not json_files:
        print(f"ERROR: No JSON files found in {data_dir}")
        sys.exit(1)
    
    # Sort files by modification time, newest first
    latest_json = max(json_files, key=os.path.getmtime)
    print(f"Found latest JSON file: {os.path.basename(latest_json)}")
    return latest_json

# Get the latest JSON file and copy it to the staging directory with the standard name
try:
    latest_json_file = get_latest_json_file()
    shutil.copy2(latest_json_file, json_path)
    print(f"Copied to staging as: {STANDARD_JSON_FILENAME}")
except Exception as e:
    print(f"ERROR copying file: {e}")
    sys.exit(1)

# Create a simple handler that serves the specific JSON file for any request
class SingleJSONHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress default logging
        return
        
    def end_headers(self):
        # Enable CORS for Unity
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Content-Type', 'application/json')
        return super().end_headers()
        
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        print(f"Received request: {self.path}")
        
        # For any path, serve the JSON file
        self.send_response(200)
        self.end_headers()
        
        # Read and serve the JSON file
        with open(json_path, 'rb') as file:
            self.wfile.write(file.read())

# Global variable to hold reference to the ngrok process
ngrok_process = None
ngrok_url = f"https://{NGROK_DOMAIN}/{STANDARD_JSON_FILENAME}"

def check_ngrok_installed():
    try:
        # Try to run ngrok version command
        result = subprocess.run(["ngrok", "version"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE,
                               text=True)
        if result.returncode == 0:
            print(f"ngrok is installed: {result.stdout.strip()}")
            return True
        else:
            print("ngrok command failed")
            return False
    except Exception as e:
        print(f"Error checking ngrok: {e}")
        return False

def start_ngrok():
    """Start ngrok process to expose the local server"""
    global ngrok_process
    
    try:
        print("Checking ngrok installation...")
        if not check_ngrok_installed():
            print("ERROR: ngrok is not installed or not in PATH")
            print("Please install ngrok and add it to your PATH")
            print("Continuing with local server only")
            return False
        
        # Build the command for running ngrok with the specified domain
        cmd = f"ngrok http {PORT} --domain={NGROK_DOMAIN}"
        
        # Start ngrok process
        print(f"Starting ngrok with command: {cmd}")
        ngrok_process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        
        # Wait for ngrok to start up
        print("Waiting for ngrok to start...")
        time.sleep(5)
        
        # Check if process started successfully
        if ngrok_process.poll() is not None:
            print("ERROR: ngrok failed to start")
            stderr = ngrok_process.stderr.read().decode('utf-8')
            print(f"Error output: {stderr}")
            return False
        
        print(f"ngrok started successfully!")
        print(f"Access your container data at: {ngrok_url}")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to start ngrok: {e}")
        return False

def stop_ngrok():
    """Stop the ngrok process"""
    global ngrok_process
    if ngrok_process:
        print("Stopping ngrok...")
        ngrok_process.terminate()
        try:
            ngrok_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            ngrok_process.kill()
        print("ngrok stopped")

def handle_shutdown(signum, frame):
    """Handler for signals to ensure clean shutdown"""
    print("\nShutdown requested...")
    stop_ngrok()
    print("Stopping HTTP server...")
    sys.exit(0)

# Register signal handlers for clean shutdown
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

# Read the JSON file to display info
try:
    print("Reading JSON file contents...")
    with open(json_path, 'r') as f:
        data = json.load(f)
        # Extract info based on your JSON structure
        container_type = data.get('container_info', {}).get('type', 'Unknown')
        timestamp = data.get('timestamp', 'Unknown')
        packed_items_count = len(data.get('packed_items', []))
        print(f"\nContainer: {container_type}")
        print(f"Timestamp: {timestamp}")
        print(f"Packed items: {packed_items_count}")
except Exception as e:
    print(f"Warning: Could not parse JSON file: {e}")

# Only run server if this file is executed directly
if __name__ == "__main__":
    # Start the HTTP server
    print(f"\nStarting local server at http://localhost:{PORT}")
    try:
        httpd = socketserver.TCPServer(("", PORT), SingleJSONHandler)
        print("HTTP server initialized successfully")
    except Exception as e:
        print(f"ERROR starting HTTP server: {e}")
        sys.exit(1)

    # Start serving in a separate thread
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    print("HTTP server thread started")

    # Start ngrok in the main thread
    print("\nStarting ngrok to expose your server...")
    ngrok_success = start_ngrok()

    # Log final status
    print("\nServer is now running!")
    print(f"Serving file: {STANDARD_JSON_FILENAME}")
    print(f"URL for Unity: {ngrok_url}")
    print("Server will run until you press Ctrl+C\n")

    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutdown initiated by user...")
    finally:
        # Clean up
        stop_ngrok()
        httpd.shutdown()
        httpd.server_close()
        print("Server stopped")
