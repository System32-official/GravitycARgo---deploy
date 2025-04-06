"""
Configuration settings for the container packing application
"""
import os

# Base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Upload settings
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max-limit
ALLOWED_EXTENSIONS = {'csv'}

# MIME types
MIME_TYPES = {
    'json': 'application/json',
    'csv': 'text/csv',
    'html': 'text/html'
}

# Secret key - using a secure random string
SECRET_KEY = "f23fc24a32e7986b99c8cdaee97f5f395caf23930a3cbf82"  # Random secure key