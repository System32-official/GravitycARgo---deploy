"""
Item class definition for container packing
"""
import random
from typing import Tuple
from modules.utils import check_overlap_2d

class Item:
    def __init__(self, name, length, width, height, weight, quantity, fragility, stackable, boxing_type, bundle, load_bearing=0, temperature_sensitivity=None):
        self.name = name
        self.original_dims = (float(length), float(width), float(height))
        self.weight = float(weight)
        self.quantity = int(quantity)  # Ensure quantity is integer
        self.fragility = fragility
        self.stackable = stackable
        self.boxing_type = boxing_type
        self.bundle = bundle
        self.position = None
        self.items_above = []
        self.load_bearing = float(load_bearing) if load_bearing else 0
        self.temperature_sensitivity = temperature_sensitivity
        self.needs_insulation = False  # Flag for temperature-sensitive items that need insulation
        
        # Set color based on fragility level
        if fragility == 'HIGH':
            self.color = 'rgb(220, 50, 50)'  # Red for high fragility
        elif fragility == 'MEDIUM':
            self.color = 'rgb(240, 180, 50)'  # Orange/yellow for medium fragility
        else:  # LOW or unspecified
            self.color = 'rgb(100, 180, 100)'  # Green for low fragility
        
        # Calculate dimensions with smarter bundling
        if bundle == 'YES' and self.quantity > 1:  # Use self.quantity after conversion
            self.dimensions = self._calculate_bundle_dimensions()
            self.weight = self.weight * self.quantity  # Use converted values
        else:
            self.dimensions = self.original_dims

    def _calculate_bundle_dimensions(self) -> Tuple[float, float, float]:
        """Calculate optimal bundle dimensions considering container constraints"""
        orig_l, orig_w, orig_h = self.original_dims
        qty = int(self.quantity)  # Ensure integer quantity
        
        # Maximum container dimensions to respect
        max_length = 13.0  # Slightly less than typical container length
        max_width = 2.4    # Standard container width
        max_height = 2.4   # Standard container height
        
        # Find best arrangement that respects container dimensions
        best_arrangement = None
        best_score = float('inf')  # Lower score is better
        
        # Try different arrangements
        for x in range(1, qty + 1):
            for y in range(1, qty + 1):
                z = -(-qty // (x * y))  # Ceiling division
                
                # Calculate dimensions for this arrangement
                length = orig_l * x
                width = orig_w * y
                height = orig_h * z
                
                # Skip if any dimension exceeds container limits
                if width > max_width or height > max_height or length > max_length:
                    continue
                    
                # Calculate score (prefer lower height and width over length)
                score = (height * 3) + (width * 2) + length
                
                # Check if this arrangement is complete and better than current best
                if x * y * z >= qty and score < best_score:
                    best_score = score
                    best_arrangement = (x, y, z)
        
        if best_arrangement:
            x, y, z = best_arrangement
            return (orig_l * x, orig_w * y, orig_h * z)
            
        # If no valid arrangement found, try to minimize height and width
        area_needed = orig_l * orig_w * qty
        max_layers = int(max_height / orig_h)
        min_layers = max(1, -(-qty // int((max_length * max_width) / (orig_l * orig_w))))
        
        for layers in range(min_layers, max_layers + 1):
            items_per_layer = -(-qty // layers)
            # Try to arrange items in each layer
            width_count = int(max_width / orig_w)
            length_count = -(-items_per_layer // width_count)
            
            if length_count * orig_l <= max_length:
                return (orig_l * length_count, orig_w * width_count, orig_h * layers)
        
        # If still no solution, return minimal stacking arrangement
        return (orig_l, orig_w, orig_h * min(qty, max_layers))

    def __eq__(self, other):
        """Equality comparison based on item name"""
        if not isinstance(other, Item):
            return False
        return self.name == other.name

    def __hash__(self):
        """Hash based on item name for use in sets and dictionaries"""
        return hash(self.name)

    def __repr__(self):
        """String representation for debugging"""
        return f"Item(name='{self.name}', dims={self.dimensions}, weight={self.weight})"