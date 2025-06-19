"""
WSGI entry point for production deployment on Render
"""
import os
import sys

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Set production environment variables before importing app
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('DEBUG', 'False')

# Import the application factory
from app_modular import create_app

# Create application instance
app = create_app()

# For gunicorn compatibility
application = app

if __name__ == "__main__":
    # For gunicorn, this won't be called, but useful for testing
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
