"""
Utility functions for the container packing application
"""
import os
import time
from flask import current_app

# Define allowed extensions directly here to avoid import issues
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

def allowed_file(filename):
    """Check if uploaded file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_old_files():
    """Remove uploaded files older than 24 hours"""
    now = time.time()
    try:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder, exist_ok=True)
            return
            
        for filename in os.listdir(upload_folder):
            filepath = os.path.join(upload_folder, filename)
            try:
                if os.path.getmtime(filepath) < now - 86400:  # 24 hours
                    os.remove(filepath)
            except OSError:
                pass
    except Exception as e:
        print(f"Error cleaning up old files: {str(e)}")

def calculate_overlap_area(rect1, rect2):
    """Calculate overlap area between two rectangles"""
    x1, y1, w1, d1 = rect1
    x2, y2, w2, d2 = rect2
    
    x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
    y_overlap = max(0, min(y1 + d1, y2 + d2) - max(y1, y2))
    
    return x_overlap * y_overlap