"""
Data models for the container packing application
"""

class ContainerStorage:
    """Global container storage for the application"""
    def __init__(self):
        self.current_container = None
        self.current_report = None