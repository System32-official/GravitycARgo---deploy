"""
Alternative entry point for the container packing application
This module uses the new optigenix_module structure while maintaining
the same functionality as the original app.py
"""
from flask import Flask, jsonify
import os
import json
import logging
from logging.handlers import RotatingFileHandler
from flask_socketio import SocketIO, emit

# Update imports to use the new package structure
from optigenix_module.constants import CONTAINER_TYPES, TRANSPORT_MODES
from optigenix_module.models import Item, EnhancedContainer, MaximalSpace

# Import configuration from config.py
from config import UPLOAD_FOLDER, PLANS_FOLDER, MAX_CONTENT_LENGTH, SECRET_KEY, ALLOWED_EXTENSIONS

# Import other modules
from modules.models import ContainerStorage
from modules.handlers import (
    landing_handler, start_handler, optimize_handler, download_report_handler,
    generate_alternative_handler, view_report_handler, preview_csv_handler,
    get_container_stats_handler, get_item_details_handler, get_container_status_handler,
    clear_container_handler, handle_socketio_update_request, generate_alternative_plan_handler
)
from modules.handlers import bp

# JSON encoder for numpy types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        import numpy as np
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.float32):
            return float(obj)
        if isinstance(obj, np.int64):
            return int(obj)
        return super(NumpyEncoder, self).default(obj)

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    
    # Use environment variable for SECRET_KEY if available (for production)
    app.secret_key = os.environ.get('SECRET_KEY', SECRET_KEY)
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
    app.route('/alternative')(generate_alternative_handler)
    app.route('/view_report')(view_report_handler)
    app.route('/preview_csv', methods=['POST'])(preview_csv_handler)
    app.route('/api/container/stats')(get_container_stats_handler)
    app.route('/api/items/<item_name>')(get_item_details_handler)
    app.route('/status')(get_container_status_handler)
    app.route('/clear', methods=['POST'])(clear_container_handler)
    app.route('/generate_alternative_plan')(generate_alternative_plan_handler)
    
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
    # For production, configure cors_allowed_origins properly
    socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")
    
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

if __name__ == '__main__':
    app = create_app()
    socketio = create_socketio(app)
    
    try:
        # Get port from environment variable (for Render deployment)
        port = int(os.environ.get("PORT", 5000))
        host = '0.0.0.0'
        debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
        
        print(f"Starting application at http://localhost:{port} using optigenix_module")
        print("Enhanced with LLM-powered dynamic fitness function and adaptive mutation")
        socketio.run(app, debug=debug, host=host, port=port)
    except Exception as e:
        print(f"Failed to start application: {e}")
        raise