"""
WSGI entry point for production deployment on Render
"""
import os
from app_modular import create_app

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')

# Create application instance
app = create_app()

if __name__ == "__main__":
    # For gunicorn, this won't be called, but useful for testing
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
