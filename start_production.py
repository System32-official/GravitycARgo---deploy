#!/usr/bin/env python3
"""
Production startup script for GravitycARgo deployment
"""
import os
import sys
import logging

# Set environment for production
os.environ['FLASK_ENV'] = 'production'
os.environ['DEBUG'] = 'False'
os.environ['PYTHONUNBUFFERED'] = '1'

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Import and create the app
try:
    from app_modular import create_app
    app = create_app()
    
    # Log startup information
    port = int(os.environ.get('PORT', 5000))
    logging.info(f"Starting GravitycARgo application on port {port}")
    logging.info(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    
    # For production, this will be handled by gunicorn
    if __name__ == "__main__":
        app.run(host='0.0.0.0', port=port, debug=False)
        
except Exception as e:
    logging.error(f"Failed to start application: {e}")
    sys.exit(1)
