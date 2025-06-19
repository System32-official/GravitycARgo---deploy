"""
Main entry point for genetic algorithm container packing optimization.
Integrates temperature constraints and packer logic.
"""
import os
import logging
from typing import List, Dict, Any

from optigenix_module.models.container import EnhancedContainer
from optigenix_module.models.item import Item
from optigenix_module.optimization.temperature import TemperatureConstraintHandler
from optigenix_module.optimization.packer import GeneticPacker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("genetic")

# Add a prominent message to show when this module is imported
logger.info("=" * 70)
logger.info("GENETIC ALGORITHM MODULE LOADED WITH LLM INTEGRATION")
logger.info("=" * 70)

def optimize_packing_with_genetic_algorithm(items, container_dims, 
                                         population_size=10, generations=8,
                                        fitness_weights=None, route_temperature=None):
    """Main function to optimize packing using genetic algorithm"""
    # Set route temperature from environment variable
    from optigenix_module.utils.llm_connector import get_llm_client
      # First, handle item quantities and sort by volume/weight for smarter initialization
    expanded_items = []
    original_item_count = 0
    
    for item in items:
        quantity = getattr(item, 'quantity', 1)
        original_item_count += quantity
        
        # Check if item is bundled - bundled items should NOT be expanded
        is_bundled = getattr(item, 'bundle', 'NO') == 'YES'
        
        if quantity > 1 and not is_bundled:
            # Only expand non-bundled items with quantity > 1
            logger.info(f"Expanding non-bundled item {item.name} with quantity {quantity}")
            for i in range(quantity):
                new_item = Item(
                    name=f"{item.name}_{i+1}",
                    length=item.original_dims[0],  # Use original dimensions for individual items
                    width=item.original_dims[1],
                    height=item.original_dims[2],
                    weight=item.weight / quantity if quantity > 0 else item.weight,  # Divide weight back to individual weight
                    quantity=1,
                    fragility=item.fragility,
                    stackable=item.stackable,
                    boxing_type=getattr(item, 'boxing_type', 'STANDARD'),
                    bundle='NO',  # Individual items are not bundled
                    temperature_sensitivity=getattr(item, 'temperature_sensitivity', None),
                    load_bearing=getattr(item, 'load_bearing', 0)
                )                # Explicitly set needs_insulation flag if needed
                if hasattr(item, 'needs_insulation'):
                    new_item.needs_insulation = item.needs_insulation
                expanded_items.append(new_item)
        else:
            # For bundled items or single items, use as-is
            if is_bundled and quantity > 1:
                logger.info(f"Keeping bundled item {item.name} as single unit (quantity {quantity} bundled together)")
            else:
                logger.info(f"Keeping single item {item.name}")
            # Important: Copy temperature sensitivity and load bearing properties
            if not hasattr(item, 'temperature_sensitivity'):
                setattr(item, 'temperature_sensitivity', None)
            if not hasattr(item, 'load_bearing'):
                setattr(item, 'load_bearing', 0)
                
            expanded_items.append(item)
    
    logger.info(f"Expanded {len(items)} CSV items to {len(expanded_items)} packable items")
    logger.info(f"Original quantity sum: {original_item_count}")
    
    # Log expansion summary for debugging
    bundled_items = [item for item in items if getattr(item, 'bundle', 'NO') == 'YES']
    non_bundled_items = [item for item in items if getattr(item, 'bundle', 'NO') == 'NO']
    
    bundled_count = len(bundled_items)
    non_bundled_total = sum(getattr(item, 'quantity', 1) for item in non_bundled_items)
    expected_total = bundled_count + non_bundled_total
    
    logger.info("=" * 50)
    logger.info("QUANTITY EXPANSION SUMMARY:")
    logger.info(f"  CSV rows processed: {len(items)}")
    logger.info(f"  Total raw quantity: {original_item_count} pieces")
    logger.info(f"  Bundled items (kept as bundles): {bundled_count}")
    logger.info(f"  Non-bundled items (expanded): {non_bundled_total}")
    logger.info(f"  Expected packable items: {expected_total}")
    logger.info(f"  Actual packable items: {len(expanded_items)}")
    if len(expanded_items) == expected_total:
        logger.info("  ✅ EXPANSION SUCCESS: Counts match!")
    else:
        logger.warning(f"  ❌ EXPANSION MISMATCH: Expected {expected_total}, got {len(expanded_items)}")
    logger.info("=" * 50)
      # Get route temperature if needed
    # FIXED: Always create context with temp handler to ensure temperature constraints work
    context = {'items': expanded_items}
    llm_client = get_llm_client()
    temp_result = llm_client.ensure_temperature_constraints(context=context)
    
    # Handle both dict and float return types for backward compatibility
    if isinstance(temp_result, dict):
        route_temperature = temp_result['route_temperature']
    else:
        # Fallback for when a float is returned
        route_temperature = float(temp_result) if temp_result is not None else 25.0
        temp_result = {'route_temperature': route_temperature, 'constraints_applied': False}
    
    # Use processed items from context with temperature constraints applied
    expanded_items = context['items']
    temp_handler = context.get('temp_handler')
    
    # Log temperature constraint details
    has_temp_sensitive = any(getattr(item, 'needs_insulation', False) for item in expanded_items)
    if has_temp_sensitive:
        logger.info(f"Temperature constraints active: {temp_result.get('temp_sensitive_count', 0)} sensitive items at {route_temperature}°C")
    else:
        logger.info(f"No temperature-sensitive items found at {route_temperature}°C")
    
    # Sort items with temperature-sensitive ones first
    expanded_items.sort(key=lambda x: (getattr(x, 'temperature_priority', 0)), reverse=True)
      # Initialize genetic packer with temperature constraints
    genetic_packer = GeneticPacker(container_dims, population_size, generations, route_temperature)
    if temp_handler:
        genetic_packer.temp_handler = temp_handler
    
    # Run optimization with fitness weights
    if fitness_weights:
        logger.info(f"Using custom fitness weights from UI sliders: {fitness_weights}")
        best_genome = genetic_packer.optimize(expanded_items, fitness_weights=fitness_weights)
    else:
        logger.info("No fitness weights provided - will use LLM dynamic weights or defaults")
        best_genome = genetic_packer.optimize(expanded_items)
    
    # Create final container with best solution
    return final_packing(best_genome, container_dims, expanded_items, route_temperature, original_item_count)

def final_packing(best_genome, container_dims, expanded_items, route_temperature=None, original_item_count=None):
    """
    Creates final container with best solution from genetic algorithm
    
    Args:
        best_genome: The best genome from genetic algorithm
        container_dims: Container dimensions (w, d, h)
        expanded_items: List of expanded items
        route_temperature: Temperature setting for the route
        original_item_count: Original count of items (including quantities)
        
    Returns:
        EnhancedContainer with packed items
    """
    successful_packs = 0
    failed_packs = 0
    
    # Initialize temperature handler if needed
    temp_handler = None
    if route_temperature is not None:
        temp_handler = TemperatureConstraintHandler(route_temperature)
    
    # Create container for final packing
    container = EnhancedContainer(container_dims)
    if route_temperature is not None:
        container.route_temperature = route_temperature
    
    # Sort spaces after each item placement for better utilization
    def sort_spaces_by_fitness(container):
        """Sort spaces by a fitness score that prefers spaces with better interlocking potential"""
        container.spaces.sort(key=lambda space: (
            # First prioritize bottom spaces for stability
            space.z,
            # Then prioritize spaces with multiple contact surfaces (corners, against walls)
            -(sum(1 for val in [space.x, space.y, space.z] if val == 0) + 
              sum(1 for dim, val in zip(range(3), [space.x+space.width, space.y+space.depth, space.z+space.height]) 
                  if val == container.dimensions[dim])),
            # Then prioritize spaces adjacent to existing items for interlocking
            -len([item for item in container.items 
                 if (abs(space.x - (item.position[0] + item.dimensions[0])) < 0.001 or
                     abs(space.x + space.width - item.position[0]) < 0.001 or
                     abs(space.y - (item.position[1] + item.dimensions[1])) < 0.001 or
                     abs(space.y + space.depth - item.position[1]) < 0.001 or
                     abs(space.z - (item.position[2] + item.dimensions[2])) < 0.001 or
                     abs(space.z + space.height - item.position[2]) < 0.001)]),
            # Then prefer spaces closer to origin for compact packing
            space.x**2 + space.y**2 + space.z**2
        ))
    
    # Track which items couldn't be packed for better reporting
    unpacked_items = []
    
    # First try to pack with the genome's suggested order and rotations
    for item, rotation_flag in zip(best_genome.item_sequence, best_genome.rotation_flags):
        # Apply rotation based on flag
        item_copy = Item(
            name=item.name,
            length=item.original_dims[0] if hasattr(item, 'original_dims') else item.dimensions[0],
            width=item.original_dims[1] if hasattr(item, 'original_dims') else item.dimensions[1],
            height=item.original_dims[2] if hasattr(item, 'original_dims') else item.dimensions[2],
            weight=item.weight,
            quantity=1,  # Already expanded
            fragility=item.fragility,
            stackable=item.stackable,
            boxing_type=getattr(item, 'boxing_type', 'STANDARD'),
            bundle=item.bundle,
            temperature_sensitivity=getattr(item, 'temperature_sensitivity', None),
            load_bearing=getattr(item, 'load_bearing', 0)
        )
        
        # Explicitly transfer needs_insulation flag
        if hasattr(item, 'needs_insulation'):
            item_copy.needs_insulation = item.needs_insulation
        
        # Apply rotation using genetic packer's rotation method
        rotated_dims = GeneticPacker._get_rotation(None, item_copy.dimensions, rotation_flag)
        item_copy.dimensions = rotated_dims
        
        # Sort spaces before trying to place this item
        sort_spaces_by_fitness(container)
        
        # Print data about temperature-sensitive items for debugging - only at DEBUG level
        if hasattr(item_copy, 'needs_insulation') and item_copy.needs_insulation:
            logger.debug(f"Trying to place temperature-sensitive item: {item_copy.name}")
            logger.debug(f"  Temperature sensitivity: {item_copy.temperature_sensitivity}")
            logger.debug(f"  Needs insulation: {item_copy.needs_insulation}")
        
        # Try to pack item
        placed = False
        for space in container.spaces:
            if space.can_fit_item(item_copy.dimensions):
                pos = (space.x, space.y, space.z)
                if container._is_valid_placement(item_copy, pos, item_copy.dimensions):
                    # For temperature sensitive items, check temperature constraints with absolute prohibition
                    if hasattr(item_copy, 'needs_insulation') and item_copy.needs_insulation and temp_handler:
                        # Use temperature handler to check constraints
                        if not temp_handler.check_temperature_constraints(item_copy, pos, container.dimensions):
                            logger.info(f"  ❌ Rejected position for temperature-sensitive item {item_copy.name} at {pos}")
                            logger.info(f"     Failed temperature constraint check")
                            continue  # Try next space
                    
                    # Check weight bearing capacity
                    if space.z > 0:  # Only check for items not on the floor
                        items_below = [i for i in container.items if 
                                     i.position[2] + i.dimensions[2] == space.z and
                                     i.position[0] < pos[0] + item_copy.dimensions[0] and
                                     i.position[0] + i.dimensions[0] > pos[0] and
                                     i.position[1] < pos[1] + item_copy.dimensions[1] and
                                     i.position[1] + i.dimensions[1] > pos[1]]
                        
                        if items_below:
                            total_weight_above = sum(i.weight for i in items_below)
                            if total_weight_above > getattr(item_copy, 'load_bearing', 0):
                                logger.info(f"  ❌ Rejected position for item {item_copy.name} at {pos}")
                                logger.info(f"     Failed weight bearing capacity check: {total_weight_above} > {getattr(item_copy, 'load_bearing', 0)}")
                                continue  # Try next space
                    
                    item_copy.position = pos
                    
                    # Explicitly set color for temperature-sensitive items that need insulation
                    if hasattr(item_copy, 'needs_insulation') and item_copy.needs_insulation:
                        item_copy.color = 'rgb(0, 128, 255)'  # Dark blue for temperature sensitive items
                    
                    container.items.append(item_copy)
                    container._update_spaces(pos, item_copy.dimensions, space)
                    
                    # Print success for temperature-sensitive items
                    if hasattr(item_copy, 'needs_insulation') and item_copy.needs_insulation:
                        logger.info(f"  ✅ Successfully placed temperature-sensitive item {item_copy.name} at {pos}")
                        # Calculate center position
                        center_x = container.dimensions[0] / 2
                        center_y = container.dimensions[1] / 2
                        item_center_x = pos[0] + item_copy.dimensions[0]/2
                        item_center_y = pos[1] + item_copy.dimensions[1]/2
                        is_central = (
                            center_x - container.dimensions[0]/6 <= item_center_x <= center_x + container.dimensions[0]/6 and
                            center_y - container.dimensions[1]/6 <= item_center_y <= center_y + container.dimensions[1]/6
                        )
                        if is_central:
                            logger.info(f"     Placed in central area of container (good for temperature protection)")
                        else:
                            # Count surrounding items for insulation
                            surrounding_items = 0
                            insulating_items = 0
                            for placed_item in container.items[:-1]:  # Exclude current item
                                if container._has_surface_contact(pos, item_copy.dimensions, placed_item):
                                    surrounding_items += 1
                                    if not getattr(placed_item, 'needs_insulation', False):
                                        insulating_items += 1
                            logger.info(f"     Not in central area, but has {surrounding_items} surrounding items ({insulating_items} insulating)")
                    
                    # Sort spaces immediately after placing an item to use the newly created spaces
                    sort_spaces_by_fitness(container)
                    placed = True
                    successful_packs += 1
                    break
        
        if not placed:
            failed_packs += 1
            unpacked_items.append(item_copy)
            logger.info(f"  ❌ Failed to place item {item_copy.name}")
    
    # Log packing statistics
    logger.info(f"Packing complete - {successful_packs} items packed successfully, {failed_packs} failed")
    if unpacked_items:
        logger.info("Unpacked items:")
        for item in unpacked_items:
            logger.info(f"  - {item.name} ({item.dimensions[0]}x{item.dimensions[1]}x{item.dimensions[2]})")      # Add best fitness from genetic algorithm to container for reporting
    # Check both directly defined fitness and best_fitness attributes
    if hasattr(best_genome, 'best_fitness') and best_genome.best_fitness > 0:
        container.best_fitness = best_genome.best_fitness
        logger.info(f"Final container best fitness (from best_fitness): {container.best_fitness:.4f}")
    elif hasattr(best_genome, 'fitness'):
        container.best_fitness = best_genome.fitness
        logger.info(f"Final container best fitness (from fitness): {container.best_fitness:.4f}")
    
    # Add generation count if available
    if hasattr(best_genome, 'generation_count'):
        container.generation_count = best_genome.generation_count
        logger.info(f"Final container generation count: {container.generation_count}")
    
    # Call _update_metrics() to update volume utilization and other metrics
    container._update_metrics()
    logger.info(f"Updated metrics: volume utilization = {container.volume_utilization:.4f} ({container.volume_utilization*100:.1f}%)")
    
    # Store unpacked items for UI display
    container.unpacked_items = unpacked_items
    
    return container