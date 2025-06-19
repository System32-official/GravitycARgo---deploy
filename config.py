"""
Configuration settings for the container packing application
"""
import os

# Configuration values with normalized paths for cross-platform compatibility
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.normpath(os.path.join(BASE_DIR, 'uploads'))
PLANS_FOLDER = os.path.normpath(os.path.join(BASE_DIR, 'container_plans'))
MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB max-limit

# Use environment variable for secret key in production
SECRET_KEY = os.environ.get('SECRET_KEY', "f23fc24a32e7986b99c8cdaee97f5f395caf23930a3cbf82")

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PLANS_FOLDER, exist_ok=True)