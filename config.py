"""
Configuration settings for the container packing application
"""
import os

# Configuration values with normalized paths for Windows compatibility
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.normpath(os.path.join(BASE_DIR, 'uploads'))
PLANS_FOLDER = os.path.normpath(os.path.join(BASE_DIR, 'container_plans'))
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max-limit
SECRET_KEY = "f23fc24a32e7986b99c8cdaee97f5f395caf23930a3cbf82"
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}