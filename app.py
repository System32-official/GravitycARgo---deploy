"""
Bridge file that imports the Flask application from app_modular.py via wsgi.py.
This allows Render's default 'gunicorn app:app' command to work correctly.
"""
from wsgi import app, socketio

# This exposes the app variable at the module level for gunicorn to find

if __name__ == '__main__':
    socketio.run(app)
