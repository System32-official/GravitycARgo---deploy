import logging

# Configure logging for WSGI
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

try:
    logger.info("Initializing application from app_modular...")
    from app_modular import create_app, create_socketio
    
    app = create_app()
    socketio = create_socketio(app)
    logger.info("Application initialized successfully")
except Exception as e:
    logger.error(f"Error initializing application from app_modular: {e}")
    # Import from app.py as fallback, which should have its own error handling
    logger.info("Attempting to initialize from app.py fallback...")
    from app import app, socketio

if __name__ == "__main__":
    socketio.run(app)
