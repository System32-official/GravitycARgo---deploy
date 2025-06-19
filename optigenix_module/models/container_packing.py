"""
Packing algorithms for the EnhancedContainer class
"""
from typing import List, Tuple, Dict
import numpy as np
import logging

from optigenix_module.models.item import Item
from optigenix_module.models.space import MaximalSpace
from modules.utils import check_overlap_2d

# Initialize logger
logger = logging.getLogger(__name__)

"""Converted to use utility function - contents moved to utils.py"""

class ContainerPacking:
    """Contains methods for packing items into the container"""
    
    def pack_items(self, items: List[Item], route_temperature=None, constraint_weights=None):
        """Pack items with improved temperature constraint handling and constraint weights"""
        self.route_temperature = route_temperature  # Store route temperature for constraint checking
        
        # Initialize constraint weights with defaults if not provided
        self.constraint_weights = constraint_weights or {
            'volume_utilization_weight': 0.75,
            'stability_score_weight': 0.50,
            'contact_ratio_weight': 0.50,
            'weight_balance_weight': 0.25,
            'items_packed_ratio_weight': 0.25,
            'temperature_constraint_weight': 0.30
        }
        
        logger.info("Standard packing using constraint weights:")
        logger.info(f"  Volume: {self.constraint_weights['volume_utilization_weight']:.2f} | " +
                    f"Stability: {self.constraint_weights['stability_score_weight']:.2f} | " + 
                    f"Contact: {self.constraint_weights['contact_ratio_weight']:.2f} | " +
                    f"Balance: {self.constraint_weights['weight_balance_weight']:.2f} | " +
                    f"Packed: {self.constraint_weights['items_packed_ratio_weight']:.2f} | " +
                    f"Temperature: {self.constraint_weights.get('temperature_constraint_weight', 0):.2f}")
        
        expanded_items = []
        
        for item in items:
            if item.bundle == 'YES' and item.quantity > 1:
                # Handle bundled items - already processed in Item initialization
                expanded_items.append(item)
            else:
                # For non-bundled items, create individual copies
                try:
                    quantity = int(item.quantity)  # Ensure integer conversion
                    for i in range(quantity):
                        new_item = Item(
                            name=f"{item.name}_{i+1}",
                            length=float(item.original_dims[0]),
                            width=float(item.original_dims[1]),
                            height=float(item.original_dims[2]),
                            weight=float(item.weight),
                            quantity=1,
                            fragility=item.fragility,
                            stackable=item.stackable,
                            boxing_type=item.boxing_type,
                            bundle='NO',
                            load_bearing=getattr(item, 'load_bearing', 0),  # Properly copy load bearing capacity
                            temperature_sensitivity=getattr(item, 'temperature_sensitivity', None)
                        )
                        expanded_items.append(new_item)
                except ValueError as e:
                    print(f"Error converting quantity for item {item.name}: {e}")
                    continue

        # Identify temperature sensitive items and mark them
        if self.route_temperature is not None:
            for item in expanded_items:
                if hasattr(item, 'temperature_sensitivity') and item.temperature_sensitivity:
                    try:
                        if 'n/a' not in item.temperature_sensitivity.lower():
                            temp_range = item.temperature_sensitivity.replace('°C', '').split(' to ')
                            min_temp = float(temp_range[0])
                            max_temp = float(temp_range[1])
                            
                            # Mark if item needs temperature protection
                            if self.route_temperature < min_temp or self.route_temperature > max_temp:
                                item.needs_insulation = True
                                print(f"🌡️ Marking item {item.name} as temperature-sensitive: {item.temperature_sensitivity}")
                                print(f"   Route temperature ({self.route_temperature}°C) is outside range.")
                    except (ValueError, IndexError):
                        pass

        # CRITICAL FIX: Sort expanded items with enhanced temperature-awareness
        # This ensures temperature-sensitive items are packed first and get optimal positions
        sorted_items = sorted(expanded_items, 
                            key=lambda x: (
                                -getattr(x, 'needs_insulation', False),  # Temperature-sensitive items first
                                # More nuanced sorting for temperature items - place smallest ones first
                                # This helps avoid situations where large items can't find temperature-safe spots
                                0 if not getattr(x, 'needs_insulation', False) else -((x.dimensions[0] + x.dimensions[1] + x.dimensions[2])/3),
                                -(x.dimensions[0] * x.dimensions[1]),     # Then larger base area
                                x.dimensions[2],                         # Lower height preferred
                                -x.weight                                # Heavier items next
                            ))
                        
        # Print temperature-sensitive items for verification
        temp_items = [item for item in sorted_items if getattr(item, 'needs_insulation', False)]
        if temp_items:
            print(f"🌡️ Found {len(temp_items)} temperature-sensitive items that need insulation:")
            for item in temp_items:
                print(f"   - {item.name}: {item.temperature_sensitivity}")
        
        # Create temperature-safe zones (away from walls) for temperature-sensitive items
        if temp_items:
            wall_buffer = 0.3  # 30cm buffer from walls
            # Define the central area of the container as a temperature-safe zone
            safe_zone = MaximalSpace(
                wall_buffer,                          # x
                wall_buffer,                          # y
                0,                                    # z
                self.dimensions[0] - 2 * wall_buffer, # width
                self.dimensions[1] - 2 * wall_buffer, # depth
                self.dimensions[2]                    # height
            )
            safe_zone.temperature_safe = True
            self.spaces.append(safe_zone)
            print(f"🌡️ Created temperature-safe zone: {wall_buffer:.2f}m from all walls")
            print(f"   Safe zone dimensions: {safe_zone.x:.2f}, {safe_zone.y:.2f}, {safe_zone.z:.2f}, {safe_zone.width:.2f}, {safe_zone.depth:.2f}, {safe_zone.height:.2f}")
        
        # Pack each item with improved wall constraints
        for item in sorted_items:
            # If this is a temperature-sensitive item, print comprehensive debug info
            if getattr(item, 'needs_insulation', False):
                print(f"\n🌡️ Attempting to place temperature-sensitive item: {item.name}")
                print(f"   Dimensions: {item.dimensions[0]:.2f} × {item.dimensions[1]:.2f} × {item.dimensions[2]:.2f}m")
                print(f"   Temperature range: {item.temperature_sensitivity}")
                print(f"   Temperature constraint: Must be > {wall_buffer:.2f}m from all walls")
            
            # Try to pack at the bottom layer first
            if not self._try_pack_in_layer(item, 0):
                # Try on existing layers
                packed = False
                for height in sorted(set(i.position[2] + i.dimensions[2] 
                                  for i in self.items if i.position)):
                    if self._try_pack_in_layer(item, height):
                        packed = True
                        break
                        
                if not packed:
                    base_name = item.name.rsplit('_', 1)[0] if '_' in item.name else item.name
                    # Get detailed reason why packing failed
                    reason = self._get_unpacking_reason(item)
                    if getattr(item, 'needs_insulation', False):
                        reason = f"Temperature-sensitive item could not be placed with proper wall clearance: {reason}"
                    
                    self.unpacked_reasons[item.name] = (reason, item)
                    
                    if getattr(item, 'needs_insulation', False):
                        print(f"❌ Failed to place temperature-sensitive item {item.name}: {reason}")

        # Calculate volume utilization and total weight
        self._update_metrics()

    def _try_pack_in_layer(self, item: Item, height: float) -> bool:
        """Enhanced packing with better error handling and strict temperature control"""
        try:
            # Validate input parameters
            if not isinstance(item, Item):
                raise ValueError("Invalid item type")
            if not isinstance(height, (int, float)):
                raise ValueError("Invalid height value")
            if height < 0 or height > self.dimensions[2]:
                return False  # Height out of bounds

            # 🔒 TEMPERATURE CONSTRAINT ENFORCEMENT - PHASE 1 (PRE-ROTATION)
            # If this is a temperature-sensitive item, we need special handling from the very beginning
            needs_temperature_protection = False
            if (hasattr(self, 'route_temperature') and 
                self.route_temperature is not None and 
                hasattr(item, 'temperature_sensitivity') and 
                item.temperature_sensitivity and 
                getattr(item, 'needs_insulation', False)):
                needs_temperature_protection = True
                # Log that we have a temperature-sensitive item
                print(f"📏 Temperature-sensitive item detected: {item.name}")
                print(f"   Temperature range: {item.temperature_sensitivity}")
                print(f"   Route temperature: {self.route_temperature}°C")

            # Get valid rotations with dimension checking
            rotations = [rot for rot in self._get_valid_rotations(item)
                        if all(d <= max_d for d, max_d in zip(rot, self.dimensions))]
            
            if not rotations:
                return False  # No valid rotation found

            best_pos = None
            best_rot = None
            best_score = float('-inf')
            best_space = None
            
            # For each rotation, try to find best position
            for rotation in rotations:
                # Skip if height + item height exceeds container height
                if height + rotation[2] > self.dimensions[2]:
                    continue

                # Find valid positions in current layer
                for space in self.spaces:
                    # Skip spaces that aren't temperature-safe for temperature-sensitive items
                    if needs_temperature_protection and hasattr(space, 'temperature_safe') and space.temperature_safe is False:
                        continue

                    if not space.can_fit_item(rotation):
                        continue
                        
                    # Only consider spaces at the correct height
                    if abs(space.z - height) > 0.001:
                        continue
                        
                    pos = (space.x, space.y, height)
                    
                    # 🔒 TEMPERATURE CONSTRAINT ENFORCEMENT - PHASE 2 (EARLY WALL CHECK)
                    # Before even checking valid placement, reject wall positions for temperature-sensitive items
                    if needs_temperature_protection:
                        # Check for wall proximity
                        wall_buffer = 0.3  # 30cm buffer from walls - FIXED: Consistent with other parts of the code
                        x, y, z = pos
                        w, d, h = rotation
                        
                        # Calculate distance from each wall
                        left_wall_dist = x
                        front_wall_dist = y
                        right_wall_dist = self.dimensions[0] - (x + w)
                        back_wall_dist = self.dimensions[1] - (y + d)
                        top_wall_dist = self.dimensions[2] - (z + h)
                        
                        # If too close to any wall, immediately reject this position
                        if (left_wall_dist < wall_buffer or 
                            front_wall_dist < wall_buffer or 
                            right_wall_dist < wall_buffer or 
                            back_wall_dist < wall_buffer or 
                            top_wall_dist < wall_buffer):
                            # Skip this position entirely for temperature-sensitive items
                            continue
                    
                    if self._is_valid_placement(item, pos, rotation):
                        # 🔒 TEMPERATURE CONSTRAINT ENFORCEMENT - PHASE 3 (DETAILED CHECK)
                        # Additional temperature constraint checks
                        if hasattr(self, 'route_temperature') and self.route_temperature is not None:
                            if not self._check_temperature_constraints(item, pos, self.route_temperature):
                                continue  # Failed temperature constraints
                        
                        # Calculate position score
                        score = self._evaluate_position_enhanced(item, pos, rotation)
                        
                        # Update best position if this one has a better score
                        if score > best_score:
                            best_score = score
                            best_pos = pos
                            best_rot = rotation
                            best_space = space
        
            if best_pos and best_rot and best_space:
                # 🔒 TEMPERATURE CONSTRAINT ENFORCEMENT - PHASE 4 (FINAL VERIFICATION)
                # One final verification for temperature-sensitive items before placement
                if needs_temperature_protection:
                    x, y, z = best_pos
                    w, d, h = best_rot
                    
                    # Calculate distance from each wall one more time
                    wall_buffer = 0.3  # 30cm buffer from walls - FIXED: Consistent value across all checks
                    left_wall_dist = x
                    front_wall_dist = y
                    right_wall_dist = self.dimensions[0] - (x + w)
                    back_wall_dist = self.dimensions[1] - (y + d)
                    top_wall_dist = self.dimensions[2] - (z + h)
                    
                    # If too close to any wall, reject this position
                    if (left_wall_dist < wall_buffer or 
                        front_wall_dist < wall_buffer or 
                        right_wall_dist < wall_buffer or 
                        back_wall_dist < wall_buffer or 
                        top_wall_dist < wall_buffer):
                        print(f"⚠️ CRITICAL SAFETY CHECK: Prevented temperature-sensitive item {item.name} from being placed at {best_pos}")
                        print(f"   This is a final safeguard that should never trigger if earlier checks are working")
                        return False  # Reject placement
                    
                    # Log successful placement with distance information
                    print(f"✅ Placing temperature-sensitive item {item.name} at position {best_pos}")
                    print(f"   Distances from walls: L:{left_wall_dist:.2f}m, F:{front_wall_dist:.2f}m, R:{right_wall_dist:.2f}m, B:{back_wall_dist:.2f}m, T:{top_wall_dist:.2f}m")
                
                # Everything checks out, place the item
                item.position = best_pos
                item.dimensions = best_rot
                self.items.append(item)
                self._update_spaces(best_pos, best_rot, best_space)
                self._update_weight_distribution(item)
                return True
            
            return False

        except Exception as e:
            print(f"Error packing item {item.name}: {str(e)}")
            return False

    def _evaluate_position_enhanced(self, item, pos, dims):
        """Enhanced position evaluation with weighted constraints"""
        # Base scores for each constraint category
        constraint_scores = {
            'volume_utilization': 0,
            'stability_score': 0,
            'contact_ratio': 0,
            'weight_balance': 0,
            'temperature_constraint': 0,
            'items_packed_ratio': 100  # Default high score for packing this item
        }
        
        x, y, z = pos
        w, d, h = dims
        
        # --- STABILITY SCORE ---
        support_score = self._calculate_support_score(item, pos, dims)
        constraint_scores['stability_score'] = support_score * 100  # Normalize to 0-100
        
        # --- VOLUME UTILIZATION ---
        # Prefer positions that minimize empty space
        # Check how well the item fits in its surrounding space
        item_volume = w * d * h
        container_volume = self.dimensions[0] * self.dimensions[1] * self.dimensions[2]
        
        # Find nearest items in all 6 directions
        nearest_distances = self._find_nearest_distances(pos, dims)
        wasted_space = sum(nearest_distances)
        
        # Lower wasted space means better volume utilization
        space_efficiency = 1.0 - min(1.0, wasted_space / (container_volume ** (1/3)))
        constraint_scores['volume_utilization'] = space_efficiency * 100
        
        # --- TEMPERATURE CONSTRAINTS ---
        if getattr(item, 'needs_insulation', False):
            # Calculate distance from walls (minimum of all 6 directions)
            wall_buffer = 0.3  # 30cm buffer
            wall_distances = [
                x,                              # Left wall
                y,                              # Front wall
                self.dimensions[0] - (x + w),   # Right wall
                self.dimensions[1] - (y + d),   # Back wall
                z,                              # Bottom
                self.dimensions[2] - (z + h)    # Top
            ]
            min_wall_distance = min(wall_distances)
            
            # Calculate temperature constraint score based on wall distance
            if min_wall_distance < wall_buffer:
                wall_distance_score = (min_wall_distance / wall_buffer) * 50  # 0-50 range
            else:
                wall_distance_score = 50 + min(50, (min_wall_distance - wall_buffer) * 50)  # 50-100 range
            
            # Count surrounding items for insulation
            surrounding_items = 0
            insulating_items = 0
            for placed_item in self.items:
                if self._has_surface_contact(pos, dims, placed_item):
                    surrounding_items += 1
                    if not getattr(placed_item, 'needs_insulation', False):
                        insulating_items += 1
            
            # Calculate insulation score
            insulation_score = min(100, (surrounding_items * 10) + (insulating_items * 20))
            
            # Combine wall distance and insulation scores
            constraint_scores['temperature_constraint'] = (wall_distance_score * 0.7) + (insulation_score * 0.3)
        
        # --- CONTACT RATIO ---
        contact_count = 0
        contact_area = 0
        total_surface_area = 2 * (w*d + w*h + d*h)
        
        for placed_item in self.items:
            if self._has_surface_contact(pos, dims, placed_item):
                contact_count += 1
                contact_area += self._calculate_contact_area(pos, dims, placed_item)
        
        contact_ratio = min(1.0, contact_area / total_surface_area)
        constraint_scores['contact_ratio'] = contact_ratio * 100
        
        # --- WEIGHT BALANCE ---
        # Calculate center of gravity impact
        current_cog = self._calculate_current_cog()
        new_cog = self._calculate_cog_with_new_item(item, pos)
        
        # Distance from ideal center
        ideal_cog = (self.dimensions[0]/2, self.dimensions[1]/2, self.dimensions[2]/4)
        current_distance = self._calculate_distance(current_cog, ideal_cog)
        new_distance = self._calculate_distance(new_cog, ideal_cog)
        
        # Better balance = lower distance to ideal center
        if current_distance > 0:
            balance_improvement = max(-100, min(100, (current_distance - new_distance) * 100 / current_distance))
        else:
            balance_improvement = 0
        
        constraint_scores['weight_balance'] = 50 + balance_improvement/2  # Center at 50, range 0-100
    
        # --- APPLY WEIGHTS ---
        weighted_score = 0
        for constraint, score in constraint_scores.items():
            weight_key = f"{constraint}_weight"
            if hasattr(self, 'constraint_weights') and weight_key in self.constraint_weights:
                weighted_score += score * self.constraint_weights[weight_key]
            else:
                # Default weights if not provided
                default_weights = {
                    'volume_utilization_weight': 0.75,
                    'stability_score_weight': 0.50,
                    'contact_ratio_weight': 0.50,
                    'weight_balance_weight': 0.25,
                    'items_packed_ratio_weight': 0.25,
                    'temperature_constraint_weight': 0.30
                }
                weighted_score += score * default_weights.get(weight_key, 0.1)
        
        return weighted_score

    def _calculate_support_score(self, item, pos, dims):
        """Calculate support score with reduced constraints"""
        x, y, z = pos
        w, d, h = dims
        
        if z == 0:  # On the ground
            return 1.0
            
        support_area = 0
        total_area = w * d
        items_below = self._get_items_below(pos, (w, d))
        
        for below_item in items_below:
            overlap = self._calculate_overlap_area(
                (x, y, w, d),
                (below_item.position[0], below_item.position[1],
                 below_item.dimensions[0], below_item.dimensions[1])
            )
            # Relaxed load bearing requirement
            stackable_support = below_item.stackable
            if stackable_support:
                support_area += overlap
        
        # If support area is insufficient, add support mechanisms
        support_ratio = support_area / total_area
        if support_ratio < 0.3:  # Reduced from 0.5
            if self._can_add_support(pos, dims):
                self._add_support_mechanism(pos, dims)
                return 0.8  # Good score with support mechanism
        
        return max(0.3, support_ratio)  # Accept lower support ratios

    def _can_add_support(self, pos, dims):
        """Check if we can add support mechanisms"""
        # Check if there's space for supports
        x, y, z = pos
        w, d, h = dims
        
        # Simple space check for now
        return z < (self.dimensions[2] * 0.8)  # Allow support if not too high

    def _add_support_mechanism(self, pos, dims):
        """Add support mechanisms to stabilize items"""
        x, y, z = pos
        w, d, h = dims
        self.support_mechanisms.append({
            'position': (x, y, z),
            'dimensions': (w, d, h),
            'type': 'block'  # Example support mechanism type
        })
    
    def _get_unpacking_reason(self, item) -> str:
        """Get detailed reason why item couldn't be packed"""
        # Check if it's a temperature sensitive item first
        if getattr(item, 'needs_insulation', False):
            # For temperature sensitive items, check if there's any space away from walls
            wall_buffer = 0.3  # 30cm buffer - FIXED: Consistent with other parts of the code
            available_width = self.dimensions[0] - (2 * wall_buffer)
            available_depth = self.dimensions[1] - (2 * wall_buffer)
            available_height = self.dimensions[2] - wall_buffer  # Buffer from top only
            
            if item.dimensions[0] > available_width or \
               item.dimensions[1] > available_depth or \
               item.dimensions[2] > available_height:
                return (f"Temperature-sensitive item is too large to be placed with buffer zone from walls. "
                       f"Available space with buffer: {available_width:.2f}×{available_depth:.2f}×{available_height:.2f}m, "
                       f"Item size: {item.dimensions[0]:.2f}×{item.dimensions[1]:.2f}×{item.dimensions[2]:.2f}m")
            
            return ("Temperature-sensitive item could not be placed away from container walls. "
                   "These items must maintain a 30cm buffer from all walls and top of container.")

        # Rest of the function remains unchanged for non-temperature sensitive items
        # Check dimensions
        if item.dimensions[0] > self.dimensions[0] or \
           item.dimensions[1] > self.dimensions[1] or \
           item.dimensions[2] > self.dimensions[2]:
            return (f"Item dimensions ({item.dimensions[0]:.2f}×{item.dimensions[1]:.2f}×{item.dimensions[2]:.2f}m) "
                    f"exceed container dimensions ({self.dimensions[0]:.2f}×{self.dimensions[1]:.2f}×{self.dimensions[2]:.2f}m)")
        
        # Check volume availability
        item_volume = item.dimensions[0] * item.dimensions[1] * item.dimensions[2]
        if self.remaining_volume < item_volume:
            return f"Insufficient container volume: Item needs {item_volume:.2f}m³, only {self.remaining_volume:.2f}m³ available"
        
        # Check stability and support
        test_positions = []
        central_positions_tried = False
        
        for space in self.spaces:
            if space.can_fit_item(item.dimensions):
                pos = (space.x, space.y, space.z)
                
                # Calculate position relative to center
                center_x = self.dimensions[0] / 2
                center_y = self.dimensions[1] / 2
                item_center_x = pos[0] + item.dimensions[0]/2
                item_center_y = pos[1] + item.dimensions[1]/2
                
                # Check if position is in central third
                is_central = (
                    center_x - self.dimensions[0]/6 <= item_center_x <= center_x + self.dimensions[0]/6 and
                    center_y - self.dimensions[1]/6 <= item_center_y <= center_y + self.dimensions[1]/6
                )
                
                if is_central:
                    central_positions_tried = True
                
                # Check support score
                support_score = self._calculate_support_score(item, pos, item.dimensions)
                if support_score < 0.3:
                    test_positions.append({
                        'pos': pos,
                        'support_score': support_score,
                        'reason': f"Insufficient base support (support score: {support_score:.2f})"
                    })
                    continue
                
                # Check stackability
                items_below = self._get_items_below(pos, item.dimensions[:2])
                for below_item in items_below:
                    if below_item.fragility == 'HIGH':
                        test_positions.append({
                            'pos': pos,
                            'reason': f"Cannot stack on high fragility item ({below_item.name})"
                        })
                        continue
                    
                    if below_item.load_bearing > 0:
                        overlap_area = self._calculate_overlap_area(
                            (pos[0], pos[1], item.dimensions[0], item.dimensions[1]),
                            (below_item.position[0], below_item.position[1],
                             below_item.dimensions[0], below_item.dimensions[1])
                        )
                        total_area = below_item.dimensions[0] * below_item.dimensions[1]
                        weight_ratio = overlap_area / total_area
                        
                        if item.weight > below_item.load_bearing * weight_ratio:
                            test_positions.append({
                                'pos': pos,
                                'reason': f"Weight ({item.weight}kg) exceeds support capacity of {below_item.name} ({below_item.load_bearing * weight_ratio:.1f}kg)"
                            })
                            continue
                
                # Temperature constraints
                if hasattr(self, 'route_temperature') and self.route_temperature is not None:
                    if hasattr(item, 'temperature_sensitivity') and item.temperature_sensitivity:
                        try:
                            if 'n/a' not in item.temperature_sensitivity.lower():
                                temp_range = item.temperature_sensitivity.replace('°C', '').split(' to ')
                                min_temp = float(temp_range[0])
                                max_temp = float(temp_range[1])
                                if self.route_temperature < min_temp or self.route_temperature > max_temp:
                                    # Check wall contacts and surrounding insulation
                                    wall_contacts = 0
                                    if pos[0] == 0 or pos[0] + item.dimensions[0] == self.dimensions[0]: 
                                        wall_contacts += 1
                                    if pos[1] == 0 or pos[1] + item.dimensions[1] == self.dimensions[1]: 
                                        wall_contacts += 1
                                    
                                    # Count surrounding items for insulation
                                    surrounding_items = 0
                                    insulating_items = 0
                                    for placed_item in self.items:
                                        if self._has_surface_contact(pos, item.dimensions, placed_item):
                                            surrounding_items += 1
                                            if not getattr(placed_item, 'needs_insulation', False):
                                                insulating_items += 1
                                    
                                    if wall_contacts > 0:
                                        if surrounding_items < 2 or insulating_items < 1:
                                            msg = (f"Temperature-sensitive item ({min_temp}°C to {max_temp}°C) needs better wall insulation. "
                                                   f"Found: {surrounding_items} surrounding, {insulating_items} insulating items. "
                                                   f"When against walls, needs at least 2 surrounding items with 1 insulating.")
                                            test_positions.append({
                                                'pos': pos,
                                                'reason': msg,
                                                'is_central': is_central
                                            })
                                            continue
                                    elif not is_central and surrounding_items < 1:
                                        msg = (f"Temperature-sensitive item ({min_temp}°C to {max_temp}°C) must be either:\n"
                                               f"1. In central third of container (current position is not central), or\n"
                                               f"2. Have surrounding items for insulation (currently has {surrounding_items} surrounding items), or\n"
                                               f"3. Against walls with proper insulation")
                                        test_positions.append({
                                            'pos': pos,
                                            'reason': msg,
                                            'is_central': is_central
                                        })
                                        continue
                        except (ValueError, IndexError):
                            pass

        if test_positions:
            # Try to give most helpful reason based on context
            has_central_failure = any(pos.get('is_central', False) for pos in test_positions)
            temperature_positions = [pos for pos in test_positions if 'Temperature-sensitive' in pos['reason']]
            
            if temperature_positions:
                if not central_positions_tried:
                    return ("No central positions available for temperature-sensitive item. "
                           "Tried wall positions but couldn't find adequate insulation.")
                elif has_central_failure:
                    central_reason = next(pos['reason'] for pos in temperature_positions if pos.get('is_central', False))
                    return f"Central position attempted but failed: {central_reason}"
                else:
                    return next(pos['reason'] for pos in temperature_positions)
            elif any('support capacity' in pos['reason'] for pos in test_positions):
                return next(pos['reason'] for pos in test_positions if 'support capacity' in pos['reason'])
            elif any('high fragility' in pos['reason'] for pos in test_positions):
                return next(pos['reason'] for pos in test_positions if 'high fragility' in pos['reason'])
            else:
                return next(pos['reason'] for pos in test_positions if 'support score' in pos['reason'])
        
        # Check available spaces
        max_space = max(self.unused_spaces, key=lambda s: s[3] * s[4] * s[5], default=None)
        if max_space:
            item_vol = item.dimensions[0] * item.dimensions[1] * item.dimensions[2]
            space_vol = max_space[3] * max_space[4] * max_space[5]
            return (f"No suitable space found - Largest available space: "
                   f"{max_space[3]:.2f}×{max_space[4]:.2f}×{max_space[5]:.2f}m "
                   f"({space_vol:.2f}m³), Item needs: "
                   f"{item.dimensions[0]:.2f}×{item.dimensions[1]:.2f}×{item.dimensions[2]:.2f}m "
                   f"({item_vol:.2f}m³)")
        
        return "No suitable position found - Complex constraint violation involving stability, support, and space requirements"

    def _check_temperature_constraints(self, item, pos, route_temperature):
        """
        Comprehensive temperature constraint check for all six container sides
        
        This function enforces temperature constraints for items that need temperature protection,
        ensuring they are kept away from all container walls (left, right, front, back, top, bottom)
        """
        # Fast path: return True if item is not temperature sensitive
        if not hasattr(item, 'temperature_sensitivity'):
            return True
        
        if not item.temperature_sensitivity or item.temperature_sensitivity.lower() == 'n/a':
            return True
        
        # Mark items as needing insulation if route temperature is outside their range
        try:
            temp_range = item.temperature_sensitivity.replace('°C', '').split(' to ')
            min_temp = float(temp_range[0])
            max_temp = float(temp_range[1])
            
            # Check if route temperature exceeds item's temperature range
            if route_temperature < min_temp or route_temperature > max_temp:
                # Item needs temperature protection
                item.needs_insulation = True
                
                # Enforce buffer from ALL walls for temperature-sensitive items
                wall_buffer = 0.3  # 30cm buffer from walls for safety - FIXED: Consistent with other parts of the code
                
                # Get position and dimensions
                x, y, z = pos
                w, d, h = item.dimensions
                
                # Calculate minimum distances to each of the six container walls
                distances = [
                    x,                              # Distance from left wall
                    y,                              # Distance from front wall
                    self.dimensions[0] - (x + w),   # Distance from right wall
                    self.dimensions[1] - (y + d),   # Distance from back wall
                    z,                              # Distance from bottom
                    self.dimensions[2] - (z + h)    # Distance from top
                ]
                
                # Find the minimum distance to any wall
                min_distance = min(distances)
                
                # If too close to any wall, reject the placement
                if min_distance < wall_buffer:
                    print(f"❌ TEMPERATURE CONSTRAINT: Rejected {item.name} at {pos}")
                    print(f"   Too close to walls: min distance = {min_distance:.2f}m, required = {wall_buffer:.2f}m")
                    print(f"   Left: {distances[0]:.2f}m, Front: {distances[1]:.2f}m, Right: {distances[2]:.2f}m")
                    print(f"   Back: {distances[3]:.2f}m, Bottom: {distances[4]:.2f}m, Top: {distances[5]:.2f}m")
                    return False
                
                # Look for surrounding items for thermal insulation
                surrounding_items = self._count_surrounding_items(item, pos)
                
                # For items placed in the center (away from walls), we still want some insulation
                min_required_items = 2  # Increased from 1 to 2 - require more surrounding items for insulation
                
                # Check if there are enough surrounding items to provide insulation
                if surrounding_items >= min_required_items:
                    print(f"✅ TEMPERATURE CONSTRAINT: Accepted {item.name} at {pos}")
                    print(f"   Min wall distance: {min_distance:.2f}m")
                    print(f"   Surrounding items: {surrounding_items}")
                    return True
                else:
                    print(f"❌ TEMPERATURE CONSTRAINT: Rejected {item.name} at {pos}")
                    print(f"   Not enough surrounding items for insulation: {surrounding_items}, needed {min_required_items}")
                    print(f"   Min wall distance: {min_distance:.2f}m, requires more surrounding items or central placement")
                    return False
            else:
                # Temperature-sensitive but not affected by route temperature
                # Reset needs_insulation flag if it was set previously
                item.needs_insulation = False
        
            return True
        
        except (ValueError, IndexError, AttributeError) as e:
            print(f"Warning: Temperature constraint error for {item.name}: {e}")
            # If there's any error, reject the position to be safe
            return False

    def _count_surrounding_items(self, item, pos):
        """Count items surrounding the given item for insulation purposes"""
        x, y, z = pos
        w, d, h = item.dimensions
        surrounding_count = 0
        
        # Define detection range - slightly larger than the item
        detection_buffer = 0.05  # 5cm detection buffer
        min_x = x - detection_buffer
        max_x = x + w + detection_buffer
        min_y = y - detection_buffer
        max_y = y + d + detection_buffer
        min_z = z - detection_buffer
        max_z = z + h + detection_buffer
        
        for placed_item in self.items:
            # Skip comparing with itself
            if placed_item.position is None or (placed_item.position == pos and placed_item.dimensions == item.dimensions):
                continue
            
            px, py, pz = placed_item.position
            pw, pd, ph = placed_item.dimensions
            
            # Check if the placed item is adjacent to or overlapping with our item
            if (px + pw >= min_x and px <= max_x and
                py + pd >= min_y and py <= max_y and
                pz + ph >= min_z and pz <= max_z):
                surrounding_count += 1
            
        return surrounding_count

    def _get_items_below(self, pos, dims_2d):
        """
        Get all items that are below the given position.
        
        Args:
            pos: Tuple (x, y, z) position to check
            dims_2d: Tuple (width, depth) dimensions in the horizontal plane
            
        Returns:
            List of items that are directly below the position
        """
        x, y, z = pos
        w, d = dims_2d
        
        # If on the ground, there are no items below
        if z <= 0.001:
            return []
            
        items_below = []
        
        for item in self.items:
            # Skip items that are not below
            if item.position is None or item.position[2] + item.dimensions[2] > z:
                continue
            
            # Check horizontal overlap using the utility function
            has_overlap = check_overlap_2d(
                (x, y, w, d),
                (item.position[0], item.position[1], item.dimensions[0], item.dimensions[1])
            )
            
            # Check if the item is directly below (no gap)
            is_directly_below = abs(item.position[2] + item.dimensions[2] - z) < 0.001
            
            if has_overlap and is_directly_below:
                items_below.append(item)
                
        return items_below

    def _update_metrics(self):
        """Update volume utilization and weight metrics"""
        if not self.items:
            self.volume_utilization = 0.0
            self.total_weight = 0.0
            self.remaining_volume = self.dimensions[0] * self.dimensions[1] * self.dimensions[2]
            return
            
        # Calculate metrics
        container_volume = self.dimensions[0] * self.dimensions[1] * self.dimensions[2]
        used_volume = sum(item.dimensions[0] * item.dimensions[1] * item.dimensions[2] 
                          for item in self.items if item.position)
                          
        self.volume_utilization = used_volume / container_volume if container_volume > 0 else 0
        self.remaining_volume = container_volume - used_volume
        
        # Calculate total weight and validate against container max payload
        self.total_weight = sum(item.weight for item in self.items if item.position)
        
        # Check if we have container type information for weight validation
        if hasattr(self, 'container_type') and self.container_type:
            from optigenix_module.constants import CONTAINER_TYPES
            if self.container_type in CONTAINER_TYPES:
                max_payload = CONTAINER_TYPES[self.container_type][3]  # Get max payload from constants
                if self.total_weight > max_payload:
                    print(f"⚠️ WARNING: Total weight ({self.total_weight:.1f} kg) exceeds container maximum payload ({max_payload} kg)")
                    self.weight_exceeded = True
                    # Could mark some items as unpacked to stay within weight limits
                else:
                    self.weight_exceeded = False
                    print(f"✅ Weight check passed: {self.total_weight:.1f} kg / {max_payload} kg")
    
    def _find_nearest_distances(self, pos, dims):
        """Find the nearest items or walls in all 6 directions"""
        x, y, z = pos
        w, d, h = dims
        
        # Initialize with distances to walls
        nearest_distances = [
            x,                              # Distance to left wall
            y,                              # Distance to front wall
            self.dimensions[0] - (x + w),   # Distance to right wall
            self.dimensions[1] - (y + d),   # Distance to back wall
            z,                              # Distance to bottom
            self.dimensions[2] - (z + h)    # Distance to top
        ]
        
        # Check all items for closer distances
        for item in self.items:
            if item.position is None:
                continue
                
            ix, iy, iz = item.position
            iw, id, ih = item.dimensions
            
            # Left distance (-X direction)
            if iy < y + d and iy + id > y and iz < z + h and iz + ih > z and ix + iw <= x:
                nearest_distances[0] = min(nearest_distances[0], x - (ix + iw))
                
            # Front distance (-Y direction)
            if ix < x + w and ix + iw > x and iz < z + h and iz + ih > z and iy + id <= y:
                nearest_distances[1] = min(nearest_distances[1], y - (iy + id))
                
            # Right distance (+X direction)
            if iy < y + d and iy + id > y and iz < z + h and iz + ih > z and ix >= x + w:
                nearest_distances[2] = min(nearest_distances[2], ix - (x + w))
                
            # Back distance (+Y direction)
            if ix < x + w and ix + iw > x and iz < z + h and iz + ih > z and iy >= y + d:
                nearest_distances[3] = min(nearest_distances[3], iy - (y + d))
                
            # Bottom distance (-Z direction)
            if ix < x + w and ix + iw > x and iy < y + d and iy + id > y and iz + ih <= z:
                nearest_distances[4] = min(nearest_distances[4], z - (iz + ih))
                
            # Top distance (+Z direction)
            if ix < x + w and ix + iw > x and iy < y + d and iy + id > y and iz >= z + h:
                nearest_distances[5] = min(nearest_distances[5], iz - (z + h))
                
        return nearest_distances

    def _calculate_contact_area(self, pos, dims, other_item):
        """Calculate contact area between two items"""
        if other_item.position is None:
            return 0
            
        x1, y1, z1 = pos
        w1, d1, h1 = dims
        x2, y2, z2 = other_item.position
        w2, d2, h2 = other_item.dimensions
        
        contact_area = 0
        
        # Check X-face contact
        if abs(x1 - (x2 + w2)) < 0.001 or abs(x2 - (x1 + w1)) < 0.001:
            # Items are adjacent in X direction
            # Calculate overlap area in YZ plane
            y_overlap = max(0, min(y1 + d1, y2 + d2) - max(y1, y2))
            z_overlap = max(0, min(z1 + h1, z2 + h2) - max(z1, z2))
            contact_area += y_overlap * z_overlap
        
        # Check Y-face contact
        if abs(y1 - (y2 + d2)) < 0.001 or abs(y2 - (y1 + d1)) < 0.001:
            # Items are adjacent in Y direction
            # Calculate overlap area in XZ plane
            x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
            z_overlap = max(0, min(z1 + h1, z2 + h2) - max(z1, z2))
            contact_area += x_overlap * z_overlap
        
        # Check Z-face contact
        if abs(z1 - (z2 + h2)) < 0.001 or abs(z2 - (z1 + h1)) < 0.001:
            # Items are adjacent in Z direction
            # Calculate overlap area in XY plane
            x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
            y_overlap = max(0, min(y1 + d1, y2 + d2) - max(y1, y2))
            contact_area += x_overlap * y_overlap
        
        return contact_area

    def _calculate_current_cog(self):
        """Calculate current center of gravity of packed items"""
        total_weight = 0
        weighted_x = 0
        weighted_y = 0
        weighted_z = 0
        
        for item in self.items:
            if item.position is None:
                continue
                
            x, y, z = item.position
            w, d, h = item.dimensions
            
            # Calculate item's center position
            center_x = x + w/2
            center_y = y + d/2
            center_z = z + h/2
            
            weighted_x += center_x * item.weight
            weighted_y += center_y * item.weight
            weighted_z += center_z * item.weight
            total_weight += item.weight
        
        if total_weight == 0:
            # If no items yet, return container center
            return (self.dimensions[0]/2, self.dimensions[1]/2, self.dimensions[2]/2)
        
        return (weighted_x/total_weight, weighted_y/total_weight, weighted_z/total_weight)

    def _calculate_cog_with_new_item(self, item, pos):
        """Calculate what the CoG would be with a new item added"""
        x, y, z = pos
        w, d, h = item.dimensions
        
        # Calculate total weight and weighted position sums with existing items
        total_weight = item.weight
        weighted_x = (x + w/2) * item.weight
        weighted_y = (y + d/2) * item.weight
        weighted_z = (z + h/2) * item.weight
        
        for packed_item in self.items:
            if packed_item.position is None:
                continue
                
            ix, iy, iz = packed_item.position
            iw, id, ih = packed_item.dimensions
            
            weighted_x += (ix + iw/2) * packed_item.weight
            weighted_y += (iy + id/2) * packed_item.weight
            weighted_z += (iz + ih/2) * packed_item.weight
            total_weight += packed_item.weight
        
        if total_weight == 0:
            return (self.dimensions[0]/2, self.dimensions[1]/2, self.dimensions[2]/2)
        
        return (weighted_x/total_weight, weighted_y/total_weight, weighted_z/total_weight)

    def _calculate_distance(self, point1, point2):
        """Calculate distance between two 3D points"""
        return ((point1[0] - point2[0])**2 + 
                (point1[1] - point2[1])**2 + 
                (point1[2] - point2[2])**2) ** 0.5