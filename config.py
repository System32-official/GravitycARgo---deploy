"""
Configuration settings for the container packing application
"""
import os

# Configuration values
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
PLANS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'container_plans')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max-limit
SECRET_KEY = "f23fc24a32e7986b99c8cdaee97f5f395caf23930a3cbf82"
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}