"""Space model for container packing"""

class MaximalSpace:
    def __init__(self, x, y, z, width, height, depth):
        self.x = x
        self.y = y
        self.z = z
        self.width = width
        self.height = height 
        self.depth = depth
        self.temperature_safe = None  # Flag indicating if space is safe for temperature-sensitive items
        
    def get_volume(self):
        """Get the volume of this space"""
        return self.width * self.height * self.depth
        
    def can_fit_item(self, item_dims):
        """Check if this space can fit an item with the given dimensions"""
        return (self.width >= item_dims[0] and 
                self.height >= item_dims[1] and 
                self.depth >= item_dims[2])
                
    def is_near_wall(self, container_dims, buffer=0.1):
        """Check if this space is near any wall of the container"""
        return (self.x < buffer or 
                self.y < buffer or 
                container_dims[0] - (self.x + self.width) < buffer or 
                container_dims[1] - (self.y + self.depth) < buffer or 
                container_dims[2] - (self.z + self.height) < buffer)
                
    def get_temperature_safe_subspace(self, container_dims, buffer=0.1):
        """Create a new space that is buffered from container walls"""
        # Calculate safe coordinates with buffer from walls
        safe_x = max(self.x, buffer)
        safe_y = max(self.y, buffer)
        
        # Calculate safe dimensions taking into account wall buffers
        safe_width = min(self.width, container_dims[0] - safe_x - buffer)
        safe_depth = min(self.depth, container_dims[1] - safe_y - buffer)
        safe_height = min(self.height, container_dims[2] - self.z - buffer)
        
        # Create new space if dimensions are positive
        if safe_width > 0 and safe_depth > 0 and safe_height > 0:
            safe_space = MaximalSpace(safe_x, safe_y, self.z, safe_width, safe_depth, safe_height)
            safe_space.temperature_safe = True
            return safe_space
        else:
            return None
            
    def __str__(self):
        """String representation with temperature safety info"""
        safety = "TEMP-SAFE" if self.temperature_safe else "STD-SPACE"
        return f"{safety} Space at ({self.x:.2f}, {self.y:.2f}, {self.z:.2f}) with dims {self.width:.2f}×{self.height:.2f}×{self.depth:.2f}m"
        
    def __repr__(self):
        return self.__str__()