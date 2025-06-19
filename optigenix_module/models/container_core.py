"""
Core functionality for the EnhancedContainer class
"""
import numpy as np
from typing import List, Tuple

from optigenix_module.models.item import Item
from optigenix_module.models.space import MaximalSpace
from modules.utils import check_overlap_2d

class ContainerCore:
    """Contains core container operations and basic geometry checks"""
    
    def _get_valid_rotations(self, item):
        """Get all valid rotations considering container constraints"""
        rotations = []
        l, w, h = item.dimensions
        
        # Base orientations
        possible_rotations = [
            (l, w, h), (l, h, w),
            (w, l, h), (w, h, l),
            (h, l, w), (h, w, l)
        ]
        
        # Filter rotations based on container dimensions and item properties
        for rot in possible_rotations:
            if (all(d <= max_d for d, max_d in zip(rot, self.dimensions)) and
                (item.fragility != 'HIGH' or rot[2] <= item.dimensions[2])):
                rotations.append(rot)
        
        return rotations

    def _check_overlap_2d(self, rect1: Tuple[float, float, float, float], 
                       rect2: Tuple[float, float, float, float]) -> bool:
        """Check if two rectangles overlap in 2D using shared utility"""
        return check_overlap_2d(rect1, rect2)

    def _check_overlap_3d(self, box1: Tuple[float, float, float, float, float, float],
                         box2: Tuple[float, float, float, float, float, float]) -> bool:
        """Check if two boxes overlap in 3D"""
        x1, y1, z1, w1, d1, h1 = box1
        x2, y2, z2, w2, d2, h2 = box2
        
        return not (x1 + w1 <= x2 or x2 + w2 <= x1 or
                   y1 + d1 <= y2 or y2 + d2 <= y1 or
                   z1 + h1 <= z2 or z2 + h2 <= z1)

    def _calculate_overlap_area(self, rect1: Tuple[float, float, float, float], 
                          rect2: Tuple[float, float, float, float]) -> float:
        """Calculate overlap area between two rectangles"""
        x1, y1, w1, d1 = rect1
        x2, y2, w2, d2 = rect2
        
        x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
        y_overlap = max(0, min(y1 + d1, y2 + d2) - max(y1, y2))
        
        return x_overlap * y_overlap

    def _is_valid_placement(self, item: Item, pos: Tuple[float, float, float], 
                          dims: Tuple[float, float, float]) -> bool:
        """Check if placement is valid including stackability"""
        x, y, z = pos
        w, d, h = dims
        
        # Check container boundaries
        if (x + w > self.dimensions[0] or
            y + d > self.dimensions[1] or
            z + h > self.dimensions[2] or
            x < 0 or y < 0 or z < 0):
            return False
            
        # Check overlap with other items
        for placed_item in self.items:
            if self._check_overlap_3d(
                (x, y, z, w, d, h),
                (placed_item.position[0], placed_item.position[1], placed_item.position[2],
                 placed_item.dimensions[0], placed_item.dimensions[1], placed_item.dimensions[2])
            ):
                return False
                
        # Check stackability and fragility
        if z > 0:  # If not on the ground
            items_below = self._get_items_below((x, y, z), (w, d))
            if not items_below:
                return False  # Need support from below
            
            # Check fragility and stackability of items below
            for below_item in items_below:
                # Can't stack on HIGH fragility items
                if below_item.fragility == 'HIGH':
                    return False
                    
                # Can't stack if item below is not stackable
                if not below_item.stackable:
                    return False
                    
                # Check load bearing capacity
                overlap_area = self._calculate_overlap_area(
                    (x, y, w, d),
                    (below_item.position[0], below_item.position[1], 
                     below_item.dimensions[0], below_item.dimensions[1])
                )
                total_area = below_item.dimensions[0] * below_item.dimensions[1]
                weight_ratio = overlap_area / total_area
                
                if below_item.load_bearing > 0 and item.weight > below_item.load_bearing * weight_ratio:
                    return False
                      # Check if current item can support weight above it based on its fragility
            if item.fragility == 'HIGH':
                # Don't allow any items to be stacked on high fragility items
                for placed_item in self.items:
                    if (placed_item.position and 
                        placed_item.position[2] > z + h and
                        check_overlap_2d(
                            (x, y, w, d),
                            (placed_item.position[0], placed_item.position[1],
                             placed_item.dimensions[0], placed_item.dimensions[1])
                        )):                        return False
                
        return True
        
    def _get_items_below(self, pos: Tuple[float, float, float], 
                        dims: Tuple[float, float]) -> List[Item]:
        """Find items directly below the given position"""
        x, y, z = pos
        w, d = dims
        items_below = []
        
        for item in self.items:
            if (abs(item.position[2] + item.dimensions[2] - z) < 0.001 and
                check_overlap_2d(
                    (x, y, w, d),
                    (item.position[0], item.position[1], 
                     item.dimensions[0], item.dimensions[1])
                )):
                items_below.append(item)
                
        return items_below

    def _has_support(self, pos, dims):
        """Check if position has support from below"""
        if pos[2] == 0:  # On the ground
            return True
            
        x, y, z = pos
        w, d, h = dims
          # Check if there's an item directly below
        for item in self.items:
            if (item.position[2] + item.dimensions[2] == z and
                check_overlap_2d(
                    (x, y, w, d),
                    (item.position[0], item.position[1], 
                     item.dimensions[0], item.dimensions[1])
                )):
                return True
        return False

    def _can_merge_spaces(self, s1: MaximalSpace, s2: MaximalSpace) -> bool:
        """Check if two spaces can be merged"""
        # Check if spaces are adjacent and have same dimensions in two directions
        return ((s1.x + s1.width == s2.x or s2.x + s2.width == s1.x) and
                s1.y == s2.y and s1.z == s2.z and
                s1.height == s2.height and s1.depth == s2.depth)

    def _merge_two_spaces(self, s1: MaximalSpace, s2: MaximalSpace) -> MaximalSpace:
        """Merge two spaces into one"""
        x = min(s1.x, s2.x)
        width = s1.width + s2.width
        return MaximalSpace(x, s1.y, s1.z, width, s1.height, s1.depth)

    def _merge_spaces(self):
        """Merge overlapping spaces"""
        # First sort spaces by size and position to prioritize optimal merging
        self.spaces.sort(key=lambda s: (-s.get_volume(), s.x, s.y, s.z))
        
        i = 0
        while i < len(self.spaces):
            j = i + 1
            while j < len(self.spaces):
                if self._can_merge_spaces(self.spaces[i], self.spaces[j]):
                    self.spaces[i] = self._merge_two_spaces(self.spaces[i], self.spaces[j])
                    self.spaces.pop(j)
                else:
                    j += 1
            i += 1
            
        # Sort spaces by position and size for optimal placement
        self.spaces.sort(key=lambda s: (
            s.z,  # Prioritize lower heights first
            s.x**2 + s.y**2,  # Prefer spaces closer to origin
            -s.get_volume(),  # Prefer larger spaces for better fitting
            min(s.width, s.depth)  # Prefer spaces with similar dimensions for better interlocking
        ))

    def _update_spaces(self, pos, dims, used_space=None):
        """Update available spaces after placing an item"""
        x, y, z = pos
        w, d, h = dims
        
        if used_space:
            # Remove used space
            self.spaces.remove(used_space)
            
            # Generate new spaces
            new_spaces = []
            
            # Space above the item
            if used_space.height > h:
                new_spaces.append(MaximalSpace(
                    x, y, z + h,
                    w, used_space.height - h, d
                ))
                
            # Space to the right
            if used_space.width > w:
                new_spaces.append(MaximalSpace(
                    x + w, y, z,
                    used_space.width - w, used_space.height, used_space.depth
                ))
                
            # Space to the front
            if used_space.depth > d:
                new_spaces.append(MaximalSpace(
                    x, y + d, z,
                    used_space.width, used_space.height, used_space.depth - d
                ))
            
            # Add new spaces and merge overlapping ones
            self.spaces.extend(new_spaces)
            self._merge_spaces()

    def _check_stackability(self, item: Item, pos: Tuple[float, float, float]) -> bool:
        """Check if an item can be stacked at the given position"""
        if pos[2] == 0:  # Items can always be placed on the floor
            return True
            
        # Get items below this position
        items_below = self._get_items_below(pos, (item.dimensions[0], item.dimensions[1]))
        
        # If no items below, not stackable
        if not items_below:
            return False
            
        # Check weight constraints and stackability
        total_weight_above = item.weight
        for below_item in items_below:
            # If item below is not stackable, can't stack on it
            if not below_item.stackable:
                return False
            
            # If item is too heavy for the item below
            if hasattr(below_item, 'load_bearing') and below_item.load_bearing > 0:
                overlap_area = self._calculate_overlap_area(
                    (pos[0], pos[1], item.dimensions[0], item.dimensions[1]),
                    (below_item.position[0], below_item.position[1], 
                     below_item.dimensions[0], below_item.dimensions[1])
                )
                total_area = below_item.dimensions[0] * below_item.dimensions[1]
                weight_ratio = overlap_area / total_area
                if total_weight_above > below_item.load_bearing * weight_ratio:
                    return False
                    
        return True

    def _has_surface_contact(self, pos1, dims1, item2):
        """Check if two items have significant surface contact"""
        x1, y1, z1 = pos1
        w1, d1, h1 = dims1
        x2, y2, z2 = item2.position
        w2, d2, h2 = item2.dimensions
        
        tolerance = 0.001  # Small tolerance for floating point comparison
        
        # Check if items are adjacent (sharing a face)
        # Top/bottom face contact
        if abs(z1 - (z2 + h2)) < tolerance or abs((z1 + h1) - z2) < tolerance:
            overlap = self._calculate_overlap_area(
                (x1, y1, w1, d1),
                (x2, y2, w2, d2)
            )
            if overlap > min(w1 * d1, w2 * d2) * 0.1:  # At least 10% overlap
                return True
                
        # Front/back face contact
        if abs(y1 - (y2 + d2)) < tolerance or abs((y1 + d1) - y2) < tolerance:
            overlap = self._calculate_overlap_area(
                (x1, z1, w1, h1),
                (x2, z2, w2, h2)
            )
            if overlap > min(w1 * h1, w2 * h2) * 0.1:
                return True
                
        # Left/right face contact
        if abs(x1 - (x2 + w2)) < tolerance or abs((x1 + w1) - x2) < tolerance:
            overlap = self._calculate_overlap_area(
                (y1, z1, d1, h1),
                (y2, z2, d2, h2)
            )
            if overlap > min(d1 * h1, d2 * h2) * 0.1:
                return True
                
        return False

    def _calculate_diversification_score(self, items):
        """Calculate diversity score for a group of items"""
        if not items:
            return 0.0
            
        # Calculate variance in dimensions and positions
        dim_variances = []
        pos_variances = []
        
        # Get arrays of dimensions and positions
        dims = [(i.dimensions[0], i.dimensions[1], i.dimensions[2]) for i in items]
        positions = [(i.position[0], i.position[1], i.position[2]) if i.position else (0,0,0) 
                    for i in items]
        
        # Calculate variance for each dimension
        for i in range(3):
            dim_values = [d[i] for d in dims]
            pos_values = [p[i] for p in positions]
            
            dim_mean = sum(dim_values) / len(dim_values)
            pos_mean = sum(pos_values) / len(pos_values)
            
            dim_var = sum((v - dim_mean) ** 2 for v in dim_values) / len(dim_values)
            pos_var = sum((v - pos_mean) ** 2 for v in pos_values) / len(pos_values)
            
            dim_variances.append(dim_var)
            pos_variances.append(pos_var)
            
        # Combine variances into a single score
        dim_score = sum(dim_variances) / 3
        pos_score = sum(pos_variances) / 3
        
        # Weight position variance more heavily as it's more important for packing
        return (dim_score * 0.3 + pos_score * 0.7) / (self.dimensions[0] * self.dimensions[1] * self.dimensions[2])