"""
Bridge file that imports the Flask application from app_modular.py via wsgi.py.
This allows Render's default 'gunicorn app:app' command to work correctly.
"""
import os
import sys

# Add error handling for missing dependencies
try:
    from wsgi import app, socketio
except ImportError as e:
    if "No module named 'plotly'" in str(e):
        print("Error: Missing plotly dependency. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "plotly"])
        from wsgi import app, socketio
    else:
        print(f"Fatal import error: {e}")
        raise

# Add health check endpoint for monitoring
@app.route('/health')
def health_check():
    return {'status': 'healthy'}, 200

# This exposes the app variable at the module level for gunicorn to find
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
