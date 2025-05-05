"""
Alternative entry point for the container packing application
This module uses the new optigenix_module structure while maintaining
the same functionality as the original app.py
"""
from flask import Flask, jsonify, request, current_app
import os
import sys
import json
import time
import logging
import subprocess
# Make psutil import optional with fallback
try:
    import psutil
except ImportError:
    logging.warning("psutil module not found. System monitoring features will be limited.")
    # Create a minimal mock for basic functionality
    class PsutilMock:
        @staticmethod
        def Process(pid):
            class MockProcess:
                @staticmethod
                def memory_info():
                    class MemInfo:
                        rss = 0
                    return MemInfo()
                @staticmethod
                def cpu_percent():
                    return 0
                @staticmethod
                def is_running():
                    return True
                @staticmethod
                def terminate():
                    pass
            return MockProcess()
    psutil = PsutilMock()
import signal
import threading
import http.server
import socketserver
import glob
import shutil
from logging.handlers import RotatingFileHandler
from flask_socketio import SocketIO, emit
import multiprocessing
from routing.Server import app as route_temp_app

# Update imports to use the new package structure

# Import configuration from config.py
from config import UPLOAD_FOLDER, PLANS_FOLDER, MAX_CONTENT_LENGTH, SECRET_KEY

# Constants
STANDARD_JSON_FILENAME = "latest_container_plan.json"  # Standard JSON filename for serving
NGROK_DOMAIN = "destined-mammoth-flowing.ngrok-free.app"  # Fixed ngrok domain
JSON_SERVER_PORT = 8000

# Import other modules
from modules.handlers import (
    landing_handler, start_handler, optimize_handler, download_report_handler,
    view_report_handler, preview_csv_handler,
    get_container_stats_handler, get_item_details_handler, get_container_status_handler,
    clear_container_handler, handle_socketio_update_request, generate_alternative_plan_handler
)
from modules.handlers import bp

# Integrated JSON Server implementation
class JSONServerService:
    """
    Manages an integrated JSON server for AR visualization.
    Runs a local HTTP server and ngrok tunnel directly within the Flask application.
    """
    _instance = None
    _server = None
    _server_thread = None
    _ngrok_process = None
    _ngrok_url = f"https://{NGROK_DOMAIN}/{STANDARD_JSON_FILENAME}"
    _is_running = False
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = JSONServerService()
        return cls._instance
    
    def __init__(self):
        """Initialize the JSONServerService"""
        # Setup static paths
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.script_dir, "container_plans")
        self.staging_dir = os.path.join(self.script_dir, "serving")
        self.json_path = os.path.join(self.staging_dir, STANDARD_JSON_FILENAME)
        
        # Prepare the staging directory
        os.makedirs(self.staging_dir, exist_ok=True)
        
        # Create handler for serving JSON
        self.handler_class = self._create_handler()
    
    def _create_handler(self):
        """Create a handler class for the HTTP server"""
        json_path = self.json_path
        
        class SingleJSONHandler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                # Redirect logs to Flask logger
                try:
                    current_app.logger.debug(f"JSONServer: {format % args}")
                except:
                    pass
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
                try:
                    current_app.logger.debug(f"JSONServer received request: {self.path}")
                except:
                    print(f"JSONServer received request: {self.path}")
                
                # For any path, serve the JSON file
                self.send_response(200)
                self.end_headers()
                
                try:
                    # Read and serve the JSON file
                    with open(json_path, 'rb') as file:
                        self.wfile.write(file.read())
                except Exception as e:
                    try:
                        current_app.logger.error(f"Error serving JSON: {e}")
                    except:
                        print(f"Error serving JSON: {e}")
        
        return SingleJSONHandler
    
    def update_json_file(self):
        """Update the JSON file with the latest container plan"""
        try:
            # Find the latest JSON file
            json_files = glob.glob(os.path.join(self.data_dir, "*.json"))
            if not json_files:
                print(f"ERROR: No JSON files found in {self.data_dir}")
                return False
                
            # Sort files by modification time, newest first
            latest_json = max(json_files, key=os.path.getmtime)
            print(f"Found latest JSON file: {os.path.basename(latest_json)}")
                
            # Copy to staging directory
            shutil.copy2(latest_json, self.json_path)
            print(f"Copied to staging as: {STANDARD_JSON_FILENAME}")
            return True
        except Exception as e:
            print(f"ERROR copying JSON file: {e}")
            return False
    
    def is_port_in_use(self, port):
        """Check if a port is already in use"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
            
    def find_available_port(self, start_port, max_attempts=10):
        """Find an available port starting from start_port"""
        port = start_port
        for _ in range(max_attempts):
            if not self.is_port_in_use(port):
                return port
            port += 1
        return None
    
    def start_server(self):
        """Start the integrated JSON server"""
        with self._lock:
            if self._is_running:
                print("JSON server is already running")
                return True
                
            try:
                # Update the JSON file first
                if not self.update_json_file():
                    return False
                
                # Check if the default port is in use
                port_to_use = JSON_SERVER_PORT
                if self.is_port_in_use(port_to_use):
                    print(f"Port {port_to_use} is already in use!")
                    
                    # Try to find an available port
                    port_to_use = self.find_available_port(port_to_use + 1)
                    if port_to_use is None:
                        raise Exception("Could not find an available port to start the JSON server")
                    print(f"Using alternative port: {port_to_use}")
                
                # Start the HTTP server
                print(f"Starting local HTTP server on port {port_to_use}...")
                self._server = socketserver.TCPServer(("", port_to_use), self.handler_class)
                
                # Run in a thread
                self._server_thread = threading.Thread(target=self._server.serve_forever)
                self._server_thread.daemon = True
                self._server_thread.start()
                print("HTTP server started successfully")
                
                # Start ngrok in another thread
                ngrok_thread = threading.Thread(target=lambda: self._start_ngrok(port_to_use))
                ngrok_thread.daemon = True
                ngrok_thread.start()
                
                # Wait for ngrok to start
                time.sleep(5)
                
                self._is_running = True
                print(f"JSON server is running. URL: {self._ngrok_url}")
                return True
                
            except Exception as e:
                print(f"Failed to start JSON server: {e}")
                self.stop_server()  # Clean up if partially started
                return False
    
    def _start_ngrok(self, port=JSON_SERVER_PORT):
        """Start ngrok tunnel"""
        try:
            # Check if ngrok is installed
            result = subprocess.run(["ngrok", "version"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   text=True)
            if result.returncode != 0:
                print("Error: ngrok is not installed or not in PATH")
                return False
                
            # Start ngrok with the specified domain
            cmd = f"ngrok http {port} --domain={NGROK_DOMAIN}"
            print(f"Starting ngrok: {cmd}")
            
            # Try to terminate any existing ngrok processes first
            self._kill_existing_ngrok()
            
            self._ngrok_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True
            )
            
            # Check if process started successfully
            if self._ngrok_process.poll() is not None:
                stderr = self._ngrok_process.stderr.read().decode('utf-8')
                print(f"Failed to start ngrok: {stderr}")
                return False
                
            print(f"ngrok started successfully with URL: {self._ngrok_url}")
            return True
            
        except Exception as e:
            print(f"Error starting ngrok: {e}")
            return False
            
    def _kill_existing_ngrok(self):
        """Attempt to kill any existing ngrok processes"""
        try:
            if os.name == 'nt':  # Windows
                # Try to kill any existing ngrok processes
                os.system("taskkill /f /im ngrok.exe 2>nul")
            else:  # Unix/Linux/Mac
                os.system("pkill ngrok 2>/dev/null")
            
            # Give it a moment to terminate
            time.sleep(1)
        except Exception as e:
            print(f"Warning: Could not kill existing ngrok processes: {e}")
            # Continue anyway
    
    def stop_server(self):
        """Stop the JSON server"""
        with self._lock:
            if not self._is_running:
                return True
                
            try:
                # Stop ngrok
                if self._ngrok_process:
                    print("Stopping ngrok...")
                    self._ngrok_process.terminate()
                    try:
                        self._ngrok_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self._ngrok_process.kill()
                    self._ngrok_process = None
                
                # Stop HTTP server
                if self._server:
                    print("Stopping HTTP server...")
                    self._server.shutdown()
                    self._server.server_close()
                    self._server = None
                    self._server_thread = None
                
                self._is_running = False
                print("JSON server stopped")
                return True
                
            except Exception as e:
                print(f"Error stopping JSON server: {e}")
                return False
    
    def is_running(self):
        """Check if the server is running"""
        with self._lock:
            if not self._is_running:
                return False
                
            # Additional check - if ngrok process died
            if self._ngrok_process and self._ngrok_process.poll() is not None:
                print("ngrok process has died unexpectedly")
                self._is_running = False
                return False
                
            return True
    
    def get_url(self):
        """Get the ngrok URL for the JSON server"""
        return self._ngrok_url

# JSON server process management for AR visualization (legacy class kept for compatibility)
class JsonServerManager:
    """Legacy class for backwards compatibility"""
    _process = None
    _server_url = None
    _lock = threading.Lock()
    
    @classmethod
    def start_server(cls):
        """Start the JSON server process"""
        service = JSONServerService.get_instance()
        result = service.start_server()
        if result:
            cls._server_url = service.get_url()
        return result
    
    @classmethod
    def stop_server(cls):
        """Stop the JSON server process"""
        service = JSONServerService.get_instance()
        result = service.stop_server()
        if result:
            cls._server_url = None
        return result
    
    @classmethod
    def is_server_running(cls):
        """Check if the JSON server process is running"""
        service = JSONServerService.get_instance()
        return service.is_running()
    
    @classmethod
    def get_server_url(cls):
        """Get the URL of the JSON server"""
        service = JSONServerService.get_instance()
        return service.get_url()

# JSON encoder for numpy types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        import numpy as np
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.float32):
            return float(obj)
        return super(NumpyEncoder, self).default(obj)

def create_app():
    """
    Create and configure the Flask application.
    This function initializes a Flask application with necessary configurations
    including upload directories, secret key, and JSON encoder. It sets up all
    route handlers, registers blueprints, configures error handlers, and
    establishes logging infrastructure.
    Configuration:
    - Sets static and template folders
    - Configures upload folder and maximum content length
    - Sets secret key and custom JSON encoder for numpy compatibility
    - Creates necessary directories for uploads and container plans
    Routes:
    - Landing page, start page, optimization endpoints
    - Report generation and download functionality
    - Alternative container plan generation
    - API endpoints for container statistics and item details
    - Container status and management endpoints
    Error Handling:
    - 413: Payload too large (file size exceeds limit)
    - 404: Resource not found
    - 500: Internal server error
    - Generic exception handler for unexpected errors
    Logging:
    - Configures rotating file-based logging when not in debug mode
    - Creates log directory if needed
    - Sets appropriate log format and level
    Returns:
        Flask: Configured Flask application instance ready to run
    """
    """Create and configure the Flask application"""
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    app.secret_key = SECRET_KEY
    app.json_encoder = NumpyEncoder

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Ensure container plans directory exists
    os.makedirs(PLANS_FOLDER, exist_ok=True)
    
    # Set up routes
    app.route('/')(landing_handler)
    app.route('/start')(start_handler)
    app.route('/optimize', methods=['POST'])(optimize_handler)
    app.route('/download_report')(download_report_handler)
    app.route('/view_report')(view_report_handler)
    app.route('/preview_csv', methods=['POST'])(preview_csv_handler)
    app.route('/api/container/stats')(get_container_stats_handler)
    app.route('/api/items/<item_name>')(get_item_details_handler)
    app.route('/status')(get_container_status_handler)
    app.route('/clear', methods=['POST'])(clear_container_handler)
    app.route('/generate_alternative_plan')(generate_alternative_plan_handler)
    
    # JSON server control routes for AR visualization
    @app.route('/start_json_server', methods=['POST'])
    def start_json_server_handler():
        """Start the integrated JSON server for AR visualization"""
        try:
            # Use our integrated JSONServerService
            service = JSONServerService.get_instance()
            result = service.start_server()
            
            if result:
                # Return the fixed ngrok URL
                return jsonify({
                    'success': True,
                    'url': service.get_url(),
                    'message': 'JSON server started successfully'
                })
            else:
                raise Exception("Failed to start JSON server")
        except Exception as e:
            app.logger.error(f"Failed to start JSON server: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/stop_json_server', methods=['POST'])
    def stop_json_server_handler():
        """Stop the JSON server for AR visualization"""
        try:
            service = JSONServerService.get_instance()
            success = service.stop_server()
            return jsonify({
                'success': success
            })
        except Exception as e:
            app.logger.error(f"Error stopping JSON server: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/check_json_server_status')
    def check_json_server_status_handler():
        """Check the status of the JSON server for AR visualization"""
        service = JSONServerService.get_instance()
        is_running = service.is_running()
        response = {
            'running': is_running
        }
        
        if is_running:
            response['url'] = service.get_url()
        
        return jsonify(response)
    
    @app.route('/check_local_server', methods=['GET'])
    def check_local_server_handler():
        """Check if the local JSON server is running directly"""
        try:
            import requests
            
            # Try to connect to the local server
            local_url = "http://localhost:8000/latest_container_plan.json"
            try:
                response = requests.get(local_url, timeout=2)
                if response.status_code == 200:
                    # Server is running
                    JsonServerManager._server_url = local_url
                    return jsonify({
                        'success': True,
                        'url': local_url,
                        'running': True
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f"Server returned status code {response.status_code}",
                        'running': False
                    })
            except requests.RequestException as e:
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'running': False
                })
        except Exception as e:
            app.logger.error(f"Error checking local server: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'running': False
            })
    
    # Register blueprint
    app.register_blueprint(bp)
    
    # Error handlers
    @app.errorhandler(413)
    def too_large(e):
        return jsonify({
            'error': 'File is too large. Maximum size is 16MB'
        }), 413

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            'error': 'Resource not found'
        }), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({
            'error': 'Internal server error occurred'
        }), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f'Unhandled exception: {str(e)}')
        return jsonify({
            'error': 'An unexpected error occurred',
            'details': str(e)
        }), 500
        
    # Set up logging
    if not app.debug:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')
            
        # Set up file handler
        file_handler = RotatingFileHandler(
            'logs/container_packing.log', 
            maxBytes=1024 * 1024,  # 1MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Container Packing Web App startup with optigenix_module')
        
    return app

def create_socketio(app):
    """Create and configure SocketIO for the application"""
    socketio = SocketIO(app, async_mode='threading')
    
    @socketio.on('request_update')
    def handle_update_request():
        update_data = handle_socketio_update_request()
        if update_data:
            emit('container_update', update_data)
    
    @socketio.on('connect')
    def handle_connect():
        app.logger.info('Client connected to Socket.IO')
        emit('connection_status', {'status': 'connected'})
    
    @socketio.on('error')
    def handle_error(error):
        app.logger.error(f'Socket.IO error: {error}')
        emit('error', {'message': 'An error occurred with the realtime connection'})
            
    return socketio

def start_route_temp_server():
    """Start the route temperature calculation server"""
    route_temp_app.run(host='0.0.0.0', port=5001, debug=False)

if __name__ == '__main__':
    app = create_app()
    socketio = create_socketio(app)
    
    try:
        # Start route temperature server in a separate process
        route_temp_process = multiprocessing.Process(target=start_route_temp_server)
        route_temp_process.daemon = True  # This ensures the process is terminated when the main process ends
        route_temp_process.start()
        print("Route temperature server started at http://localhost:5001")
        
        # Run main application
        print("Starting application at http://localhost:5000 using optigenix_module")
        print("Enhanced with LLM-powered dynamic fitness function and adaptive mutation")
        socketio.run(app, debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"Failed to start application: {e}")
        raise