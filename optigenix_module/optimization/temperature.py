"""
Temperature constraint handler module for 3D container packing optimization.
Centralizes all temperature-related logic for temperature-sensitive items.
"""
import logging
import os
from typing import List, Tuple, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("temperature")
# Set temperature logger to DEBUG level to reduce terminal output
# Only critical temperature messages will be shown in terminal
logger.setLevel(logging.WARNING)

class TemperatureConstraintHandler:
    """
    Handles temperature constraints for packing temperature-sensitive items
    
    This class centralizes all temperature-related logic for the packing algorithm,
    including checking temperature constraints, preprocessing items, and providing
    feedback about temperature-related placements.
    """
    
    def __init__(self, route_temperature=None):
        """Initialize the temperature constraint handler"""
        self.route_temperature = route_temperature
        logger.info(f"Temperature constraint handler initialized with route temperature: {route_temperature}°C")
    
    def preprocess_items_temperature(self, items):
        """
        Preprocess items to identify temperature sensitivity requirements
        
        Args:
            items: List of items to process
            
        Returns:
            List of items with temperature sensitivity flags set
        """
        if self.route_temperature is None:
            logger.info("No route temperature specified, skipping temperature preprocessing")
            return items
            
        logger.info(f"Preprocessing items for temperature sensitivity at {self.route_temperature}°C")
        temp_sensitive_count = 0
        
        for item in items:
            if hasattr(item, 'temperature_sensitivity') and item.temperature_sensitivity:
                try:
                    if 'n/a' not in str(item.temperature_sensitivity).lower():
                        temp_range = str(item.temperature_sensitivity).replace('°C', '').split(' to ')
                        min_temp = float(temp_range[0])
                        max_temp = float(temp_range[1])
                        
                        if self.route_temperature < min_temp or self.route_temperature > max_temp:
                            item.needs_insulation = True
                            temp_sensitive_count += 1
                            logger.info(f"Item {item.name} needs insulation (temp range: {min_temp}°C to {max_temp}°C)")
                            # Add a significant weight penalty to ensure these items get priority
                            item.temperature_priority = 1000  # Artificial high weight to prioritize temp-sensitive items
                            # Set color to blue for temperature-sensitive items for visualization
                            item.color = 'rgb(0, 128, 255)'  # Sky blue color
                        else:
                            item.temperature_priority = 0
                            item.needs_insulation = False
                except (ValueError, IndexError) as e:
                    logger.error(f"Error processing temperature for {item.name}: {e}")
                    item.temperature_priority = 0
                    item.needs_insulation = False
            else:
                item.temperature_priority = 0
                item.needs_insulation = False
        
        logger.info(f"Identified {temp_sensitive_count} temperature-sensitive items")
        return items
    
    def check_temperature_constraints(self, item, position, container_dimensions):
        """
        Check if the item placement satisfies temperature constraints
        
        Args:
            item: The item to be placed
            position: The (x, y, z) position for placement
            container_dimensions: The (width, depth, height) of the container
            
        Returns:
            bool: True if position satisfies temperature constraints, False otherwise
        """
        if not hasattr(item, 'needs_insulation') or not item.needs_insulation:
            return True  # No temperature constraints for regular items
            
        if self.route_temperature is None:
            return True  # No temperature constraints if route temperature not set
        
        # Check wall proximity - enforce minimum distance from walls
        wall_buffer = 0.3  # 30cm buffer from walls
        x, y, z = position
        w, d, h = item.dimensions
        
        # Calculate distance from walls
        if (x < wall_buffer or 
            y < wall_buffer or 
            container_dimensions[0] - (x + w) < wall_buffer or 
            container_dimensions[1] - (y + d) < wall_buffer or
            container_dimensions[2] - (z + h) < wall_buffer):
            logger.info(f"❌ Rejected position for temperature-sensitive item {item.name} at {position}")
            logger.info(f"   Item would be TOO CLOSE TO CONTAINER WALL (less than {wall_buffer*100}cm)")
            return False
        
        # Calculate central position score
        center_x = container_dimensions[0] / 2
        center_y = container_dimensions[1] / 2
        item_center_x = x + w/2
        item_center_y = y + d/2
        
        # Check if item is in central area (preferred for temperature protection)
        is_central = (
            center_x - container_dimensions[0]/4 <= item_center_x <= center_x + container_dimensions[0]/4 and
            center_y - container_dimensions[1]/4 <= item_center_y <= center_y + container_dimensions[1]/4
        )
        
        if is_central:
            logger.info(f"✅ Good central position for temperature-sensitive item {item.name}")
            return True
            
        # If not central, position might still be acceptable if well-insulated
        logger.info(f"⚠️ Temperature-sensitive item {item.name} not in central position")
        return True  # Allow placement, but it's not ideal
    
    def calculate_temperature_fitness_bonus(self, item, position, container_dimensions, surrounding_items=None):
        """
        Calculate temperature-related fitness bonus for an item placement
        
        Args:
            item: The item being evaluated
            position: The (x, y, z) position of the item
            container_dimensions: The (width, depth, height) of the container
            surrounding_items: Optional list of items surrounding this item
            
        Returns:
            float: Temperature fitness bonus (0.0 to 0.1)
        """
        if not hasattr(item, 'needs_insulation') or not item.needs_insulation:
            return 0.0  # No temperature bonus for regular items
            
        if self.route_temperature is None:
            return 0.0  # No temperature bonus if route temperature not set
            
        # Calculate distance from walls
        x, y, z = position
        w, d, h = item.dimensions
        
        min_wall_dist = min(
            x,                                  # Distance from left wall
            y,                                  # Distance from front wall
            container_dimensions[0] - (x + w),  # Distance from right wall
            container_dimensions[1] - (y + d),  # Distance from back wall
            z,                                  # Distance from bottom
            container_dimensions[2] - (z + h)   # Distance from top
        )
        
        # Calculate central position score (0-1)
        center_x = container_dimensions[0] / 2
        center_y = container_dimensions[1] / 2
        item_center_x = x + w/2
        item_center_y = y + d/2
        
        # Calculate distance from center (normalized 0-1)
        distance_from_center = ((item_center_x - center_x)**2 + (item_center_y - center_y)**2) / (
            (container_dimensions[0]/2)**2 + (container_dimensions[1]/2)**2)
        
        # Central position bonus (0-0.05)
        central_bonus = 0.05 * (1 - distance_from_center)
        
        # Wall distance bonus (0-0.05), maxes out at 50cm
        wall_dist_bonus = min(0.05, min_wall_dist / 10.0)
        
        # Count surrounding items (insulation bonus)
        insulation_bonus = 0.0
        if surrounding_items:
            insulating_items = sum(1 for item in surrounding_items if not getattr(item, 'needs_insulation', False))
            insulation_bonus = min(0.03, insulating_items * 0.01)  # 0.01 per regular item up to 0.03
        
        # Calculate total bonus (max 0.1)
        return min(0.1, central_bonus + wall_dist_bonus + insulation_bonus)

    @staticmethod
    def get_route_temperature():
        """Get route temperature from environment or use default"""
        return float(os.environ.get("ROUTE_TEMPERATURE", 25.0))
        
    def calculate_temperature_metrics(self, container):
        """
        Calculate temperature-related metrics for container evaluation
        
        Args:
            container: Container with packed items
            
        Returns:
            dict: Dictionary with temperature-related metrics
        """
        metrics = {
            'temp_items_count': 0,
            'temp_items_central': 0,
            'temp_items_well_insulated': 0,
            'avg_wall_distance': 0.0
        }
        
        temp_items = [i for i in container.items if getattr(i, 'needs_insulation', False)]
        if not temp_items:
            return metrics
            
        metrics['temp_items_count'] = len(temp_items)
        total_dist = 0
        
        # Calculate center of container
        center_x = container.dimensions[0] / 2
        center_y = container.dimensions[1] / 2
        
        for item in temp_items:
            x, y, z = item.position
            w, d, h = item.dimensions
            
            # Check if central
            item_center_x = x + w/2
            item_center_y = y + d/2
            is_central = (
                center_x - container.dimensions[0]/4 <= item_center_x <= center_x + container.dimensions[0]/4 and
                center_y - container.dimensions[1]/4 <= item_center_y <= center_y + container.dimensions[1]/4
            )
            
            if is_central:
                metrics['temp_items_central'] += 1
                
            # Calculate minimum wall distance
            min_dist = min(
                x,                                   # Distance from left wall
                y,                                   # Distance from front wall
                container.dimensions[0] - (x + w),   # Distance from right wall
                container.dimensions[1] - (y + d),   # Distance from back wall
                z,                                   # Distance from bottom
                container.dimensions[2] - (z + h)    # Distance from top
            )
            total_dist += min_dist
            
            # Check if well insulated by surrounding items
            surrounding_items = 0
            for other_item in container.items:
                if other_item == item:
                    continue
                # Check if items are in contact
                if self._has_surface_contact(item.position, item.dimensions, other_item):
                    surrounding_items += 1
            
            if surrounding_items >= 2:
                metrics['temp_items_well_insulated'] += 1
        
        metrics['avg_wall_distance'] = total_dist / len(temp_items) if temp_items else 0
        return metrics

    def _has_surface_contact(self, pos, dims, other_item):
        """Check if two items have surface contact"""
        # This is a simplified version - in practice you'd use the container's actual method
        x1, y1, z1 = pos
        w1, d1, h1 = dims
        x2, y2, z2 = other_item.position
        w2, d2, h2 = other_item.dimensions
        
        # Check if boxes overlap in x-y plane and are adjacent in z
        x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
        y_overlap = max(0, min(y1 + d1, y2 + d2) - max(y1, y2))
        z_contact = (abs(z1 - (z2 + h2)) < 0.001) or (abs(z2 - (z1 + h1)) < 0.001)
        
        if x_overlap > 0 and y_overlap > 0 and z_contact:
            return True
            
        # Check if boxes overlap in x-z plane and are adjacent in y
        x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
        z_overlap = max(0, min(z1 + h1, z2 + h2) - max(z1, z2))
        y_contact = (abs(y1 - (y2 + d2)) < 0.001) or (abs(y2 - (y1 + d1)) < 0.001)
        
        if x_overlap > 0 and z_overlap > 0 and y_contact:
            return True
            
        # Check if boxes overlap in y-z plane and are adjacent in x
        y_overlap = max(0, min(y1 + d1, y2 + d2) - max(y1, y2))
        z_overlap = max(0, min(z1 + h1, z2 + h2) - max(z1, z2))
        x_contact = (abs(x1 - (x2 + w2)) < 0.001) or (abs(x2 - (x1 + w1)) < 0.001)
        
        if y_overlap > 0 and z_overlap > 0 and x_contact:
            return True
            
        return False