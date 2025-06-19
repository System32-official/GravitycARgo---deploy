"""
Genetic algorithm implementation for container packing optimization.
"""
import random
import time
import json
import logging
import multiprocessing
from copy import deepcopy
from typing import List, Dict, Tuple, Any, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
from array import array
import numpy as np

from optigenix_module.models.container import EnhancedContainer
from optigenix_module.models.item import Item
from optigenix_module.utils.llm_connector import get_llm_client
from optigenix_module.optimization.temperature import TemperatureConstraintHandler
from optigenix_module.optimization.max_utilization_fitness import apply_max_volume_fitness, detect_demo_dataset

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("packer")

# Conditional logging for the module loaded message
if multiprocessing.current_process().name == 'MainProcess':
    logger.info("=" * 70)
    logger.info("AI-ENHANCED GENETIC PACKER MODULE LOADED")
    logger.info("=" * 70)

# Initialize LLM client
llm_client = get_llm_client()

class PackingGenome:
    """
    Genome class for genetic algorithm-based packing optimization
    
    Represents a potential solution to the packing problem with a specific
    item sequence and rotation configuration.
    """
    
    def __init__(self, items, mutation_rate=0.1):
        """Initialize genome with items and mutation rate"""
        self.items = items  # Store the original items list
        self.item_sequence = items.copy()
        # Use array for rotation flags instead of list for better memory usage
        self.rotation_flags = array('B', [random.randint(0, 5) for _ in items])
        self.mutation_rate = mutation_rate
        self.fitness = 0.0

    def mutate(self, operation_focus=None, rate_modifier=0):
        """
        Apply mutation operators to modify the genome
        
        Args:
            operation_focus: Focus specific mutation operations ("rotation", "swap", "subsequence", "balanced", or "aggressive")
            rate_modifier: Adjustment to mutation rate (-0.05 to 0.2)
        """
        # Apply rate modifier while ensuring rate remains in valid range
        effective_rate = max(0.01, min(0.5, self.mutation_rate + rate_modifier))
        
        # Define operation probabilities based on focus
        if operation_focus == "rotation":
            rotation_prob = 1.0
            swap_prob = 0.3
            subsequence_prob = 0.2
            aggressive_prob = 0.0
        elif operation_focus == "swap":
            rotation_prob = 0.3
            swap_prob = 1.0
            subsequence_prob = 0.3
            aggressive_prob = 0.0
        elif operation_focus == "subsequence":
            rotation_prob = 0.3
            swap_prob = 0.3
            subsequence_prob = 1.0
            aggressive_prob = 0.0
        elif operation_focus == "aggressive":
            # Aggressive strategy - high probability for all operations
            rotation_prob = 1.0
            swap_prob = 1.0
            subsequence_prob = 1.0
            aggressive_prob = 1.0  # Enable aggressive mutations
        else:  # balanced
            rotation_prob = 1.0
            swap_prob = 1.0
            subsequence_prob = 1.0
            aggressive_prob = 0.0
        
        # Rotation mutation
        for i in range(len(self.item_sequence)):
            if random.random() < effective_rate * rotation_prob:
                self.rotation_flags[i] = random.randint(0, 5)

        # Sequence mutation - swap items
        if random.random() < effective_rate * swap_prob * 2:
            if len(self.item_sequence) >= 2:
                idx1, idx2 = random.sample(range(len(self.item_sequence)), 2)
                self.item_sequence[idx1], self.item_sequence[idx2] = \
                    self.item_sequence[idx2], self.item_sequence[idx1]
            
        # Sequence mutation - shift subsequence
        if random.random() < effective_rate * subsequence_prob:
            if len(self.item_sequence) > 3:
                seq_length = random.randint(2, max(2, len(self.item_sequence) // 2))
                start_idx = random.randint(0, len(self.item_sequence) - seq_length - 1)
                target_idx = random.randint(0, len(self.item_sequence) - seq_length)
                
                # Extract subsequence
                subsequence = self.item_sequence[start_idx:start_idx+seq_length]
                rotation_subseq = list(self.rotation_flags[start_idx:start_idx+seq_length])
                
                # Remove subsequence
                self.item_sequence = self.item_sequence[:start_idx] + \
                                    self.item_sequence[start_idx+seq_length:]
                
                # Create new rotation flags array
                new_rotation_flags = (list(self.rotation_flags[:start_idx]) + 
                                    list(self.rotation_flags[start_idx+seq_length:]))
                
                # Insert at target location
                self.item_sequence = self.item_sequence[:target_idx] + \
                                    subsequence + \
                                    self.item_sequence[target_idx:]
                
                # Insert rotation subsequence and rebuild array
                final_rotations = (new_rotation_flags[:target_idx] + 
                                 rotation_subseq + 
                                 new_rotation_flags[target_idx:])
                self.rotation_flags = array('B', final_rotations)
        
        # Aggressive mutations - only applied when specified
        if aggressive_prob > 0 and random.random() < effective_rate * aggressive_prob:
            # Multiple aggressive mutations to escape local optima
            
            # 1. Large sequence reversal - reverse a significant chunk of the sequence
            if len(self.item_sequence) > 10:
                chunk_size = random.randint(len(self.item_sequence)//4, len(self.item_sequence)//2)
                start = random.randint(0, len(self.item_sequence) - chunk_size)
                
                # Reverse the subsequence
                self.item_sequence[start:start+chunk_size] = reversed(self.item_sequence[start:start+chunk_size])
                
                # Also randomize rotations in that subsequence
                for i in range(start, start + chunk_size):
                    self.rotation_flags[i] = random.randint(0, 5)
            
            # 2. Complete rotation randomization with high probability
            if random.random() < 0.7:  # 70% chance
                for i in range(len(self.rotation_flags)):
                    if random.random() < 0.5:  # Randomize about half of all rotations
                        self.rotation_flags[i] = random.randint(0, 5)
            
            # 3. Multiple swaps - perform several random swaps to significantly change the sequence
            swap_count = random.randint(3, max(3, len(self.item_sequence) // 5))
            for _ in range(swap_count):
                if len(self.item_sequence) >= 2:
                    idx1, idx2 = random.sample(range(len(self.item_sequence)), 2)
                    self.item_sequence[idx1], self.item_sequence[idx2] = \
                        self.item_sequence[idx2], self.item_sequence[idx1]

class GeneticPacker:
    """
    Genetic algorithm implementation for optimizing container packing
    
    Uses evolutionary algorithms to find efficient item arrangements.
    """
    
    def __init__(self, container_dims, population_size=10, generations=8, route_temperature=None):
        """Initialize genetic packer with container dimensions and algorithm parameters"""
        self.container_dims = container_dims
        self.population_size = population_size
        self.generations = generations
        self.best_solution = None
        self.mutation_rates = {
            'rotation': 0.2,    # Higher rate for rotation mutations
            'swap': 0.15,       # Moderate rate for swaps
            'subsequence': 0.1  # Lower rate for subsequence changes
        }
        self.elite_percentage = 0.15  # Preserve top 15% of solutions
        self.route_temperature = route_temperature
        self.items_to_pack = None  # Will be set in optimize method
        self.fitness_weights = None  # Will be set in optimize method
        
        # Initialize temperature constraint handler
        self.temp_handler = TemperatureConstraintHandler(route_temperature)

    def _calculate_initial_metrics(self) -> Dict[str, Any]:
        """
        Calculate initial metrics for the LLM to determine initial fitness weights.
        This method should be called after self.items_to_pack is set.
        """
        if not self.items_to_pack:
            logger.warning("_calculate_initial_metrics: self.items_to_pack is not set. Cannot calculate initial metrics.")
            return {
                'initial_volume_utilization_estimate': 0.0,
                'item_count': 0,
                'container_dimensions': [0,0,0],
                'container_weight_capacity': 0.0, # Added
                'has_temperature_sensitive_items': False
            }

        # Calculate total volume of all items
        total_item_volume = sum(item.dimensions[0] * item.dimensions[1] * item.dimensions[2] for item in self.items_to_pack if hasattr(item, 'dimensions') and len(item.dimensions) == 3)

        # Get container volume and weight capacity
        container_volume = 0
        container_weight_capacity = 0.0 # Default
        container_dims_for_prompt = [0,0,0]

        if isinstance(self.container_dims, dict): # For EnhancedContainer like structures
            container_actual_dims = self.container_dims.get('dimensions', [0,0,0])
            container_weight_capacity = float(self.container_dims.get('weight_capacity', 0.0))
            if len(container_actual_dims) == 3:
                container_volume = container_actual_dims[0] * container_actual_dims[1] * container_actual_dims[2]
                container_dims_for_prompt = container_actual_dims
        elif isinstance(self.container_dims, (list, tuple)) and len(self.container_dims) == 3: # For simple list/tuple dimensions
            container_volume = self.container_dims[0] * self.container_dims[1] * self.container_dims[2]
            container_dims_for_prompt = list(self.container_dims)
            # Weight capacity might not be available in this case, defaults to 0
        else:
            logger.warning(f"_calculate_initial_metrics: Invalid container_dims format: {self.container_dims}")


        initial_volume_utilization_estimate = (total_item_volume / container_volume) if container_volume > 0 else 0
        item_count = len(self.items_to_pack)
        has_temp_sensitive = any(getattr(item, 'temperature_sensitivity', None) is not None for item in self.items_to_pack)

        metrics = {
            'initial_volume_utilization_estimate': round(initial_volume_utilization_estimate, 4),
            'item_count': item_count,
            'container_dimensions': container_dims_for_prompt,
            'container_weight_capacity': container_weight_capacity, # Added
            'has_temperature_sensitive_items': has_temp_sensitive
        }
        logger.info(f"Calculated initial metrics: {metrics}")
        return metrics

    def _get_initial_dynamic_fitness_weights(self, initial_metrics=None):
        """
        Get initial dynamic fitness function weights from LLM.
        Uses module-level llm_client and logger.
        """
        global llm_client, logger # Access module-level instances

        if not llm_client or not hasattr(llm_client, 'get_llm_completion'):
            logger.info("LLM client not available for initial dynamic fitness weights.")
            return None

        if initial_metrics is None:
            initial_metrics = self._calculate_initial_metrics() # Ensure items_to_pack is set before calling this
        
        prompt = f"""
        Provide a set of fitness weights for a genetic algorithm optimizing 3D bin packing.
        Consider the following initial metrics:
        - Estimated volume utilization: {initial_metrics.get('initial_volume_utilization_estimate', 0.0)}
        - Item count: {initial_metrics.get('item_count', 0)}
        - Container dimensions: {initial_metrics.get('container_dimensions', [0,0,0])}

        The weights should guide the optimization towards better packing solutions.
        Return the weights in JSON format with the following keys:
        - volume_utilization_weight
        - stability_score_weight
        - contact_ratio_weight
        - weight_balance_weight
        - items_packed_ratio_weight
        - temperature_constraint_weight (consider if temperature-sensitive items might be present, default to 0 if unsure)
        - explanation (brief explanation for the chosen weights)

        Ensure the numeric weights sum up to 1.0.
        """
        
        try:
            response_text = llm_client.get_llm_completion(prompt)
            logger.info(f"LLM response for initial dynamic weights: {response_text}")
            
            if not response_text:
                logger.warning("LLM returned an empty response for initial dynamic weights.")
                return None

            # It's good practice to strip whitespace before parsing JSON
            weights_data = json.loads(response_text.strip()) 
            
            explanation = weights_data.pop("explanation", "No explanation provided by LLM for initial weights.")
            logger.info(f"LLM Explanation for initial weights: {explanation}")

            expected_weight_keys = [
                'volume_utilization_weight', 'stability_score_weight', 
                'contact_ratio_weight', 'weight_balance_weight', 
                'items_packed_ratio_weight', 'temperature_constraint_weight',
                'weight_capacity_weight' # Added
            ]
            
            parsed_weights = {}
            for key in expected_weight_keys:
                parsed_weights[key] = float(weights_data.get(key, 0.0)) # Default to 0.0 if key is missing
            
            total_weight = sum(parsed_weights.values())

            if abs(total_weight) < 1e-6: # Check if sum is effectively zero
                 logger.warning("Sum of initial weights from LLM is zero. Cannot normalize. Returning None.")
                 return None

            if abs(total_weight - 1.0) > 0.01: # Normalize if not already summing to 1.0
                logger.info(f"Normalizing LLM initial weights. Original sum: {total_weight}")
                for key in parsed_weights:
                    parsed_weights[key] /= total_weight # Normalize
            
            logger.info(f"Successfully obtained and processed initial dynamic fitness weights: {parsed_weights}")
            return parsed_weights
            
        except json.JSONDecodeError:
            logger.error("Error decoding JSON response from LLM for initial dynamic fitness weights.", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error getting initial dynamic fitness weights from LLM: {e}", exc_info=True)
            return None

    def _get_default_fitness_weights(self):
        """Returns a default set of fitness weights."""
        return {
            'volume_utilization_weight': 0.50, 
            'stability_score_weight': 0.10,
            'contact_ratio_weight': 0.10,
            'weight_balance_weight': 0.10,
            'items_packed_ratio_weight': 0.15, 
            'temperature_constraint_weight': 0.05,
            'weight_capacity_weight': 0.00 # Default to 0, can be adjusted by LLM
        }

    def _evaluate_fitness(self, genome):
        """
        Evaluate fitness of a genome considering fitness weights.
        
        Args:
            genome: PackingGenome to evaluate
            
        Returns:
            float: Fitness score of the genome
        """
        fitness = 0.0  # Initialize fitness to 0.0 at the beginning

        container = EnhancedContainer(self.container_dims)
        
        # Set route temperature if available
        if self.route_temperature is not None:
            container.route_temperature = self.route_temperature
        
        # Sort spaces by their distance from container origin for better packing
        def sort_spaces_local(current_container_instance): # Renamed to avoid conflict
            current_container_instance.spaces.sort(key=lambda space: (
                space.z,  # Prioritize lower heights first
                space.x**2 + space.y**2,  # Prefer spaces closer to origin
                -(space.width * space.height * space.depth)  # Prefer larger spaces
            ))
        
        # Make a local copy of items to avoid modifying the originals
        # Ensure items in genome.item_sequence are full Item objects
        items_to_pack_for_eval = []
        for item_in_seq, rotation_flag_val in zip(genome.item_sequence, genome.rotation_flags):
            if isinstance(item_in_seq, Item): # Make sure it's an Item object
                 # Create a copy of the item for modification during evaluation
                item_copy = Item(
                    name=item_in_seq.name,
                    length=item_in_seq.original_dims[0], # Use original_dims for copying
                    width=item_in_seq.original_dims[1],
                    height=item_in_seq.original_dims[2],
                    weight=item_in_seq.weight / item_in_seq.quantity if item_in_seq.bundle == 'YES' and item_in_seq.quantity > 1 else item_in_seq.weight, # Adjust weight if bundled
                    quantity=item_in_seq.quantity, # This will be handled by bundle logic in Item constructor if needed
                    fragility=item_in_seq.fragility,
                    stackable=item_in_seq.stackable,
                    boxing_type=item_in_seq.boxing_type,
                    bundle=item_in_seq.bundle, # Let Item constructor handle bundling if quantity > 1
                    load_bearing=item_in_seq.load_bearing,
                    temperature_sensitivity=item_in_seq.temperature_sensitivity
                )
                item_copy.needs_insulation = item_in_seq.needs_insulation # Preserve this flag
                items_to_pack_for_eval.append((item_copy, rotation_flag_val))
            else:
                logger.error(f"Item in genome.item_sequence is not an Item object: {item_in_seq}")
                continue # Skip non-Item objects

        # Pre-sort items by volume and weight for better initial packing
        # Ensure dimensions are available for sorting
        items_to_pack_for_eval.sort(key=lambda x: (
            -(x[0].dimensions[0] * x[0].dimensions[1] * x[0].dimensions[2]) if hasattr(x[0], 'dimensions') and len(x[0].dimensions) == 3 else 0,
            -x[0].weight if hasattr(x[0], 'weight') else 0,
            not x[0].stackable if hasattr(x[0], 'stackable') else True
        ), reverse=True) # Sorting should be largest to smallest, heaviest to lightest
        
        # Pack items and track metrics
        total_contact_area_eval = 0.0
        total_surface_area_eval = 0.0
        
        for item_obj, rotation_flag_val in items_to_pack_for_eval:
            original_dims = item_obj.dimensions # This should be the (potentially bundled) dimensions
            # Apply rotation to a temporary dimension variable for placement checks
            rotated_dims_for_check = GeneticPacker._get_rotation(None, original_dims, rotation_flag_val)
            
            best_pos_eval = None
            best_rot_applied = None # Store the actual dimensions used for packing
            best_space_eval = None
            best_score_eval = float('-inf')
            
            is_temperature_sensitive_eval = hasattr(item_obj, 'needs_insulation') and item_obj.needs_insulation and self.route_temperature is not None
            
            for space_candidate in container.spaces:
                if is_temperature_sensitive_eval and hasattr(space_candidate, 'temperature_safe') and not space_candidate.temperature_safe:
                    continue
                    
                if space_candidate.can_fit_item(rotated_dims_for_check):
                    pos_candidate = (space_candidate.x, space_candidate.y, space_candidate.z)
                    # Pass rotated_dims_for_check for validation
                    if container._is_valid_placement(item_obj, pos_candidate, rotated_dims_for_check):
                        if is_temperature_sensitive_eval:
                            wall_buffer = 0.3
                            x_pos, y_pos, z_pos = pos_candidate
                            w_dim, d_dim, h_dim = rotated_dims_for_check # Use rotated dimensions for checks
                            
                            # Check proximity to all six walls
                            if not (x_pos >= wall_buffer and \
                                    y_pos >= wall_buffer and \
                                    z_pos >= wall_buffer and \
                                    container.dimensions[0] - (x_pos + w_dim) >= wall_buffer and \
                                    container.dimensions[1] - (y_pos + d_dim) >= wall_buffer and \
                                    container.dimensions[2] - (z_pos + h_dim) >= wall_buffer):
                                continue
                        
                        contact_score_eval = 0.0
                        wall_contacts_eval = 0
                        # Use rotated_dims_for_check for contact calculations
                        if pos_candidate[0] == 0 or pos_candidate[0] + rotated_dims_for_check[0] == container.dimensions[0]:
                            wall_contacts_eval += 1
                        if pos_candidate[1] == 0 or pos_candidate[1] + rotated_dims_for_check[1] == container.dimensions[1]:
                            wall_contacts_eval += 1
                        if pos_candidate[2] == 0:
                            wall_contacts_eval += 1
                        
                        for placed_item_instance in container.items:
                            if hasattr(container, '_has_surface_contact') and hasattr(container, '_calculate_overlap_area') and \
                               container._has_surface_contact(pos_candidate, rotated_dims_for_check, placed_item_instance):
                                overlap_area_eval = container._calculate_overlap_area(
                                    (pos_candidate[0], pos_candidate[1], rotated_dims_for_check[0], rotated_dims_for_check[1]),
                                    (placed_item_instance.position[0], placed_item_instance.position[1],
                                     placed_item_instance.dimensions[0], placed_item_instance.dimensions[1])
                                )
                                contact_score_eval += overlap_area_eval
                        
                        current_placement_score = 0.0
                        if is_temperature_sensitive_eval:
                            center_x_container = container.dimensions[0] / 2
                            center_y_container = container.dimensions[1] / 2
                            # Use rotated_dims_for_check for item center calculation
                            item_center_x_eval = pos_candidate[0] + rotated_dims_for_check[0]/2
                            item_center_y_eval = pos_candidate[1] + rotated_dims_for_check[1]/2
                            
                            distance_from_center_sq = ((item_center_x_eval - center_x_container)**2 + 
                                                  (item_center_y_eval - center_y_container)**2)
                            max_distance_sq = ((container.dimensions[0]/2)**2 + (container.dimensions[1]/2)**2)
                            normalized_distance = (distance_from_center_sq / max_distance_sq) if max_distance_sq > 0 else 0.0
                                                  
                            central_bonus_eval = 50 * (1 - normalized_distance) # Max 50 points
                            current_placement_score = contact_score_eval * 3 + central_bonus_eval
                        else:
                            current_placement_score = contact_score_eval * 2 + wall_contacts_eval * 1.5
                        
                        if current_placement_score > best_score_eval:
                            best_score_eval = current_placement_score
                            best_pos_eval = pos_candidate
                            best_rot_applied = rotated_dims_for_check # This is the dimension set to use
                            best_space_eval = space_candidate
            
            if best_pos_eval and best_rot_applied: # Ensure best_rot_applied is also found
                item_obj.position = best_pos_eval
                item_obj.dimensions = best_rot_applied # Set the item's dimensions to the rotated ones used for packing
                container.items.append(item_obj)
                container._update_spaces(best_pos_eval, best_rot_applied, best_space_eval)
                
                item_surface_area = 2 * (
                    item_obj.dimensions[0] * item_obj.dimensions[1] +
                    item_obj.dimensions[1] * item_obj.dimensions[2] +
                    item_obj.dimensions[0] * item_obj.dimensions[2]
                )
                total_surface_area_eval += item_surface_area
                
                for other_item_instance in container.items[:-1]:
                    if hasattr(container, '_has_surface_contact') and hasattr(container, '_calculate_overlap_area') and \
                       container._has_surface_contact(item_obj.position, item_obj.dimensions, other_item_instance):
                        overlap_area_contact = container._calculate_overlap_area(
                             (item_obj.position[0], item_obj.position[1], item_obj.dimensions[0], item_obj.dimensions[1]),
                             (other_item_instance.position[0], other_item_instance.position[1], other_item_instance.dimensions[0], other_item_instance.dimensions[1])
                        )
                        total_contact_area_eval += overlap_area_contact
                
                sort_spaces_local(container)
        
        # Calculate all metrics
        metrics = {}
        container_volume_val = container.dimensions[0] * container.dimensions[1] * container.dimensions[2]
        
        packed_volume_total = sum(
            packed_item.dimensions[0] * packed_item.dimensions[1] * packed_item.dimensions[2] 
            for packed_item in container.items if hasattr(packed_item, 'dimensions') and len(packed_item.dimensions) == 3
        )
        metrics['volume_utilization'] = (packed_volume_total / container_volume_val) if container_volume_val > 0 else 0.0
        
        metrics['contact_ratio'] = total_contact_area_eval / (total_surface_area_eval + 1e-6) if total_surface_area_eval > 0 else 0.0
        
        try:
            # Ensure stability score is calculated correctly and handles missing methods/attributes
            if container.items and hasattr(container, '_calculate_stability_score'):
                stability_scores = [container._calculate_stability_score(s_item, s_item.position, s_item.dimensions)
                                    for s_item in container.items if hasattr(s_item, 'position') and hasattr(s_item, 'dimensions')]
                metrics['stability_score'] = sum(stability_scores) / len(stability_scores) if stability_scores else 0.0
            else:
                metrics['stability_score'] = 0.0
        except (AttributeError, ZeroDivisionError, TypeError) as e:
            logger.debug(f"Could not calculate stability score: {e}")
            metrics['stability_score'] = 0.0
        
        try:
            metrics['weight_balance'] = container._calculate_weight_balance_score() if hasattr(container, '_calculate_weight_balance_score') else 0.0
        except AttributeError as e:
            logger.debug(f"Could not calculate weight balance score: {e}")
            metrics['weight_balance'] = 0.0
            
        metrics['items_packed_ratio'] = (len(container.items) / len(genome.item_sequence)) if len(genome.item_sequence) > 0 else \
                                      (1.0 if not genome.item_sequence and not container.items else 0.0) # Handle empty item sequence

        # Temperature Constraint Score
        # Higher is better (closer to 1.0 means constraint is well met)
        temp_constraint_score = 1.0 # Default if no temp items or no route temp
        if self.route_temperature is not None:
            temp_sensitive_packed_items = [item for item in container.items if getattr(item, 'needs_insulation', False)]
            if temp_sensitive_packed_items:
                total_min_wall_distance = 0
                target_avg_wall_distance = 0.3 # e.g., 30cm desired average distance from wall

                for item in temp_sensitive_packed_items:
                    if not (hasattr(item, 'position') and hasattr(item, 'dimensions')):
                        continue
                    x, y, z = item.position
                    w, d, h = item.dimensions
                    
                    # Distances to each of the 6 walls
                    dist_to_walls = [
                        x, y, z,
                        container.dimensions[0] - (x + w),
                        container.dimensions[1] - (y + d),
                        container.dimensions[2] - (z + h)
                    ]
                    min_dist_for_item = min(d for d in dist_to_walls if d >= 0) # Smallest distance to any wall
                    total_min_wall_distance += min_dist_for_item
                
                avg_min_wall_distance = total_min_wall_distance / len(temp_sensitive_packed_items) if temp_sensitive_packed_items else 0
                
                # Normalize score: 1 if avg distance >= target, scales down to 0
                temp_constraint_score = min(1.0, avg_min_wall_distance / target_avg_wall_distance) if target_avg_wall_distance > 0 else 1.0
            # If no temp-sensitive items are packed, constraint is considered met.
        metrics['temperature_constraint'] = temp_constraint_score

        # Weight Capacity Score
        # Higher is better (1.0 if within capacity, penalizes overweight)
        weight_capacity_score = 1.0
        if hasattr(container, 'weight_capacity') and container.weight_capacity is not None and container.weight_capacity > 0:
            total_packed_weight = sum(item.weight for item in container.items if hasattr(item, 'weight'))
            if total_packed_weight > container.weight_capacity:
                # Penalize proportionally to how much it's overweight
                # Score becomes 0 if 2x over capacity, 0.5 if 1.5x over capacity etc.
                overweight_ratio = total_packed_weight / container.weight_capacity
                weight_capacity_score = max(0.0, 2.0 - overweight_ratio) # Linear penalty
        metrics['weight_capacity'] = weight_capacity_score

        # Store metrics in genome for detailed logging
        genome.metrics = metrics

        # Apply weights to calculate main fitness
        current_weights = self.fitness_weights
        if not current_weights or not isinstance(current_weights, dict) or not any(w > 0 for w in current_weights.values()):
            logger.warning("_evaluate_fitness: self.fitness_weights not set, invalid, or all zero. Falling back to default.")
            current_weights = self._get_default_fitness_weights() 
        
        fitness = 0.0
        for weight_name, weight_value in current_weights.items():
            metric_key = weight_name.replace('_weight', '')
            metric_value = metrics.get(metric_key, 0.0)
            fitness += metric_value * weight_value
            logger.debug(f"Fitness component: {metric_key}={metric_value:.4f} * {weight_value:.4f} = {metric_value * weight_value:.4f}")
        
        # Store metrics in genome for detailed logging
        genome.metrics = metrics

        # Apply weights to calculate main fitness
        current_weights = self.fitness_weights
        if not current_weights or not isinstance(current_weights, dict) or not any(w > 0 for w in current_weights.values()):
            logger.warning("_evaluate_fitness: self.fitness_weights not set, invalid, or all zero. Falling back to default.")
            current_weights = self._get_default_fitness_weights() 
        
        fitness = 0.0
        for weight_name, weight_value in current_weights.items():
            metric_key = weight_name.replace('_weight', '')
            metric_value = metrics.get(metric_key, 0.0)
            fitness += metric_value * weight_value
            logger.debug(f"Fitness component: {metric_key}={metric_value:.4f} * {weight_value:.4f} = {metric_value * weight_value:.4f}")
        
        genome.fitness = fitness # Assign calculated fitness to the genome object
        logger.debug(f"Total fitness: {fitness:.4f}, Metrics: {metrics}")
        return fitness

    def mutate_population(self, population, operation_focus, rate_modifier):
        """
        Mutate a population of genomes with specified mutation strategy
        
        Args:
            population: List of PackingGenome instances to mutate
            operation_focus: Specific mutation operations to focus on
            rate_modifier: Adjustment to mutation rate
        """
        for genome in population:
            genome.mutate(operation_focus=operation_focus, rate_modifier=rate_modifier)
    
    def _get_adaptive_mutation_strategy(self, generation: int, population, 
                                     stagnation_counter: int) -> Optional[Dict[str, Any]]:
        """
        Get adaptive mutation strategy recommendations from LLM
        
        Args:
            generation: Current generation number
            population: Current population of genomes
            stagnation_counter: Number of generations without improvement
            
        Returns:
            Dictionary with mutation strategy recommendations or None if API call fails
        """
        # Check every 3 generations instead of 5 when stagnation is high
        check_frequency = 3 if stagnation_counter >= 5 else 5
        
        # Always check when stagnation is getting critical
        if generation % check_frequency != 0 and stagnation_counter < 5:
            # If stagnation is detected but not critical, use fallback aggressive strategy
            if stagnation_counter >= 3:
                # Return aggressive mutation strategy without calling LLM
                return self._get_aggressive_mutation_strategy(stagnation_counter)
            return None
            
        try:
            # Calculate current statistics
            fitnesses = [g.fitness for g in population]
            avg_fitness = sum(fitnesses) / len(fitnesses)
            best_fitness = max(fitnesses)
            fitness_variance = sum((f - avg_fitness) ** 2 for f in fitnesses) / len(fitnesses)
            
            # Print key algorithm metrics with cleaner formatting
            logger.info(f"\n{'='*20} ALGORITHM METRICS {'='*20}")
            logger.info(f"Generation: {generation} | Population: {len(population)}")
            logger.info(f"Best fitness: {best_fitness:.4f} | Average: {avg_fitness:.4f}")
            logger.info(f"Fitness variance: {fitness_variance:.6f} | Stagnation: {stagnation_counter}")
            
            # Create a prompt with current algorithm state
            prompt = f"""
            Return a mutation strategy for a genetic algorithm optimizing 3D bin packing with temperature-sensitive items.
            Current metrics:
            - Generation: {generation}
            - Best fitness: {best_fitness:.4f}
            - Average fitness: {avg_fitness:.4f}
            - Fitness variance: {fitness_variance:.6f}
            - Stagnation: {stagnation_counter} generations

            Based on these metrics, provide a JSON object with these EXACT keys:
            {{
                "mutation_rate_modifier": number, // Between -0.05 and 0.2
                "operation_focus": string,        // One of: "rotation", "swap", "subsequence", "balanced", "aggressive" 
                "explanation": string             // Brief explanation of strategy choice
            }}

            Guidelines for strategy selection:
            - High fitness variance ({fitness_variance:.6f} > 0.1) -> Need more exploitation, focus on subsequence for better interlocking
            - Low fitness variance ({fitness_variance:.6f} < 0.01) -> Need more exploration with swap operations
            - Stagnation ({stagnation_counter} > 5 generations) -> VERY aggressive mutation with highest rate modifier (0.15-0.2)
            - Temperature-sensitive items require central placement with good interlocking -> subsequence operations help
            - Poor space utilization requires compact placement -> subsequence operations help group similar items
            - High stagnation should trigger "aggressive" operation_focus with high mutation rate

            Focus options effects:
            - "rotation": Prioritize item orientation changes - good for fine-tuning but not for interlocking
            - "swap": Prioritize reordering items - good for exploration
            - "subsequence": Prioritize moving groups of items - BEST FOR INTERLOCKING and temperature-sensitive items
            - "balanced": Equal focus on all operations - use when uncertain
            - "aggressive": NEW OPTION - combines high rate subsequence mutations with random reordering - best for escaping stagnation

            If stagnation > 8, ALWAYS use "aggressive" focus with maximum rate modifier (0.2).
            If stagnation between 5-8, use "subsequence" with high rate modifier (0.15-0.2).
            If stagnation < 5, use "balanced" or specific focus based on fitness variance.

            RESPOND WITH ONLY THE JSON OBJECT, NO OTHER TEXT.
            """
            
            response = llm_client.generate(prompt)
            
            try:
                strategy = json.loads(response.strip())
                if "mutation_rate_modifier" in strategy and "operation_focus" in strategy:
                    # Allow higher mutation rates for stagnation scenarios (up to 0.2)
                    max_modifier = 0.2 if stagnation_counter >= 5 else 0.15
                    strategy["mutation_rate_modifier"] = max(-0.05, min(max_modifier, strategy["mutation_rate_modifier"]))
                    
                    # Override with aggressive strategy for high stagnation
                    if stagnation_counter >= 8 and strategy["operation_focus"] != "aggressive":
                        strategy["operation_focus"] = "aggressive"
                        strategy["mutation_rate_modifier"] = 0.2
                        strategy["explanation"] = "Overriding with aggressive strategy due to critical stagnation"
                    
                    logger.info(f"    🤖 LLM Strategy: {strategy['operation_focus']} (rate: {strategy['mutation_rate_modifier']:.3f})")
                    logger.info(f"    💭 Explanation: {strategy.get('explanation', 'No explanation provided')}")
                    return strategy
                    
            except json.JSONDecodeError:
                logger.warning("WARNING: Invalid LLM response format")
                return self._get_aggressive_mutation_strategy(stagnation_counter)
                
            return None
            
        except Exception as e:
            logger.error(f"ERROR: Failed to get adaptive mutation strategy: {e}")
            return self._get_aggressive_mutation_strategy(stagnation_counter)
    
    def _get_aggressive_mutation_strategy(self, stagnation_counter: int) -> Dict[str, Any]:
        """
        Generate an aggressive mutation strategy without using LLM when stagnation is detected
        
        Args:
            stagnation_counter: Number of generations without improvement
            
        Returns:
            Dictionary with aggressive mutation strategy
        """
        # Scale mutation rate based on stagnation severity
        if stagnation_counter >= 10:
            # Critical stagnation - maximum disruption
            return {
                "mutation_rate_modifier": 0.2,
                "operation_focus": "aggressive",
                "explanation": "Critical stagnation detected - using maximum disruption strategy"
            }
        elif stagnation_counter >= 7:
            # Severe stagnation - use subsequence with high rate
            return {
                "mutation_rate_modifier": 0.15,
                "operation_focus": "subsequence", 
                "explanation": "Severe stagnation - using high disruption subsequence strategy"
            }
        elif stagnation_counter >= 3:
            # Mild stagnation - increase exploration
            return {
                "mutation_rate_modifier": 0.1,
                "operation_focus": "swap",
                "explanation": "Mild stagnation - increasing exploration with swap operations"
            }
        else:
            # Default balanced strategy
            return {
                "mutation_rate_modifier": 0.05,
                "operation_focus": "balanced",
                "explanation": "Default balanced strategy for early optimization"
            }

    def _get_dynamic_fitness_weights(self, generation: int, population, 
                                     current_metrics: Dict[str, float]) -> Optional[Dict[str, float]]:
        """Get dynamic fitness function weights from LLM based on current optimization state"""
        
        try:
            global llm_client, logger # Access module-level instances
            
            # Handle None current_metrics
            if current_metrics is None:
                logger.warning("current_metrics is None in _get_dynamic_fitness_weights. Cannot fetch dynamic weights.")
                return None

            if not llm_client or not hasattr(llm_client, 'get_llm_completion'):
                logger.info("LLM client not available for dynamic fitness weights.")
                return None
            
            # Calculate metrics for LLM context
            avg_fitness = sum(g.fitness for g in population) / len(population) if population else 0
            best_fitness = max((g.fitness for g in population), default=0)
            fitness_variance = np.var([g.fitness for g in population]) if population else 0 # Requires numpy
            
            logger.info(f"\\n{'='*20} DYNAMIC FITNESS WEIGHTS REQUEST {'='*20}")
            logger.info(f"Generation: {generation} | Best fitness: {best_fitness:.4f} | Average: {avg_fitness:.4f}")
            logger.info("Current Metrics:")
            logger.info(f"  Volume utilization: {current_metrics.get('volume_utilization', 0.0):.4f}")
            logger.info(f"  Contact ratio: {current_metrics.get('contact_ratio', 0.0):.4f}")
            logger.info(f"  Stability score: {current_metrics.get('stability_score', 0.0):.4f}")
            logger.info(f"  Weight balance: {current_metrics.get('weight_balance', 0.0):.4f}")
            logger.info(f"  Items packed ratio: {current_metrics.get('items_packed_ratio', 0.0):.4f}")
            
            # Create a prompt with current algorithm state
            prompt = f"""
            Adjust the fitness weights for a genetic algorithm optimizing 3D bin packing with temperature-sensitive items.
            The algorithm is currently at generation {generation}.
            Current performance metrics:
            - Best fitness: {best_fitness:.4f}
            - Average fitness: {avg_fitness:.4f}
            - Fitness variance: {fitness_variance:.6f}
            Detailed current packing metrics:
            - Volume utilization: {current_metrics.get('volume_utilization', 0.0):.4f}
            - Stability score: {current_metrics.get('stability_score', 0.0):.4f}
            - Contact ratio: {current_metrics.get('contact_ratio', 0.0):.4f}
            - Weight balance: {current_metrics.get('weight_balance', 0.0):.4f}
            - Items packed ratio: {current_metrics.get('items_packed_ratio', 0.0):.4f}
            - Route temperature: {self.route_temperature if self.route_temperature is not None else "Not set"}

            Based on these metrics, provide a new set of fitness weights in JSON format.
            The weights should guide the optimization towards improving areas that are currently underperforming
            or reinforce strategies that are working well. For example, if volume utilization is low, consider increasing its weight.
            If stability is poor, its weight might need an increase.
            
            Return the weights in JSON format with the following keys:
            - volume_utilization_weight
            - stability_score_weight
            - contact_ratio_weight
            - weight_balance_weight
            - items_packed_ratio_weight
            - temperature_constraint_weight (adjust based on presence of temp-sensitive items and route_temperature. If route_temperature is not set, this weight should likely be low or zero unless items are inherently temperature-sensitive.)
            - explanation (brief explanation for the chosen weight adjustments)

            Ensure the numeric weights sum up to 1.0.
            RESPOND WITH ONLY THE JSON OBJECT, NO OTHER TEXT.
            """
            
            response_text = llm_client.get_llm_completion(prompt)
            logger.info(f"LLM response for dynamic fitness weights: {response_text}")
            
            if not response_text:
                logger.warning("LLM returned an empty response for dynamic fitness weights.")
                return None

            # It's good practice to strip whitespace before parsing JSON
            weights_data = json.loads(response_text.strip()) 
            
            explanation = weights_data.pop("explanation", "No explanation provided by LLM for dynamic weights.")
            logger.info(f"LLM Explanation for dynamic weights: {explanation}")

            expected_weight_keys = [
                'volume_utilization_weight', 'stability_score_weight', 
                'contact_ratio_weight', 'weight_balance_weight', 
                'items_packed_ratio_weight', 'temperature_constraint_weight'
            ]
            
            parsed_weights = {}
            for key in expected_weight_keys:
                parsed_weights[key] = float(weights_data.get(key, 0.0)) # Default to 0.0 if key is missing
            
            total_weight = sum(parsed_weights.values())

            if abs(total_weight) < 1e-6: # Check if sum is effectively zero
                 logger.warning("Sum of dynamic weights from LLM is zero. Cannot normalize. Returning None.")
                 return None

            if abs(total_weight - 1.0) > 0.01: # Normalize if not already summing to 1.0
                logger.info(f"Normalizing LLM dynamic weights. Original sum: {total_weight}")
                for key in parsed_weights:
                    parsed_weights[key] /= total_weight # Normalize
            
            logger.info(f"Successfully obtained and processed dynamic fitness weights: {parsed_weights}")
            return parsed_weights
            
        except json.JSONDecodeError:
            logger.error("Error decoding JSON response from LLM for dynamic fitness weights.", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error getting dynamic fitness weights from LLM: {e}", exc_info=True)
            return None

    def optimize(self, items, fitness_weights=None):
        """
        Run the genetic algorithm to find the best packing solution.
        Args:
            items: List of items to pack
            fitness_weights (dict, optional): Predefined fitness weights from UI.
                                              If None or empty, dynamic weights may be fetched.
        Returns:
            tuple: (best_genome, best_fitness, generation_count)
        """
        self.items_to_pack = items # Store items for use in _calculate_initial_metrics and _evaluate_fitness
        
        logger.info(f"GeneticPacker.optimize called. Received fitness_weights from UI/caller: {fitness_weights}")

        # Determine the fitness weights to use
        if fitness_weights and isinstance(fitness_weights, dict) and any(w > 0 for w in fitness_weights.values()): # Check if any weight is positive
            self.fitness_weights = fitness_weights
            logger.info(f"Using fitness weights provided by UI/caller: {self.fitness_weights}")
        else:
            if not fitness_weights:
                 logger.info("No fitness_weights from UI/caller (None or empty). Attempting to get dynamic weights from LLM.")
            else: # Handles case where fitness_weights might be e.g. all zeros from UI
                 logger.info(f"Received fitness_weights from UI/caller ({fitness_weights}), but they are not effectively usable (e.g., all zero). Attempting to get dynamic weights from LLM.")

            # Calculate initial metrics first, as _get_initial_dynamic_fitness_weights might need them.
            # self.items_to_pack should be set before calling _calculate_initial_metrics.
            initial_metrics_for_llm = self._calculate_initial_metrics()
            dynamic_weights = self._get_initial_dynamic_fitness_weights(initial_metrics=initial_metrics_for_llm) 
            
            if dynamic_weights:
                self.fitness_weights = dynamic_weights
                logger.info(f"Using dynamic fitness weights from LLM: {self.fitness_weights}")
            else:
                logger.info("Failed to get dynamic weights from LLM or LLM disabled. Using default fitness weights.")
                self.fitness_weights = self._get_default_fitness_weights()
        
        # Final fallback: Ensure fitness_weights are always set to a default if still None or empty
        if not self.fitness_weights or not any(w > 0 for w in self.fitness_weights.values()):
            logger.warning("Fitness weights were still None, empty, or all zero after all attempts. Forcing default weights.")
            self.fitness_weights = self._get_default_fitness_weights()
        
        logger.info(f"Final fitness weights for optimization run: {self.fitness_weights}")

        # Initialize population
        population = [PackingGenome(items) for _ in range(self.population_size)]
        best_overall_genome = None
        best_overall_fitness = float('-inf')
        stagnation_counter = 0

        for generation in range(self.generations):
            logger.info(f"\n{'='*60}")
            logger.info(f"🧬 GENERATION {generation + 1}/{self.generations}")
            logger.info(f"{'='*60}")

            # Evaluate fitness for the current population
            # Use sequential evaluation instead of multiprocessing to avoid pickling issues
            logger.info(f"  📊 Evaluating {len(population)} genomes...")
            for i, genome in enumerate(population):
                try:
                    genome.fitness = self._evaluate_fitness(genome)
                    if (i + 1) % 5 == 0 or i == len(population) - 1:
                        logger.info(f"    ✅ Evaluated {i + 1}/{len(population)} genomes (latest fitness: {genome.fitness:.4f})")
                except Exception as e:
                    logger.error(f"❌ Error evaluating genome {i + 1}: {e}")
                    genome.fitness = 0.0

            # Calculate generation statistics
            fitnesses = [g.fitness for g in population]
            current_best = max(fitnesses)
            current_avg = sum(fitnesses) / len(fitnesses)
            current_worst = min(fitnesses)
            current_std = np.std(fitnesses) if len(fitnesses) > 1 else 0.0
            
            logger.info(f"\n  📈 GENERATION {generation + 1} RESULTS:")
            logger.info(f"    🏆 Best fitness: {current_best:.4f}")
            logger.info(f"    📊 Average fitness: {current_avg:.4f}")
            logger.info(f"    📉 Worst fitness: {current_worst:.4f}")
            logger.info(f"    📏 Std deviation: {current_std:.4f}")
            
            # Show metrics from best genome in this generation
            best_gen_genome = max(population, key=lambda x: x.fitness)
            if hasattr(best_gen_genome, 'metrics') and best_gen_genome.metrics:
                metrics = best_gen_genome.metrics
                logger.info(f"    📋 Best genome metrics:")
                logger.info(f"       Volume util: {metrics.get('volume_utilization', 0.0):.2%} | "
                           f"Items packed: {metrics.get('items_packed_ratio', 0.0):.2%} | "
                           f"Stability: {metrics.get('stability_score', 0.0):.3f}")
                logger.info(f"       Contact ratio: {metrics.get('contact_ratio', 0.0):.3f} | "
                           f"Weight balance: {metrics.get('weight_balance', 0.0):.3f}")
                if self.route_temperature is not None:
                    logger.info(f"       Temp constraint: {metrics.get('temperature_constraint', 0.0):.3f}")
                if metrics.get('weight_capacity', 1.0) < 1.0:
                    logger.info(f"       Weight capacity: {metrics.get('weight_capacity', 0.0):.3f} (capacity exceeded!)")
            
            # Show fitness weights being used
            if generation == 0:
                logger.info(f"    ⚖️  Current fitness weights:")
                for weight_name, weight_value in self.fitness_weights.items():
                    if weight_value > 0:
                        metric_name = weight_name.replace('_weight', '')
                        logger.info(f"       {metric_name}: {weight_value:.3f}")

            # Update best overall solution if improved
            improved = False
            for genome in population:
                if genome.fitness > best_overall_fitness:
                    best_overall_fitness = genome.fitness
                    best_overall_genome = genome
                    improved = True
                    logger.info(f"    🎯 NEW BEST SOLUTION! Fitness: {genome.fitness:.4f}")

            # Check stagnation
            if not improved:
                stagnation_counter += 1
                logger.info(f"    ⏳ Stagnation: {stagnation_counter} generation(s)")
            else:
                stagnation_counter = 0
                logger.info(f"    🚀 Improvement found! Stagnation reset.")

            # Adaptive mutation strategy
            if stagnation_counter >= 5:
                new_strategy = self._get_adaptive_mutation_strategy(generation, population, stagnation_counter)
                if new_strategy:
                    logger.info(f"    🧬 Adapting mutation strategy: {new_strategy['operation_focus']} (rate: {new_strategy['mutation_rate_modifier']:.3f})")
                    logger.info(f"    💡 Reasoning: {new_strategy.get('explanation', 'No explanation provided')}")
                    for genome in population:
                        genome.mutate(
                            operation_focus=new_strategy["operation_focus"],
                            rate_modifier=new_strategy["mutation_rate_modifier"]
                        )

            # Dynamic fitness weight adjustment every few generations (only if LLM is available)
            if generation > 0 and generation % 3 == 0 and best_overall_genome:
                # Get current metrics from best genome for dynamic weight adjustment
                current_metrics = getattr(best_overall_genome, 'metrics', {})
                if current_metrics:
                    dynamic_weights = self._get_dynamic_fitness_weights(generation, population, current_metrics)
                    if dynamic_weights:
                        logger.info(f"    🎯 Updated fitness weights based on current performance")
                        logger.info(f"    📊 New weights: {dynamic_weights}")
                        self.fitness_weights = dynamic_weights

            # Elitism: carry forward the best genome
            elite_count = max(1, int(self.population_size * self.elite_percentage))
            new_population = sorted(population, key=lambda x: x.fitness, reverse=True)[:elite_count]

            # Crossover and mutation to create new population
            while len(new_population) < self.population_size:
                parent1 = self._tournament_select(population)
                parent2 = self._tournament_select(population)
                child = self._crossover(parent1, parent2)
                
                # Apply mutation
                child.mutate(
                    operation_focus="balanced",  # Use a balanced approach for exploration
                    rate_modifier=random.uniform(0.05, 0.2)  # Small to moderate mutation rate
                )
                
                new_population.append(child)
            
            population = new_population

        # Final generation summary
        logger.info(f"\n{'='*60}")
        logger.info(f"🏁 OPTIMIZATION COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"  🏆 Best fitness achieved: {best_overall_fitness:.4f}")
        logger.info(f"  📊 Generations completed: {self.generations}")
        if best_overall_genome and hasattr(best_overall_genome, 'metrics'):
            metrics = best_overall_genome.metrics
            logger.info(f"  📈 Final metrics:")
            logger.info(f"    - Volume utilization: {metrics.get('volume_utilization', 0.0):.2%}")
            logger.info(f"    - Items packed ratio: {metrics.get('items_packed_ratio', 0.0):.2%}")
            logger.info(f"    - Stability score: {metrics.get('stability_score', 0.0):.3f}")
            logger.info(f"    - Contact ratio: {metrics.get('contact_ratio', 0.0):.3f}")
            logger.info(f"    - Weight balance: {metrics.get('weight_balance', 0.0):.3f}")
            logger.info(f"    - Temperature constraint: {metrics.get('temperature_constraint', 0.0):.3f}")
            logger.info(f"    - Weight capacity: {metrics.get('weight_capacity', 0.0):.3f}")
        logger.info(f"{'='*60}")

        self.best_solution = best_overall_genome
        self.best_fitness = best_overall_fitness
        self.generation_count = self.generations
        
        # Store final performance data in the best genome for reporting
        if best_overall_genome:
            best_overall_genome.best_fitness = best_overall_fitness
            best_overall_genome.generation_count = self.generations
        
        return best_overall_genome

    @staticmethod
    def _get_rotation(_, original_dims: Tuple[float, float, float], rotation_flag: int) -> Tuple[float, float, float]:
        """Get dimensions after rotation based on flag (static method for external access)"""
        l, w, h = original_dims
        rotations = [
            (l, w, h), (l, h, w), (w, l, h),
            (w, h, l), (h, l, w), (h, w, l)
        ]
        return rotations[rotation_flag]
    
    def _tournament_select(self, population, tournament_size=3):
        """Tournament selection"""
        tournament = random.sample(population, tournament_size)
        return max(tournament, key=lambda x: x.fitness)

    def _crossover(self, parent1, parent2):
        """Order crossover (OX) for sequence, uniform crossover for rotations"""
        # OX crossover for item sequence
        size = len(parent1.item_sequence)
        start, end = sorted(random.sample(range(size), 2))
        
        # Create child sequence using OX
        child_sequence = [None] * size
        child_sequence[start:end] = parent1.item_sequence[start:end]
        
        remaining = [item for item in parent2.item_sequence 
                    if item not in child_sequence[start:end]]
        
        j = 0
        for i in range(size):
            if child_sequence[i] is None:
                child_sequence[i] = remaining[j]
                j += 1
        
        # Uniform crossover for rotations
        child_rotations = array('B', [
            parent1.rotation_flags[i] if random.random() < 0.5 
            else parent2.rotation_flags[i]
            for i in range(size)
        ])
        
        child = PackingGenome(child_sequence)
        child.rotation_flags = child_rotations
        return child