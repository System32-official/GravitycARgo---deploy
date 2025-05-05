"""
Genetic algorithm implementation for container packing optimization.
"""
import random
from typing import List, Dict, Tuple, Any, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
from array import array
import json
import logging

from optigenix_module.models.container import EnhancedContainer
from optigenix_module.models.item import Item
from optigenix_module.utils.llm_connector import get_llm_client
from optigenix_module.optimization.temperature import TemperatureConstraintHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("packer")

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
                rotation_subseq = self.rotation_flags[start_idx:start_idx+seq_length]
                
                # Remove subsequence
                self.item_sequence = self.item_sequence[:start_idx] + \
                                    self.item_sequence[start_idx+seq_length:]
                self.rotation_flags = self.rotation_flags[:start_idx] + \
                                     self.rotation_flags[start_idx+seq_length:]
                
                # Insert at target location
                self.item_sequence = self.item_sequence[:target_idx] + \
                                    subsequence + \
                                    self.item_sequence[target_idx:]
                self.rotation_flags = self.rotation_flags[:target_idx] + \
                                     rotation_subseq + \
                                     self.rotation_flags[target_idx:]
        
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
    
    def __init__(self, container_dims, population_size=200, generations=150, route_temperature=None):
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
        
        # Initialize temperature constraint handler
        self.temp_handler = TemperatureConstraintHandler(route_temperature)
    
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
                    
                    logger.info(f"LLM Strategy: {strategy['operation_focus']} (rate: {strategy['mutation_rate_modifier']:.3f})")
                    logger.info(f"Explanation: {strategy['explanation']}")
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
        import numpy as np
        
        try:
            # Calculate metrics for LLM context
            avg_fitness = sum(g.fitness for g in population) / len(population) if population else 0
            best_fitness = max((g.fitness for g in population), default=0)
            fitness_variance = np.var([g.fitness for g in population]) if population else 0
            
            logger.info(f"\n{'='*20} DYNAMIC FITNESS WEIGHTS REQUEST {'='*20}")
            logger.info(f"Generation: {generation} | Best fitness: {best_fitness:.4f} | Average: {avg_fitness:.4f}")
            logger.info("Current Metrics:")
            logger.info(f"  Volume utilization: {current_metrics.get('volume_utilization', 0):.4f}")
            logger.info(f"  Contact ratio: {current_metrics.get('contact_ratio', 0):.4f}")
            logger.info(f"  Stability score: {current_metrics.get('stability_score', 0):.4f}")
            logger.info(f"  Weight balance: {current_metrics.get('weight_balance', 0):.4f}")
            logger.info(f"  Items packed ratio: {current_metrics.get('items_packed_ratio', 0):.4f}")
            
            # Create a prompt with current algorithm state
            prompt = f"""
            Return optimal fitness weights for a 3D bin packing genetic algorithm.
            Current metrics:
            - Generation: {generation}
            - Best fitness: {best_fitness:.4f}
            - Average fitness: {avg_fitness:.4f}
            - Fitness variance: {fitness_variance:.6f}
            - Current volume utilization: {current_metrics.get('volume_utilization', 0):.4f}
            - Current contact ratio: {current_metrics.get('contact_ratio', 0):.4f}
            - Current stability score: {current_metrics.get('stability_score', 0):.4f}
            - Current weight balance: {current_metrics.get('weight_balance', 0):.4f}
            - Items packed ratio: {current_metrics.get('items_packed_ratio', 0):.4f}

            Based on these metrics, provide a JSON object with these EXACT keys:
            {{
                "volume_utilization_weight": number, // Between 0.1 and 0.4
                "contact_ratio_weight": number,      // Between 0.2 and 0.5
                "stability_score_weight": number,    // Between 0.1 and 0.4
                "weight_balance_weight": number,     // Between 0.05 and 0.2
                "items_packed_ratio_weight": number, // Between 0.05 and 0.15
                "explanation": string                // Brief explanation of weights choice
            }}

            Guidelines for weight selection:
            - Sum of all weights must equal 1.0
            - Focus on volume_utilization and contact_ratio early in the optimization
            - Prioritize stability_score and weight_balance in later generations
            - For generations with low fitness variance, increase weight_balance to break plateaus
            - For generations with low volume_utilization, prioritize that component
            """
            
            # Use the global llm_client that's already initialized
            response = llm_client.generate(prompt)
            
            if not response:
                return None
                
            try:
                result = json.loads(response)
                required_keys = [
                    "volume_utilization_weight", "contact_ratio_weight", 
                    "stability_score_weight", "weight_balance_weight", 
                    "items_packed_ratio_weight", "explanation"
                ]
                
                # Validate response
                if not all(key in result for key in required_keys):
                    logger.error("LLM response missing required keys for fitness weights")
                    return None
                    
                # Ensure weights sum to approximately 1.0
                weights_sum = sum(result[key] for key in required_keys if key != "explanation")
                if abs(weights_sum - 1.0) > 0.01:
                    logger.warning(f"Weights don't sum to 1.0 (sum: {weights_sum}), normalizing")
                    factor = 1.0 / weights_sum
                    for key in required_keys:
                        if key != "explanation":
                            result[key] *= factor
                
                # Log the weights in a clean tabular format
                logger.info(f"\n{'='*20} DYNAMIC FITNESS WEIGHTS RECEIVED {'='*20}")
                logger.info("Weight values:")
                logger.info(f"  Volume utilization: {result['volume_utilization_weight']:.4f}")
                logger.info(f"  Contact ratio:     {result['contact_ratio_weight']:.4f}")
                logger.info(f"  Stability score:   {result['stability_score_weight']:.4f}")
                logger.info(f"  Weight balance:    {result['weight_balance_weight']:.4f}")
                logger.info(f"  Items packed:      {result['items_packed_ratio_weight']:.4f}")
                logger.info(f"Explanation: {result['explanation']}")
                
                return result
                
            except json.JSONDecodeError:
                logger.error("Failed to parse LLM response as JSON")
                return None
                
        except Exception as e:
            logger.error(f"Error getting dynamic fitness weights: {str(e)}")
            return None
            
        return None

    def optimize(self, items):
        """Optimize container packing using genetic algorithm with LLM-based adaptive mutation"""
        # Initialize population and variables
        logger.info(f"\n{'*'*70}")
        logger.info(f"STARTING GENETIC ALGORITHM WITH LLM INTEGRATION")
        logger.info(f"{'*'*70}")
        logger.info(f"Population size: {self.population_size}")
        logger.info(f"Max generations: {self.generations}")
        logger.info(f"Items to pack: {len(items)}")
        logger.info(f"Container dimensions: {self.container_dims}")
        logger.info(f"{'*'*70}\n")
        
        # Initialize with smart population strategies
        self.initialize_smart_population(items)
        population = self.population
        
        self.best_fitness = 0.0
        stagnation_counter = 0
        max_stagnation = 20  # Stop if no improvement after 15 generations
        
        # Default mutation strategy
        current_mutation_strategy = {
            "mutation_rate_modifier": 0.0,
            "operation_focus": "balanced",
            "explanation": "Initial default strategy"
        }
        logger.info(f"Initial mutation strategy: {current_mutation_strategy['operation_focus']} (default)")
        
        # Initialize metrics storage
        self.current_metrics = {}
        
        # Initialize dynamic fitness weights
        self.fitness_weights = None
        
        for generation in range(self.generations):
            previous_best = self.best_fitness
            
            logger.info(f"\n{'-'*40}")
            logger.info(f"GENERATION {generation + 1}/{self.generations}")
            logger.info(f"{'-'*40}")
            
            # Parallelize fitness evaluation
            logger.info(f"Evaluating fitness for {len(population)} solutions...")
            with ProcessPoolExecutor() as executor:
                # Submit all fitness evaluations
                future_to_genome = {executor.submit(self._evaluate_fitness, genome): genome 
                                  for genome in population}
                
                # Collect results as they complete
                for future in as_completed(future_to_genome):
                    genome = future_to_genome[future]
                    try:
                        genome.fitness = future.result()
                        
                        # Update best solution
                        if genome.fitness > self.best_fitness:
                            self.best_fitness = genome.fitness
                            self.best_solution = genome
                    except Exception as e:
                        logger.error(f"Fitness evaluation failed: {e}")
            
            # Check for improvement
            if self.best_fitness <= previous_best:
                stagnation_counter += 1
                improvement_status = "No improvement"
            else:
                stagnation_counter = 0
                improvement_status = "Improved"
            
            # Early stopping condition
            if stagnation_counter >= max_stagnation:
                logger.info(f"\nSTOPPING EARLY: No improvement for {max_stagnation} generations")
                break
            
            # Get dynamic fitness weights every 5 generations or when stagnation occurs
            if generation % 5 == 0 or stagnation_counter > 2:
                self.fitness_weights = self._get_dynamic_fitness_weights(
                    generation, population, self.current_metrics
                )
            
            # Get adaptive mutation strategy from LLM
            new_strategy = self._get_adaptive_mutation_strategy(
                generation, population, stagnation_counter
            )
            
            if new_strategy:
                logger.info(f"\nUPDATING MUTATION STRATEGY:")
                logger.info(f"Old: {current_mutation_strategy['operation_focus']} with modifier {current_mutation_strategy.get('mutation_rate_modifier', 0):.3f}")
                
                current_mutation_strategy = new_strategy
                
                logger.info(f"New: {current_mutation_strategy['operation_focus']} with modifier {current_mutation_strategy['mutation_rate_modifier']:.3f}")
            
            # Add elitism: keep the best individuals
            elite_count = max(1, int(self.population_size * self.elite_percentage))  # Keep top 15%
            
            # Selection and reproduction
            logger.info(f"Creating new population with elite count: {elite_count}")
            new_population = []
            
            # First add the elite individuals
            sorted_population = sorted(population, key=lambda x: x.fitness, reverse=True)
            new_population.extend(sorted_population[:elite_count])
            
            # Fill the rest with offspring
            while len(new_population) < self.population_size:
                parent1 = self._tournament_select(population)
                parent2 = self._tournament_select(population)
                child = self._crossover(parent1, parent2)
                
                # Apply adaptive mutation with current strategy
                child.mutate(
                    operation_focus=current_mutation_strategy["operation_focus"],
                    rate_modifier=current_mutation_strategy["mutation_rate_modifier"]
                )
                
                new_population.append(child)
                
            population = new_population
            
            # Print generation summary in a cleaner format
            avg_fitness = sum(g.fitness for g in population) / len(population)
            best_in_gen = max(g.fitness for g in population)
            
            logger.info(f"\nGENERATION {generation + 1} SUMMARY:")
            logger.info(f"Best fitness: {self.best_fitness:.4f} ({improvement_status})")
            logger.info(f"Best in generation: {best_in_gen:.4f} | Average: {avg_fitness:.4f}")
            logger.info(f"Stagnation counter: {stagnation_counter}")
            logger.info(f"Mutation strategy: {current_mutation_strategy['operation_focus']} (modifier: {current_mutation_strategy['mutation_rate_modifier']:.3f})")
            
            # Print current fitness weights in a readable format
            if self.fitness_weights:
                logger.info("Current fitness weights:")
                logger.info(f"  Volume: {self.fitness_weights['volume_utilization_weight']:.2f} | " +
                      f"Contact: {self.fitness_weights['contact_ratio_weight']:.2f} | " +
                      f"Stability: {self.fitness_weights['stability_score_weight']:.2f} | " +
                      f"Balance: {self.fitness_weights['weight_balance_weight']:.2f} | " +
                      f"Packed: {self.fitness_weights['items_packed_ratio_weight']:.2f}")
        
        logger.info(f"\n{'='*70}")
        logger.info(f"GENETIC ALGORITHM COMPLETED")
        logger.info(f"Best fitness achieved: {self.best_fitness:.4f}")
        logger.info(f"Generations run: {generation + 1}")
        logger.info(f"Total mutations applied: ~{generation * self.population_size}")
        logger.info(f"LLM strategy updates: ~{(generation + 1) // 5}")
        logger.info(f"{'='*70}\n")
        
        return self.best_solution

    def _evaluate_fitness(self, genome):
        """Enhanced fitness evaluation with dynamic weights from LLM"""
        container = EnhancedContainer(self.container_dims)
        
        # Set route temperature if available
        if self.route_temperature is not None:
            container.route_temperature = self.route_temperature
        
        # Sort spaces by their distance from the container origin for better packing
        def sort_spaces(container):
            container.spaces.sort(key=lambda space: (
                space.z,  # Prioritize lower heights first
                space.x**2 + space.y**2,  # Prefer spaces closer to origin
                -(space.width * space.height * space.depth)  # Prefer larger spaces
            ))
        
        # Make a local copy of items to avoid modifying the originals
        items_to_pack = [(item, rotation_flag) for item, rotation_flag in 
                         zip(genome.item_sequence, genome.rotation_flags)]
        
        # Pre-sort items by volume and weight for better initial packing
        items_to_pack.sort(key=lambda x: (
            -(x[0].dimensions[0] * x[0].dimensions[1] * x[0].dimensions[2]),  # Larger volume first
            -x[0].weight,  # Heavier items first
            not x[0].stackable  # Non-stackable items first
        ))
        
        # Pack items and track metrics
        total_contact_area = 0
        total_surface_area = 0
        gaps_penalty = 0
        
        for item, rotation_flag in items_to_pack:
            original_dims = item.dimensions
            item.dimensions = self._get_rotation(original_dims, rotation_flag)
            
            best_pos = None
            best_rot = None
            best_space = None
            best_score = float('-inf')
            
            # TEMPERATURE SENSITIVITY CHECK - using TemperatureConstraintHandler
            is_temperature_sensitive = False
            if hasattr(item, 'needs_insulation') and item.needs_insulation:
                is_temperature_sensitive = True
            
            # Try current rotation in all available spaces
            for space in container.spaces:
                # Skip spaces that aren't suitable for temperature-sensitive items
                if is_temperature_sensitive and hasattr(space, 'temperature_safe') and space.temperature_safe is False:
                    continue
                    
                if space.can_fit_item(item.dimensions):
                    pos = (space.x, space.y, space.z)
                    if container._is_valid_placement(item, pos, item.dimensions):
                        # WALL PROXIMITY CHECK using Temperature Handler
                        if is_temperature_sensitive:
                            if not self.temp_handler.check_temperature_constraints(item, pos, container.dimensions):
                                continue  # Skip positions that don't satisfy temperature constraints
                        
                        # Calculate placement score
                        contact_score = 0
                        gap_score = 0
                        
                        # Check contact with container walls
                        wall_contacts = 0
                        if pos[0] == 0 or pos[0] + item.dimensions[0] == container.dimensions[0]:
                            wall_contacts += 1
                        if pos[1] == 0 or pos[1] + item.dimensions[1] == container.dimensions[1]:
                            wall_contacts += 1
                        if pos[2] == 0:
                            wall_contacts += 1
                        
                        # Check contact with other items
                        for placed_item in container.items:
                            if container._has_surface_contact(pos, item.dimensions, placed_item):
                                overlap_area = container._calculate_overlap_area(
                                    (pos[0], pos[1], item.dimensions[0], item.dimensions[1]),
                                    (placed_item.position[0], placed_item.position[1],
                                     placed_item.dimensions[0], placed_item.dimensions[1])
                                )
                                contact_score += overlap_area
                        
                        # Check for small gaps
                        for gap_space in container.spaces:
                            if gap_space != space:
                                if (gap_space.width < 0.3 and gap_space.depth < 0.3) or \
                                   (gap_space.width < 0.3 and gap_space.height < 0.3) or \
                                   (gap_space.depth < 0.3 and gap_space.height < 0.3):
                                    gap_score -= gap_space.get_volume()
                        
                        # DIFFERENT SCORING STRATEGY BASED ON TEMPERATURE SENSITIVITY
                        if is_temperature_sensitive:
                            # Calculate central position score
                            center_x = container.dimensions[0] / 2
                            center_y = container.dimensions[1] / 2
                            item_center_x = pos[0] + item.dimensions[0]/2
                            item_center_y = pos[1] + item.dimensions[1]/2
                            
                            # Calculate distance from center (normalized 0-1)
                            distance_from_center = ((item_center_x - center_x)**2 + 
                                                   (item_center_y - center_y)**2) / (
                                                       (container.dimensions[0]/2)**2 + 
                                                       (container.dimensions[1]/2)**2)
                            
                            # Central position bonus (0-50 points)
                            central_bonus = 50 * (1 - distance_from_center)
                            
                            # Score formula for temperature-sensitive items
                            position_score = (
                                contact_score * 3 +      # Contact with other items is good
                                central_bonus +          # Central placement bonus
                                gap_score * 3            # Penalize small gaps
                            )
                        else:
                            # Score formula for regular items
                            position_score = (
                                contact_score * 2 +      # Contact with other items
                                wall_contacts * 1.5 +    # Wall contact bonus for regular items
                                gap_score * 3            # Penalize small gaps
                            )
                        
                        if position_score > best_score:
                            best_score = position_score
                            best_pos = pos
                            best_rot = item.dimensions
                            best_space = space
            
            if best_pos:
                item.position = best_pos
                item.dimensions = best_rot
                container.items.append(item)
                container._update_spaces(best_pos, best_rot, best_space)
                
                # Update metrics
                total_surface_area += 2 * (
                    item.dimensions[0] * item.dimensions[1] +
                    item.dimensions[1] * item.dimensions[2] +
                    item.dimensions[0] * item.dimensions[2]
                )
                
                # Update contact area
                for other_item in container.items[:-1]:  # Exclude current item
                    if container._has_surface_contact(item.position, item.dimensions, other_item):
                        overlap_area = container._calculate_overlap_area(
                            (item.position[0], item.position[1], 
                             item.dimensions[0], item.dimensions[1]),
                            (other_item.position[0], other_item.position[1],
                             other_item.dimensions[0], other_item.dimensions[1])
                        )
                        total_contact_area += overlap_area
                
                sort_spaces(container)
            
            # Restore original dimensions
            item.dimensions = original_dims
        
        # Calculate enhanced fitness components
        metrics = {}
        
        metrics['volume_utilization'] = (sum(
            item.dimensions[0] * item.dimensions[1] * item.dimensions[2] 
            for item in container.items
        ) / (container.dimensions[0] * container.dimensions[1] * container.dimensions[2]))
        
        metrics['contact_ratio'] = total_contact_area / (total_surface_area + 1e-6) if total_surface_area > 0 else 0
        
        try:
            metrics['stability_score'] = sum(
                container._calculate_stability_score(item, item.position, item.dimensions)
                for item in container.items
            ) / len(container.items) if container.items else 0
        except (AttributeError, ZeroDivisionError):
            metrics['stability_score'] = 0
        
        try:
            metrics['weight_balance'] = container._calculate_weight_balance_score()
        except AttributeError:
            metrics['weight_balance'] = 0
            
        metrics['items_packed_ratio'] = len(container.items) / len(genome.item_sequence)
        
        # Cache metrics for current genome for use in adaptive mutation
        if hasattr(self, 'current_metrics'):
            self.current_metrics = metrics.copy()
        
        # Use dynamic weights if available, otherwise fall back to default weights
        if hasattr(self, 'fitness_weights') and self.fitness_weights:
            fitness = (
                metrics['volume_utilization'] * self.fitness_weights['volume_utilization_weight'] +
                metrics['contact_ratio'] * self.fitness_weights['contact_ratio_weight'] +
                metrics['stability_score'] * self.fitness_weights['stability_score_weight'] +
                metrics['weight_balance'] * self.fitness_weights['weight_balance_weight'] +
                metrics['items_packed_ratio'] * self.fitness_weights['items_packed_ratio_weight']
            )
        else:
            # Default weights if no dynamic weights available
            fitness = (
                metrics['volume_utilization'] * 0.25 +
                metrics['contact_ratio'] * 0.35 +
                metrics['stability_score'] * 0.25 +
                metrics['weight_balance'] * 0.1 +
                metrics['items_packed_ratio'] * 0.05
            )
        
        # Additional penalties/bonuses for temperature-sensitive item placement - using TemperatureHandler
        temp_items = [i for i in container.items if getattr(i, 'needs_insulation', False)]
        if temp_items:
            # Calculate average distance from walls for temperature items
            total_dist = 0
            for item in temp_items:
                x, y, z = item.position
                w, d, h = item.dimensions
                min_dist = min(
                    x,                                   # Distance from left wall
                    y,                                   # Distance from front wall
                    container.dimensions[0] - (x + w),   # Distance from right wall
                    container.dimensions[1] - (y + d),   # Distance from back wall
                    z,                                   # Distance from bottom
                    container.dimensions[2] - (z + h)    # Distance from top
                )
                total_dist += min_dist
            
            avg_wall_dist = total_dist / len(temp_items) if temp_items else 0
            
            # Calculate bonus based on temp handler
            temp_bonus = min(0.1, avg_wall_dist / 2.0)  # Max bonus at 50cm average
            fitness += temp_bonus
        
        return fitness

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
        child_rotations = [
            parent1.rotation_flags[i] if random.random() < 0.5 
            else parent2.rotation_flags[i]
            for i in range(size)
        ]
        
        child = PackingGenome(child_sequence)
        child.rotation_flags = child_rotations
        return child

    def _get_rotation(self, dims, flag):
        """Get dimensions after rotation based on flag"""
        l, w, h = dims
        rotations = [
            (l, w, h), (l, h, w), (w, l, h),
            (w, h, l), (h, l, w), (h, w, l)
        ]
        return rotations[flag]

    def initialize_smart_population(self, items):
        """Initialize population with smart strategies for better starting solutions"""
        population = []
        
        # Calculate item properties for smart initialization
        total_volume = sum(i.dimensions[0] * i.dimensions[1] * i.dimensions[2] for i in items)
        container_volume = self.container_dims[0] * self.container_dims[1] * self.container_dims[2]
        avg_item_volume = total_volume / len(items)
        
        # Strategy 1: Volume-based sorting (30% of population)
        volume_count = int(self.population_size * 0.3)
        for _ in range(volume_count):
            sorted_items = sorted(items.copy(), 
                key=lambda x: x.dimensions[0] * x.dimensions[1] * x.dimensions[2],
                reverse=True)
            genome = PackingGenome(sorted_items)
            # Smart rotation initialization for large items
            for i, item in enumerate(sorted_items):
                if item.dimensions[0] * item.dimensions[1] * item.dimensions[2] > avg_item_volume:
                    best_rot = 0
                    min_height = float('inf')
                    for rot in range(6):
                        dims = self._get_rotation(item.dimensions, rot)
                        if dims[2] < min_height and all(d <= max_d for d, max_d in zip(dims, self.container_dims)):
                            min_height = dims[2]
                            best_rot = rot
                    genome.rotation_flags[i] = best_rot
            population.append(genome)
            
        # Strategy 2: Layer-based grouping (30% of population)
        layer_count = int(self.population_size * 0.3)
        for _ in range(layer_count):
            # Group items by similar heights
            items_copy = items.copy()
            items_copy.sort(key=lambda x: x.dimensions[2])
            genome = PackingGenome(items_copy)
            # Initialize rotations to minimize height variations within layers
            current_height = 0
            current_layer = []
            for i, item in enumerate(items_copy):
                if item.dimensions[2] > current_height * 1.2:  # Allow 20% variance in layer height
                    # Start new layer
                    current_height = item.dimensions[2]
                    current_layer = []
                current_layer.append(i)
                # Try to maintain consistent height within layer
                best_rot = 0
                min_diff = float('inf')
                for rot in range(6):
                    dims = self._get_rotation(item.dimensions, rot)
                    if abs(dims[2] - current_height) < min_diff and all(d <= max_d for d, max_d in zip(dims, self.container_dims)):
                        min_diff = abs(dims[2] - current_height)
                        best_rot = rot
                genome.rotation_flags[i] = best_rot
            population.append(genome)
            
        # Strategy 3: Weight and stability based (20% of population)
        weight_count = int(self.population_size * 0.2)
        for _ in range(weight_count):
            # Sort by weight and stability requirements
            sorted_items = sorted(items.copy(), 
                key=lambda x: (x.weight, x.fragility != 'HIGH', x.stackable),
                reverse=True)
            genome = PackingGenome(sorted_items)
            # Initialize rotations focusing on stability
            for i, item in enumerate(sorted_items):
                if item.fragility == 'HIGH' or item.weight > 100:
                    # Find rotation with largest base area for stability
                    best_rot = 0
                    max_base = 0
                    for rot in range(6):
                        dims = self._get_rotation(item.dimensions, rot)
                        base_area = dims[0] * dims[1]
                        if base_area > max_base and all(d <= max_d for d, max_d in zip(dims, self.container_dims)):
                            max_base = base_area
                            best_rot = rot
                    genome.rotation_flags[i] = best_rot
            population.append(genome)
            
        # Strategy 4: Random with smart constraints (20% of population)
        random_count = self.population_size - len(population)
        for _ in range(random_count):
            shuffled_items = items.copy()
            random.shuffle(shuffled_items)
            genome = PackingGenome(shuffled_items)
            # Add some smart constraints even to random solutions
            for i, item in enumerate(shuffled_items):
                if not item.stackable or item.fragility == 'HIGH':
                    # Prefer orientations with lower height for unstackable items
                    best_rot = 0
                    min_height = float('inf')
                    for rot in range(6):
                        dims = self._get_rotation(item.dimensions, rot)
                        if dims[2] < min_height and all(d <= max_d for d, max_d in zip(dims, self.container_dims)):
                            min_height = dims[2]
                            best_rot = rot
                    genome.rotation_flags[i] = best_rot
            population.append(genome)
            
        # Set initial population
        self.population = population
        logger.info(f"Created smart initial population with {len(population)} diverse solutions")