"""Gemini LLM client connector for adaptive genetic algorithm"""
import os
import json
import time
import logging
import random
import re
import concurrent.futures
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from functools import lru_cache
import google.generativeai as genai
# Ensure FinishReason is NOT imported directly if it causes issues
from google.generativeai.types import HarmCategory, HarmBlockThreshold # MODIFIED: Keep only necessary imports

# Load environment variables
load_dotenv()

# Global singleton instance
_GLOBAL_CLIENT_INSTANCE = None

class GeminiClient:
    """Gemini client for Google Generative AI using singleton pattern"""
    def __init__(self, api_key=None, log_file="llm_strategies.log"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            print("[WARNING] No Gemini API key found. LLM features will be disabled.")
            self.enabled = False
            return
        self.enabled = True
        self.model_name = "gemini-2.5-flash-preview-05-20"  # Updated to use the latest flash model
        
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            print(f"\\n{'='*50}")
            print(f"[OK] LLM Connector initialized with Gemini AI")
            print(f"Model: {self.model_name}")
            print(f"{'='*50}\\n")
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        except Exception as e:
            print(f"[WARNING] Failed to initialize Gemini client: {e}")
            self.enabled = False
            return
            
        self.strategy_history = []  # Initialize strategy history
    
        # Set up logging
        self.logger = logging.getLogger("llm_connector")
        self.logger.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.logger.addHandler(file_handler)
    
    def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """Generate with Gemini model"""
        if not self.enabled:
            fallback = self._get_fallback_strategy()
            return json.dumps(fallback)
            
        print(f"\\n{'='*60}")
        print(f"🧠 QUERYING LLM: Asking Gemini for adaptive mutation strategy...")
        print(f"{'='*60}")
        
        # Print abbreviated prompt
        print("\n📝 PROMPT SUMMARY:")
        prompt_lines = prompt.strip().split('\n')
        if len(prompt_lines) > 10:
            for line in prompt_lines[:5]:
                print(f"  {line.strip()}")
            print("  ...")
            for line in prompt_lines[-3:]:
                print(f"  {line.strip()}")
        else:
            for line in prompt_lines:
                print(f"  {line.strip()}")
        
        start_time = time.time()
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                print("\\\\n⏳ WAITING FOR RESPONSE ", end="", flush=True)
                
                # Configure generation settings
                generation_config = genai.types.GenerationConfig(
                    temperature=min(1.0, max(0.0, temperature)),
                    max_output_tokens=max_tokens
                )
                
                # Add system instruction for JSON response
                enhanced_prompt = f"""You are a helpful AI assistant that ALWAYS responds in valid JSON format. Your responses should contain ONLY the JSON object, with no additional text, explanations, or markdown.

{prompt}"""
                
                response = self.model.generate_content(
                    enhanced_prompt,
                    generation_config=generation_config,
                    safety_settings=self.safety_settings
                )
                
                # Robustly check response content and safety blocking
                if response.candidates:
                    candidate = response.candidates[0]                    # Using integer values for finish_reason comparison to avoid enum import issues
                    # STOP=1, MAX_TOKENS=2, SAFETY=3, RECITATION=4, OTHER=5
                    finish_reason_value = int(candidate.finish_reason)
                    
                    if finish_reason_value == 3:  # SAFETY
                        block_reason_msg = f"Content blocked due to: SAFETY (finish_reason={finish_reason_value}). Safety Ratings: {candidate.safety_ratings}"
                        if response.prompt_feedback and response.prompt_feedback.block_reason:
                            block_reason_msg = f"Prompt blocked due to: {response.prompt_feedback.block_reason}. {block_reason_msg}"
                        self.logger.warning(f"Safety block encountered. Candidate: {candidate}, Prompt Feedback: {response.prompt_feedback}")
                        raise Exception(f"Gemini API response issue: {block_reason_msg}")
                    
                    elif finish_reason_value == 2:  # MAX_TOKENS
                        # Log the full candidate for detailed inspection if MAX_TOKENS is hit
                        actual_content = ""
                        if hasattr(candidate.content, 'parts') and candidate.content.parts and hasattr(candidate.content.parts[0], 'text'):
                            actual_content = candidate.content.parts[0].text
                        self.logger.warning(f"MAX_TOKENS encountered. Actual content before cutoff (if any): '{actual_content}'. Candidate: {candidate}")
                        raise Exception(f"Gemini API response issue: MAX_TOKENS (finish_reason={finish_reason_value}). The response was cut off. Full candidate: {candidate}")

                    elif finish_reason_value == 1:  # STOP
                        if hasattr(candidate.content, 'parts') and candidate.content.parts and hasattr(candidate.content.parts[0], 'text'):
                            content = candidate.content.parts[0].text.strip()
                            if not content: # Check if stripped content is empty
                                self.logger.warning(f"Finish reason STOP but extracted text content is empty. Candidate: {candidate}")
                                raise Exception(f"Gemini API response issue: Finish reason STOP (value={finish_reason_value}) but extracted text is empty. Full candidate: {candidate}")
                            
                            end_time = time.time()
                            print(f"\\n[OK] RESPONSE RECEIVED ({end_time - start_time:.2f}s)")
                            print(f"{'='*60}")
                            return content
                        else: # No parts or no text attribute
                            self.logger.warning(f"Finish reason STOP but no valid content parts or text attribute. Candidate: {candidate}")
                            raise Exception(f"Gemini API response issue: Finish reason STOP (value={finish_reason_value}) but no text content found in parts. Full candidate: {candidate}")
                    else:
                        # Handle other finish reasons like RECITATION (4), OTHER (5), etc.
                        # It's good practice to log the actual value of finish_reason if it's unexpected
                        self.logger.warning(f"Unhandled finish reason value: {finish_reason_value}. Candidate: {candidate}")
                        raise Exception(f"Gemini API response issue: Unhandled finish reason '{finish_reason_value}'. Full candidate: {candidate}")

                elif response.prompt_feedback and response.prompt_feedback.block_reason:
                    # This handles cases where the prompt itself was blocked and no candidates were generated
                    raise Exception(f"Gemini API prompt issue: Prompt blocked due to {response.prompt_feedback.block_reason}. Safety Ratings: {response.prompt_feedback.safety_ratings}")
                else:
                    # No candidates and no prompt feedback block reason, this is an unexpected state
                    raise Exception(f"Empty or malformed response from Gemini API (no candidates or prompt feedback block reason). Full response: {response}")
                    
            except Exception as e:
                error_msg = str(e)
                print(f"\n[WARNING] Retry {attempt + 1}/{max_retries} after error: {error_msg}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    print(f"\n❌ ERROR: Gemini API request failed after {max_retries} attempts: {error_msg}")
                    print(f"{'='*60}")
                    fallback = self._get_fallback_strategy()
                    return json.dumps(fallback)
        
        # This should never be reached, but just in case
        fallback = self._get_fallback_strategy()
        return json.dumps(fallback)

    def _clean_json_response(self, response: str) -> dict:
        """Clean and parse JSON response from Gemini"""
        try:
            # Remove markdown code blocks if present
            cleaned = re.sub(r'```json\s*|\s*```', '', response.strip())
            
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # Try parsing the cleaned response directly
                return json.loads(cleaned)
                
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"[WARNING] JSON parsing failed: {e}")
            return self._get_fallback_strategy()

    def _get_fallback_strategy(self) -> dict:
        """Return a fallback mutation strategy when LLM is unavailable"""
        strategies = [
            {
                "mutation_rate_modifier": 0.05,
                "operation_focus": "balanced",
                "explanation": "Fallback strategy: Balanced approach with slightly increased exploration"
            },
            {
                "mutation_rate_modifier": -0.02,
                "operation_focus": "rotation", 
                "explanation": "Fallback strategy: Focus on rotation optimization"
            },
            {
                "mutation_rate_modifier": 0.1,
                "operation_focus": "swap",
                "explanation": "Fallback strategy: Increased item sequence mutations"
            }
        ]
        return random.choice(strategies)

    @lru_cache(maxsize=32)
    def _get_strategy_for_state(self, state_hash: str, problem_signature: str) -> str:
        """Cache strategies for similar container states to reduce API calls"""
        # Create a prompt based on the state hash and problem signature
        prompt = f"""
        Based on the following container state and problem signature, suggest an adaptive mutation strategy:
        State Hash: {state_hash}
        Problem Signature: {problem_signature}
        
        Respond with a JSON object containing:
        1. mutation_rate_modifier: A float between -0.5 and 0.5 to adjust the base mutation rate
        2. operation_focus: One of "balanced", "rotation", "swap" or "position"
        3. explanation: A brief explanation of the strategy
        """
        return self.generate(prompt)

    def get_batch_strategies(self, items=None, container=None, population_metrics=None, batch_size: int = 5) -> list:
        """Get multiple mutation strategies at once to reduce API calls
        
        Args:
            items: List of items to pack (optional, for compatibility)
            container: Container specifications (optional, for compatibility)
            population_metrics: Population metrics for strategy generation
            batch_size: Number of strategies to generate
        """
        # Use population_metrics if provided, otherwise use items/container info
        if population_metrics is None and items is not None:
            # Placeholder for logic to derive population_metrics from items/container
            # For now, assume population_metrics is correctly formed or [] if not available.
            population_metrics = [] # Default to empty if not otherwise set
            
        batch_prompt = self._create_batch_prompt(population_metrics or [], batch_size)
        raw_response_str = self.generate(batch_prompt)
        
        try:
            parsed_response = self._clean_json_response(raw_response_str)

            if "strategies" in parsed_response and isinstance(parsed_response["strategies"], list):
                generated_strategies = parsed_response["strategies"]
                
                # Ensure each strategy is valid, otherwise replace with fallback
                validated_strategies = []
                for strat in generated_strategies:
                    if self._validate_strategy(strat): # Assuming _validate_strategy exists and is suitable
                        validated_strategies.append(strat)
                    else:
                        print(f"[WARNING] Invalid strategy received in batch, using fallback: {strat}")
                        validated_strategies.append(self._get_fallback_strategy())

                if len(validated_strategies) >= batch_size:
                    return validated_strategies[:batch_size]
                else:
                    num_needed = batch_size - len(validated_strategies)
                    return validated_strategies + [self._get_fallback_strategy() for _ in range(num_needed)]
            else:
                # This case handles if parsed_response is already a single fallback strategy (dict)
                # or if 'strategies' key is missing/invalid.
                if isinstance(parsed_response, dict) and "mutation_rate_modifier" in parsed_response: # It's a single fallback
                     print(f"[WARNING] Batch strategy generation resulted in a single fallback strategy. Expected list.")
                else:
                    print(f"[WARNING] Batch strategy response missing 'strategies' list or invalid structure. Response: {parsed_response}")
                
        except Exception as e:
            print(f"❌ Error processing batch strategies response: {e}")
            
        # Fallback if try block fails, doesn't return, or structure is unexpected
        return [self._get_fallback_strategy() for _ in range(batch_size)]

    def _create_batch_prompt(self, population_metrics: list, batch_size: int) -> str:
        """Create a prompt for generating multiple strategies"""
        # Ensure population_metrics is a list for slicing
        if isinstance(population_metrics, dict):
            population_metrics = [population_metrics]
        elif not isinstance(population_metrics, list):
            population_metrics = []
            
        prompt = f"""
        Generate {batch_size} different mutation strategies for a genetic algorithm packing optimization.
        
        Population metrics: {json.dumps(population_metrics[:5]) if population_metrics else "No current metrics"}
        
        Return a JSON object with this structure:
        {{
            "strategies": [
                {{
                    "mutation_rate_modifier": float between -0.5 and 0.5,
                    "operation_focus": "balanced" | "rotation" | "swap" | "position",
                    "explanation": "brief explanation"
                }},
                ...
            ]
        }}
        """
        return prompt

    def _create_progressive_prompt(self, base_prompt: str, generation: int) -> str:
        """Create a prompt that focuses on different aspects based on generation"""
        early_focus = "focus on finding valid placements and exploring the solution space"
        mid_focus = "focus on optimizing space utilization and wall contacts"
        late_focus = "focus on fine-tuning the solution with minimal adjustments"
        
        if generation < 10:
            focus = early_focus
        elif generation < 30:
            focus = mid_focus
        else:
            focus = late_focus
            
        return f"{base_prompt}\n\nFor this generation ({generation}), {focus}."

    def generate_streaming(self, prompt: str, callback=None) -> str:
        """Generate with streaming response (adapted for Gemini)"""
        if not self.enabled:
            fallback = self._get_fallback_strategy()
            result = json.dumps(fallback)
            if callback:
                callback(result)
            return result
        
        # Note: Gemini streaming works differently than other APIs
        # For now, we'll use regular generation and simulate streaming
        print("🔄 Note: Gemini streaming adapted to regular generation")
        result = self.generate(prompt)
        
        if callback:
            callback(result)
        
        return result

    def record_strategy_performance(self, strategy: dict, performance: dict) -> None:
        """Record strategy performance for adaptive learning"""
        timestamp = time.time()
        
        record = {
            "timestamp": timestamp,
            "strategy": strategy,
            "performance": performance
        }
        
        self.strategy_history.append(record)
        
        # Keep only recent history (last 100 entries)
        if len(self.strategy_history) > 100:
            self.strategy_history = self.strategy_history[-100:]
        
        # Log the performance
        self.logger.info(f"Strategy performance recorded: {strategy.get('name', 'Unknown')} -> {performance}")

    def evaluate_strategies_concurrently(self, strategies: list, items: list, container: dict) -> list:
        """Evaluate multiple strategies concurrently"""
        def evaluate_single_strategy(strategy):
            """Evaluate a single strategy"""
            try:
                # Simulate strategy evaluation
                start_time = time.time()
                
                # Mock evaluation based on strategy parameters
                base_fitness = random.uniform(0.3, 0.9)
                
                # Adjust based on strategy focus
                focus = strategy.get("operation_focus", "balanced")
                if focus == "rotation":
                    fitness = base_fitness + random.uniform(-0.1, 0.15)
                elif focus == "swap":
                    fitness = base_fitness + random.uniform(-0.15, 0.1)
                else:
                    fitness = base_fitness
                
                fitness = max(0.0, min(1.0, fitness))
                execution_time = time.time() - start_time
                
                return {
                    "fitness": fitness,
                    "execution_time": execution_time,
                    "items_packed": random.randint(len(items)//2, len(items))
                }
            except Exception as e:
                return {"fitness": 0.0, "execution_time": 1.0, "error": str(e)}
        
        # Use ThreadPoolExecutor for concurrent evaluation
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(strategies))) as executor:
            future_to_strategy = {executor.submit(evaluate_single_strategy, strategy): strategy 
                                for strategy in strategies}
            
            for future in concurrent.futures.as_completed(future_to_strategy):
                strategy = future_to_strategy[future]
                try:
                    result = future.result()
                    results.append((strategy, result))
                except Exception as e:
                    print(f"Strategy evaluation failed: {e}")
                
        return sorted(results, key=lambda x: x[1].get("fitness", 0), reverse=True)

    def _validate_strategy(self, strategy: dict) -> bool:
        """Validate that a strategy has all required fields and valid values"""
        if not isinstance(strategy, dict):
            return False
            
        required_fields = ["mutation_rate_modifier", "operation_focus"]
        
        if not all(field in strategy for field in required_fields):
            return False
            
        # Validate mutation_rate_modifier is within reasonable bounds
        modifier = strategy.get("mutation_rate_modifier")
        if not isinstance(modifier, (int, float)) or not -0.5 <= modifier <= 0.5:
            return False
            
        # Validate operation_focus
        valid_focuses = ["balanced", "rotation", "swap", "position"]
        if strategy.get("operation_focus") not in valid_focuses:
            return False
            
        return True

    def _send_feedback_to_llm(self, performance_data: dict) -> str:
        """Send feedback about strategy performance to LLM for learning"""
        if not self.enabled:
            return "LLM not enabled"
        
        feedback_prompt = f"""
        Based on the following performance data, provide insights for improving future strategies:
        
        Performance Data: {json.dumps(performance_data, indent=2)}
        
        Respond with a JSON object containing:
        {{
            "insights": "key insights from the performance data",
            "recommendations": "recommendations for future strategies",
            "focus_areas": ["area1", "area2", "area3"]
        }}
        """
        
        try:
            response = self.generate(feedback_prompt)
            return response
        except Exception as e:
            print(f"[WARNING] Feedback sending failed: {e}")
            return json.dumps({
                "insights": "Unable to generate insights due to API error",
                "recommendations": "Continue with current approach",
                "focus_areas": ["stability", "exploration", "exploitation"]
            })

    def _extract_generation_from_prompt(self, prompt: str) -> int:
        """Extract generation number from prompt if present"""
        match = re.search(r'generation\s+(\d+)', prompt.lower())
        return int(match.group(1)) if match else 0

    async def generate_async(self, prompt: str, **kwargs) -> str:
        """Async wrapper for generate method (Gemini is synchronous by nature)"""
        # Gemini API is synchronous, so we'll wrap it in async
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Run in thread pool to avoid blocking
        return await loop.run_in_executor(None, self.generate, prompt)

    def ensure_temperature_constraints(self, temperature=None, context=None):
        """
        Ensure temperature constraints are properly initialized and applied
        
        Args:
            temperature: Float temperature value to constrain (0.0-1.0)
            context: Dictionary containing optimization context (items, container, etc.)
            
        Returns:
            float or dict: Constrained temperature value or information about applied constraints
        """
        # If a temperature value is provided, constrain it and return
        if temperature is not None:
            if isinstance(temperature, (int, float)):
                return max(0.0, min(1.0, float(temperature)))
            return 0.7  # Default safe value
        
        # Get route temperature from environment (for context processing)
        route_temp = float(os.environ.get("ROUTE_TEMPERATURE", 25.0))
        print(f"LLM Client: Using ROUTE_TEMPERATURE={route_temp}°C")
        
        # If we have a context with items, process temperature-related aspects
        if context and isinstance(context, dict) and 'items' in context:
            try:
                # Process any temperature-sensitive items
                temp_sensitive_items = []
                for item in context['items']:
                    if isinstance(item, dict):
                        # Check for temperature-related properties
                        if any(key in item for key in ['temperature', 'temp_sensitive', 'fragile']):
                            temp_sensitive_items.append(item.get('id', 'unknown'))
                
                return {
                    "route_temperature": route_temp,
                    "temperature_sensitive_items": temp_sensitive_items,
                    "constraints_applied": True
                }
            except Exception as e:
                print(f"[WARNING] Temperature constraint processing error: {e}")
                return {"route_temperature": route_temp, "constraints_applied": False}
        
        return {"route_temperature": route_temp, "constraints_applied": True}


def get_llm_client() -> GeminiClient:
    """Get the global LLM client instance (singleton pattern)"""
    global _GLOBAL_CLIENT_INSTANCE
    
    if _GLOBAL_CLIENT_INSTANCE is None:
        _GLOBAL_CLIENT_INSTANCE = GeminiClient()
    
    return _GLOBAL_CLIENT_INSTANCE
