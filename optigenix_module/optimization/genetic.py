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
                                         population_size=200, generations=150):
    """Main function to optimize packing using genetic algorithm"""
    # Set route temperature from environment variable
    from optigenix_module.utils.llm_connector import get_llm_client
    
    # First, handle item quantities and sort by volume/weight for smarter initialization
    expanded_items = []
    original_item_count = 0
    
    for item in items:
        quantity = getattr(item, 'quantity', 1)
        original_item_count += quantity
        
        if quantity > 1:
            logger.info(f"Expanding item {item.name} with quantity {quantity}")
            for i in range(quantity):
                new_item = Item(
                    name=f"{item.name}_{i+1}",
                    length=item.dimensions[0],
                    width=item.dimensions[1],
                    height=item.dimensions[2],
                    weight=item.weight,
                    quantity=1,
                    fragility=item.fragility,
                    stackable=item.stackable,
                    boxing_type=getattr(item, 'boxing_type', 'STANDARD'),
                    bundle=item.bundle,
                    temperature_sensitivity=getattr(item, 'temperature_sensitivity', None),
                    load_bearing=getattr(item, 'load_bearing', 0)
                )
                # Explicitly set needs_insulation flag if needed
                if hasattr(item, 'needs_insulation'):
                    new_item.needs_insulation = item.needs_insulation
                expanded_items.append(new_item)
        else:
            # Important: Copy temperature sensitivity and load bearing properties
            if not hasattr(item, 'temperature_sensitivity'):
                setattr(item, 'temperature_sensitivity', None)
            if not hasattr(item, 'load_bearing'):
                setattr(item, 'load_bearing', 0)
                
            expanded_items.append(item)
    
    logger.info(f"Expanded {len(items)} items to {len(expanded_items)} individual items for packing")
    logger.info(f"Total item count (including quantities): {original_item_count}")
    
    # Get route temperature if needed
    # FIXED: Always create context with temp handler to ensure temperature constraints work
    context = {'items': expanded_items}
    llm_client = get_llm_client()
    temp_result = llm_client.ensure_temperature_constraints(context)
    route_temperature = temp_result['route_temperature']
    
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
    
    # Run optimization
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
                    
                    successful_packs += 1
                    placed = True
                    break
        
        if not placed:
            # Try other rotations if the genome's suggested rotation didn't work
            for alt_flag in range(6):
                if alt_flag == rotation_flag:
                    continue  # Skip the already tried rotation
                
                alt_dims = GeneticPacker._get_rotation(None, item_copy.dimensions, alt_flag)
                item_copy.dimensions = alt_dims
                
                found_valid_space = False
                for space in container.spaces:
                    if space.can_fit_item(item_copy.dimensions):
                        pos = (space.x, space.y, space.z)
                        if container._is_valid_placement(item_copy, pos, item_copy.dimensions):
                            # Check temperature constraints again with stricter enforcement
                            if hasattr(item_copy, 'needs_insulation') and item_copy.needs_insulation and temp_handler:
                                if not temp_handler.check_temperature_constraints(item_copy, pos, container.dimensions):
                                    continue  # Try next space
                            
                            item_copy.position = pos
                            
                            # Explicitly set color for temperature-sensitive items that need insulation
                            if hasattr(item_copy, 'needs_insulation') and item_copy.needs_insulation:
                                item_copy.color = 'rgb(0, 128, 255)'  # Dark blue for temperature sensitive items
                            
                            container.items.append(item_copy)
                            container._update_spaces(pos, item_copy.dimensions, space)
                            
                            # Sort spaces again
                            sort_spaces_by_fitness(container)
                            
                            successful_packs += 1
                            placed = True
                            found_valid_space = True
                            break
                
                if found_valid_space:
                    break
            
            if not placed:
                failed_packs += 1
                unpacked_items.append(item_copy)
                
                # Store the reason for not packing
                container.unpacked_reasons[item_copy.name] = (
                    container._get_unpacking_reason(item_copy), item_copy
                )
                
                # Make sure temperature-sensitive items are correctly marked with special color in unpacked items
                if getattr(item_copy, 'temperature_sensitivity', None) and item_copy.temperature_sensitivity != 'N/A':
                    try:
                        temp_range = str(item_copy.temperature_sensitivity).replace('°C', '').split(' to ')
                        min_temp = float(temp_range[0])
                        max_temp = float(temp_range[1])
                        
                        # More strict temperature requirements (8-25°C) always need insulation, 
                        # regardless of route temperature
                        if min_temp > 5 and max_temp < 30:
                            item_copy.needs_insulation = True
                            item_copy.color = 'rgb(0, 128, 255)'  # Dark blue for temperature sensitive items
                    except (ValueError, IndexError):
                        pass
                
                # Show detailed reason for temperature-sensitive items
                if hasattr(item_copy, 'needs_insulation') and item_copy.needs_insulation:
                    reason = container.unpacked_reasons[item_copy.name][0]
                    logger.info(f"  ❌ Failed to place temperature-sensitive item {item_copy.name}")
                    logger.info(f"     Reason: {reason}")
    
    logger.info(f"\nFinal packing statistics:")
    logger.info(f"  Successfully packed: {successful_packs} items")
    logger.info(f"  Failed to pack: {failed_packs} items")
    
    if original_item_count is not None:
        logger.info(f"  Total items: {original_item_count} items")
    else:
        # Calculate total items from expanded_items if original_item_count wasn't passed
        total_items = len(best_genome.item_sequence) if best_genome else len(expanded_items)
        logger.info(f"  Total items: {total_items} items")
        
    # Display the container utilization as a percentage (multiplied by 100)
    # This prevents the 0.00% display issue by formatting correctly
    logger.info(f"  Container utilization: {container.volume_utilization:.2%}")
    
    # Print detailed unpacked item report
    if failed_packs > 0:
        logger.info("\nUnpacked items:")
        for name, (reason, item) in container.unpacked_reasons.items():
            temp_info = ""
            if hasattr(item, 'needs_insulation') and item.needs_insulation:
                temp_info = " (temperature-sensitive)"
            logger.info(f"  {name}{temp_info}: {reason}")
    
    # Update container metrics
    container._update_metrics()
    
    # Calculate and update volume utilization correctly
    total_packed_volume = sum(
        item.dimensions[0] * item.dimensions[1] * item.dimensions[2] 
        for item in container.items
    )
    container_volume = container.dimensions[0] * container.dimensions[1] * container.dimensions[2]
    container.volume_utilization = total_packed_volume / container_volume if container_volume > 0 else 0
    container.remaining_volume = container_volume - total_packed_volume
    
    # Log the actual volume utilization (display as percentage in logs)
    logger.info(f"  Container volume utilization (corrected): {container.volume_utilization:.2%}")
    
    # Store the unpacked items in the container for reporting
    container.unpacked_items = unpacked_items
    
    return container