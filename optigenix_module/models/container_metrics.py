"""
Metrics calculation for the EnhancedContainer class
"""
import numpy as np
from typing import Tuple, List
from modules.utils import calculate_overlap_area, check_overlap_2d

class ContainerMetrics:
    """Contains methods for calculating metrics and scores"""
    
    def _update_metrics(self):
        """Enhanced metrics calculation with error handling"""
        try:
            # Calculate packed volume safely
            packed_volume = sum(
                max(0, item.dimensions[0]) * max(0, item.dimensions[1]) * max(0, item.dimensions[2])
                for item in self.items
            )
            
            # Update metrics with bounds checking - store as decimal (0.0-1.0) not percentage
            self.volume_utilization = min(1.0, packed_volume / max(0.001, self.total_volume))
            self.total_weight = sum(max(0, item.weight) for item in self.items)
            self.remaining_volume = max(0, self.total_volume - packed_volume)

            # Update center of gravity
            if self.items:
                self._update_center_of_gravity()
                
        except Exception as e:
            print(f"Error updating metrics: {str(e)}")
            # Set safe default values
            self.volume_utilization = 0
            self.total_weight = 0
            self.remaining_volume = self.total_volume

    def _update_center_of_gravity(self):
        """Calculate center of gravity after each item placement"""
        total_moment = np.array([0.0, 0.0, 0.0])
        self.total_weight = 0
        
        for item in self.items:
            pos = np.array(item.position)
            center = pos + np.array(item.dimensions) / 2
            total_moment += center * item.weight
            self.total_weight += item.weight
            
        if self.total_weight > 0:
            self.center_of_gravity = total_moment / self.total_weight

    def _update_weight_distribution(self, item) -> None:
        """Update weight distribution when placing a new item"""
        # Calculate which third of the container the item is in
        section_size = self.dimensions[0] / 3
        x = item.position[0]
        section = int(x / section_size)
        
        # Update weight distribution dictionary
        if section not in self.weight_distribution:
            self.weight_distribution[section] = 0
        self.weight_distribution[section] += item.weight
        
        # Update weight map for detailed balance calculation
        col = int((x / self.dimensions[0]) * self.weight_map.shape[1])
        row = int((item.position[1] / self.dimensions[1]) * self.weight_map.shape[0])
        if 0 <= row < self.weight_map.shape[0] and 0 <= col < self.weight_map.shape[1]:
            self.weight_map[row, col] += item.weight

    def _calculate_weight_balance_score(self) -> float:
        """Calculate overall weight balance score"""
        if not self.weight_distribution:
            return 0.0
            
        weights = list(self.weight_distribution.values())
        total_weight = sum(weights)
        if total_weight == 0:
            return 1.0
            
        # Calculate variance in weight distribution
        mean_weight = total_weight / len(weights)
        variance = sum((w - mean_weight) ** 2 for w in weights) / len(weights)
        
        # Return normalized score (0-1, higher is better)
        return 1.0 / (1.0 + variance / 1000)

    def _calculate_interlocking_score(self) -> float:
        """Calculate overall interlocking score"""
        if not self.items:
            return 0.0
            
        total_contacts = 0
        for item in self.items:
            for other in self.items:
                if item != other and self._has_surface_contact(
                    item.position, item.dimensions, other
                ):
                    total_contacts += 1
                    
        # Return normalized score (0-1, higher is better)
        max_possible_contacts = len(self.items) * 6  # Each item can touch 6 sides
        return total_contacts / max_possible_contacts

    def _calculate_stability_score(self, item, pos, dims):
        """Calculate stability score for item placement"""
        x, y, z = pos
        w, d, h = dims
        score = 0
        
        # Check support from below
        support_area = 0
        total_area = w * d
        items_below = self._get_items_below(pos, (w, d))
        
        # Ground placement is most stable
        if z == 0:
            return 1.0
            
        # Calculate support from items below
        for below_item in items_below:
            overlap = self._calculate_overlap_area(
                (x, y, w, d),
                (below_item.position[0], below_item.position[1],
                 below_item.dimensions[0], below_item.dimensions[1])
            )
            support_area += overlap
            
        # Calculate support ratio
        support_ratio = support_area / total_area
        score += support_ratio * 5
        
        # Additional stability factors
        if support_ratio >= 0.8:  # Well supported
            score += 2
            
        # Lower center of gravity is better
        if h <= max(w, d):
            score += 1
            
        # Wall contact adds stability
        wall_contacts = 0
        if x == 0 or x + w == self.dimensions[0]:
            wall_contacts += 1
        if y == 0 or y + d == self.dimensions[1]:
            wall_contacts += 1
        score += wall_contacts * 0.5
        
        # Normalize final score to 0-1 range
        return min(1.0, score / 8.0)  # 8.0 is maximum possible score

    def _calculate_local_density(self, pos, dims):
        """Calculate local density of items near position"""
        x, y, z = pos
        w, d, h = dims
        nearby_volume = 0
        total_volume = w * d * h * 27  # 3x3x3 grid around position
        
        for item in self.items:
            if (abs(item.position[0] - x) <= w * 2 and
                abs(item.position[1] - y) <= d * 2 and
                abs(item.position[2] - z) <= h * 2):
                nearby_volume += (item.dimensions[0] * 
                                item.dimensions[1] * 
                                item.dimensions[2])
        
        return nearby_volume / total_volume

    def _calculate_wall_contact(self, pos, dims):
        """Calculate how many container walls the item touches"""
        x, y, z = pos
        l, w, h = dims
        score = 0
        tolerance = 0.001
        
        # Check wall contacts
        if abs(x) < tolerance or abs(x + l - self.dimensions[0]) < tolerance:
            score += 1
        if abs(y) < tolerance or abs(y + w - self.dimensions[1]) < tolerance:
            score += 1
        if abs(z) < tolerance:  # Floor contact
            score += 2
            
        return score

    def _evaluate_cog_impact(self, item, pos):
        """Evaluate how an item placement affects center of gravity"""
        temp_cog = np.array(self.center_of_gravity)
        temp_weight = self.total_weight
        
        item_center = np.array(pos) + np.array(item.dimensions) / 2
        new_cog = (temp_cog * temp_weight + item_center * item.weight) / (temp_weight + item.weight)
        
        # Prefer positions that keep COG near center
        target = np.array(self.dimensions) / 2
        current_dist = np.linalg.norm(temp_cog - target)
        new_dist = np.linalg.norm(new_cog - target)
        
        return 1.0 / (1.0 + new_dist)

    def _has_surface_contact(self, pos1, dims1, item2) -> bool:
        """Check if two items have surface contact"""
        if not item2.position:  # Skip if item2 hasn't been placed
            return False
            
        x1, y1, z1 = pos1
        l1, w1, h1 = dims1
        x2, y2, z2 = item2.position
        l2, w2, h2 = item2.dimensions
        
        # Check for surface contact on each face with tolerance
        tolerance = 0.001
          # Bottom face contact
        if abs(z1 - (z2 + h2)) < tolerance:
            if check_overlap_2d(
                (x1, y1, l1, w1),
                (x2, y2, l2, w2)
            ):
                return True
                  # Top face contact
        if abs((z1 + h1) - z2) < tolerance:
            if check_overlap_2d(
                (x1, y1, l1, w1),
                (x2, y2, l2, w2)
            ):
                return True
                  # Front/back face contacts
        if abs(y1 - (y2 + w2)) < tolerance or abs((y1 + w1) - y2) < tolerance:
            if check_overlap_2d(
                (x1, z1, l1, h1),
                (x2, z2, l2, h2)
            ):
                return True
                  # Left/right face contacts
        if abs(x1 - (x2 + l2)) < tolerance or abs((x1 + l1) - x2) < tolerance:
            if check_overlap_2d(
                (y1, z1, w1, h1),
                (y2, z2, w2, h2)
            ):
                return True
                
        return False

    def _is_near_container_wall(self, pos, dims, wall_buffer=0.1) -> bool:
        """Check if an item is positioned near a container wall"""
        x, y, z = pos
        l, w, h = dims
        
        # Check proximity to container walls
        if (x <= wall_buffer or 
            y <= wall_buffer or 
            x + l >= self.dimensions[0] - wall_buffer or 
            y + w >= self.dimensions[1] - wall_buffer):
            return True
            
        return False
        
    def _check_temperature_constraints(self, item, pos, route_temperature):
        """
        Check if item placement satisfies temperature constraints.
        Only items affected by route temperature (outside their acceptable range)
        will be colored blue and require special positioning.
        """
        if not item.temperature_sensitivity or item.temperature_sensitivity.lower() == 'n/a':
            return True
            
        try:
            # Parse temperature range from the sensitivity string (e.g., "10°C to 30°C")
            temp_range = item.temperature_sensitivity.replace('°C', '').split(' to ')
            min_temp = float(temp_range[0])
            max_temp = float(temp_range[1])
            
            # Check if route temperature exceeds item's temperature range
            if route_temperature > max_temp:
                # Item needs temperature protection
                item.needs_insulation = True
                # Set special color for temperature-sensitive items affected by route temperature
                item.color = f'rgb(0, 128, 255)'  # Sky blue color
            else:
                # Temperature-sensitive but not affected by route temperature
                # Reset needs_insulation flag if it was set previously
                item.needs_insulation = False
                # Let the item use standard coloring (will be set in Item class initialization)
            
            return True
            
        except (ValueError, IndexError):
            # If we can't parse the temperature range, assume it's fine
            return True
    
    def calculate_overall_stability_score(self) -> float:
        """Calculate overall stability score for all items in the container"""
        if not self.items:
            return 0.0
            
        total_score = 0.0
        item_count = 0
        
        for item in self.items:
            if hasattr(item, 'position') and item.position and hasattr(item, 'dimensions'):
                stability_score = self._calculate_stability_score(item, item.position, item.dimensions)
                total_score += stability_score
                item_count += 1
        
        return total_score / item_count if item_count > 0 else 0.0
    
    def calculate_overall_contact_ratio(self) -> float:
        """Calculate overall contact ratio for all items in the container"""
        if not self.items or len(self.items) < 2:
            return 0.0
            
        total_contact_area = 0.0
        total_surface_area = 0.0
        
        for item in self.items:
            if not (hasattr(item, 'position') and item.position and hasattr(item, 'dimensions')):
                continue
                
            # Calculate total surface area for this item
            w, d, h = item.dimensions
            item_surface_area = 2 * (w*d + w*h + d*h)
            total_surface_area += item_surface_area
            
            # Calculate contact area with other items
            for other_item in self.items:
                if item != other_item and hasattr(other_item, 'position') and other_item.position:
                    contact_area = self._calculate_contact_area_between_items(
                        item.position, item.dimensions, other_item
                    )
                    total_contact_area += contact_area
        
        # Avoid double counting (each contact is counted twice in the loop above)
        total_contact_area /= 2
        
        return total_contact_area / total_surface_area if total_surface_area > 0 else 0.0
    
    def _calculate_contact_area_between_items(self, pos, dims, other_item):
        """Calculate contact area between two items (helper method)"""
        if not other_item.position:
            return 0.0
            
        x1, y1, z1 = pos
        w1, d1, h1 = dims
        x2, y2, z2 = other_item.position
        w2, d2, h2 = other_item.dimensions
        
        contact_area = 0.0
        tolerance = 0.001
        
        # Check X-face contact (left/right)
        if abs(x1 - (x2 + w2)) < tolerance or abs(x2 - (x1 + w1)) < tolerance:
            y_overlap = max(0, min(y1 + d1, y2 + d2) - max(y1, y2))
            z_overlap = max(0, min(z1 + h1, z2 + h2) - max(z1, z2))
            contact_area += y_overlap * z_overlap
        
        # Check Y-face contact (front/back)
        if abs(y1 - (y2 + d2)) < tolerance or abs(y2 - (y1 + d1)) < tolerance:
            x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
            z_overlap = max(0, min(z1 + h1, z2 + h2) - max(z1, z2))
            contact_area += x_overlap * z_overlap
        
        # Check Z-face contact (top/bottom)
        if abs(z1 - (z2 + h2)) < tolerance or abs(z2 - (z1 + h1)) < tolerance:
            x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
            y_overlap = max(0, min(y1 + d1, y2 + d2) - max(y1, y2))
            contact_area += x_overlap * y_overlap
        
        return contact_area
    
    def _get_items_below(self, pos, base_dims):
        """Get items that are below a given position (helper method)"""
        x, y = pos[0], pos[1]
        z = pos[2]
        w, d = base_dims
        
        items_below = []
        for item in self.items:
            if not (hasattr(item, 'position') and item.position):
                continue
                
            ix, iy, iz = item.position
            iw, id, ih = item.dimensions
            
            # Check if item is below and overlaps in XY plane
            if iz + ih <= z + 0.001:  # Item is below (with small tolerance)
                # Check XY overlap
                if (ix < x + w and ix + iw > x and 
                    iy < y + d and iy + id > y):
                    items_below.append(item)
        
        return items_below
    
    def _calculate_overlap_area(self, rect1, rect2):
        """Calculate overlap area between two rectangles (helper method)"""
        x1, y1, w1, h1 = rect1
        x2, y2, w2, h2 = rect2
        
        # Calculate overlap
        x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
        y_overlap = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
        
        return x_overlap * y_overlap