"""
Entry point for Gunicorn and other WSGI servers.
This file redirects to our actual application in app_modular.py
"""
import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Try to import required packages, install them if missing
required_packages = ['psutil']
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        logger.warning(f"Package {package} not found. Attempting to install...")
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            logger.info(f"Successfully installed {package}")
        except Exception as e:
            logger.error(f"Failed to install {package}: {e}")
            if package == 'psutil':
                logger.warning("psutil is required but couldn't be installed. Some system monitoring features may not work.")

# Set up groq module fallback
try:
    # First try to import the actual module
    import groq
    logger.info("Groq module imported successfully")
except ImportError:
    logger.warning("Groq module not available. Using direct API calls instead.")
    # If it's not available, create a path to the fallback module
    fallback_path = os.path.join(os.path.dirname(__file__), "optigenix_module", "utils")
    if fallback_path not in sys.path:
        sys.path.append(fallback_path)
    # No need to import groq_fallback here, it will be imported as needed

# Global variable to store the initialization error if one occurs
INIT_ERROR = None

try:
    # Try to import polyline here to catch it early
    try:
        import polyline
        logger.info("Polyline module imported successfully")
    except ImportError:
        logger.warning("Polyline module not found. Installing...")
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "polyline"])
            import polyline
            logger.info("Successfully installed polyline")
        except Exception as e:
            logger.error(f"Failed to install polyline: {e}")
            raise ImportError(f"Failed to install required package polyline: {e}")
    
    # Now import and create our app
    from app_modular import create_app, create_socketio
    
    app = create_app()
    socketio = create_socketio(app)
    
    if __name__ == "__main__":
        socketio.run(app)
except Exception as e:
    INIT_ERROR = str(e)
    logger.error(f"Error initializing application: {e}")
    # Create a minimal Flask app for debugging
    from flask import Flask, jsonify
    
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        return jsonify({
            "status": "error", 
            "message": f"Application failed to initialize: {INIT_ERROR}",
            "python_version": sys.version,
            "current_directory": os.getcwd(),
            "directory_contents": os.listdir('.')
        })
    
    if __name__ == "__main__":
        app.run()
