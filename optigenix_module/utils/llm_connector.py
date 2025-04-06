"""Groq LLM client connector for adaptive genetic algorithm"""
import os
import json
import requests
import time
import sys
import random  # Add this missing import
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from functools import lru_cache
import asyncio
import aiohttp
import concurrent.futures
import logging

# Load environment variables
load_dotenv()

class GroqClient:
    """Simple client for Groq Cloud API"""
    
    def __init__(self, api_key=None, log_file="llm_strategies.log"):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            print("⚠️  Warning: No Groq API key found. LLM features will be disabled.")
            self.enabled = False
            return
            
        self.enabled = True
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        print(f"\n{'='*50}")
        print(f"✅ LLM Connector initialized with Groq Cloud")
        print(f"{'='*50}\n")
        self.session = requests.Session()  # Create persistent session
        self.strategy_history = []  # Initialize strategy history
    
        # Set up logging
        self.logger = logging.getLogger("llm_connector")
        self.logger.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.logger.addHandler(file_handler)
    
    def generate(self, prompt: str, max_tokens: int = 300) -> str:
        """Generate with model fallback for faster responses"""
        models = [
            "llama-3.3-70b-versatile",  # Try faster model first
            "llama-3.3-70b-specdec"  # Fallback to more powerful model if needed
        ]
        
        for model in models:
            try:
                # Attempt with current model
                result = self._generate_with_model(prompt, model, max_tokens)
                # If successful, return result
                return result
            except Exception as e:
                print(f"Model {model} failed: {e}, trying next model")
                
        # All models failed, use fallback
        return self._get_fallback_strategy()

    def _generate_with_model(self, prompt: str, model: str, max_tokens: int) -> str:
        """Generate text from prompt using Groq Cloud API"""
        if not self.enabled:
            return self._get_fallback_strategy()
            
        # Add system prompt to enforce JSON response
        data = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant that ALWAYS responds in valid JSON format. Your responses should contain ONLY the JSON object, with no additional text, explanations, or markdown."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3  # Lower temperature for more consistent JSON formatting
        }
        
        print(f"\n{'='*60}")
        print(f"🧠 QUERYING LLM: Asking Groq Cloud for adaptive mutation strategy...")
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
        
        spinner = ['⣾', '⣷', '⣯', '⣟', '⡿', '⢿', '⣻', '⣽']
        idx = 0
        start_time = time.time()
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                print("\n⏳ WAITING FOR RESPONSE ", end="", flush=True)
                # Use session instead of requests directly
                response = self.session.post(
                    self.api_url,
                    headers=self.headers,
                    json=data,
                    timeout=30
                )
                
                elapsed_time = time.time() - start_time
                print(f"\r✅ RESPONSE RECEIVED in {elapsed_time:.2f} seconds    ")
                
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # Try to clean and parse the response
                cleaned_content = self._clean_json_response(content)
                
                print("\n📊 LLM RESPONSE:")
                try:
                    parsed = json.loads(cleaned_content)
                    print(json.dumps(parsed, indent=2))
                    print(f"\n{'='*60}\n")
                    return cleaned_content
                except json.JSONDecodeError:
                    print(f"\n⚠️  WARNING: Invalid JSON response, using fallback")
                    print(f"\n{'='*60}\n")
                    return self._get_fallback_strategy()
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"\n⚠️ Retry {attempt+1}/{max_retries} after error: {e}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    print(f"\n❌ ERROR: Groq API request failed after {max_retries} attempts: {e}")
                    print(f"\n{'='*60}\n")
                    return self._get_fallback_strategy()
            
    def _clean_json_response(self, content: str) -> str:
        """Clean up the LLM response to extract valid JSON"""
        # Remove any markdown code block markers
        content = content.replace("```json", "").replace("```", "")
        
        # Try to find JSON object between { and }
        start = content.find('{')
        end = content.rfind('}')
        
        if start >= 0 and end > start:
            content = content[start:end+1]
            
        # Remove any trailing commas before closing braces/brackets
        content = content.replace(",]", "]").replace(",}", "}")
        
        # Handle common formatting issues
        content = content.replace("'", '"')  # Replace single quotes with double quotes
        content = content.strip()  # Remove whitespace
        
        return content

    def _get_fallback_strategy(self) -> str:
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
        return json.dumps(random.choice(strategies))

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
        2. operation_focus: One of "balanced", "rotation", "swap", or "position"
        3. explanation: A brief explanation of the strategy
        """
        return self.generate(prompt)

    def get_batch_strategies(self, population_metrics: list, batch_size: int = 5) -> list:
        """Get multiple mutation strategies at once to reduce API calls"""
        batch_prompt = self._create_batch_prompt(population_metrics, batch_size)
        response = self.generate(batch_prompt)
        
        try:
            strategies = json.loads(response)
            if "strategies" in strategies and isinstance(strategies["strategies"], list):
                return strategies["strategies"]
        except (json.JSONDecodeError, KeyError):
            pass
            
        # Fallback: Generate individual strategies
        return [json.loads(self._get_fallback_strategy()) for _ in range(batch_size)]

    def _create_progressive_prompt(self, base_prompt: str, generation: int) -> str:
        """Create a prompt that focuses on different aspects based on generation"""
        early_focus = "focus on finding valid placements and exploring the solution space"
        mid_focus = "focus on optimizing space utilization and wall contacts"
        late_focus = "focus on fine-tuning the solution with minimal adjustments"
        
        if generation < 30:
            focus = early_focus
        elif generation < 70:
            focus = mid_focus
        else:
            focus = late_focus
        
        return f"{base_prompt}\n\nAt generation {generation}, please {focus}."

    def generate_streaming(self, prompt: str, model: str = "llama-3.3-70b-specdec", max_tokens: int = 300):
        """Stream response from the LLM to start processing earlier"""
        if not self.enabled:
            return self._get_fallback_strategy()
            
        # Add system prompt to enforce JSON response
        data = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant that ALWAYS responds in valid JSON format. Your responses should contain ONLY the JSON object, with no additional text, explanations, or markdown."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,  # Lower temperature for more consistent JSON formatting
            "stream": True  # Enable streaming
        }
        
        # Adjust temperature based on optimization phase
        current_generation = self._extract_generation_from_prompt(prompt)
        max_generations = 100  # Estimate
        
        if current_generation < max_generations * 0.3:
            data["temperature"] = 0.5  # Early: More exploration
        elif current_generation < max_generations * 0.7:
            data["temperature"] = 0.3  # Middle: Balanced
        else:
            data["temperature"] = 0.1  # Late: More exploitation
        
        # Clear terminal and print header
        print("\033c", end="")  # Clear screen
        print(f"\n{'='*78}")
        print(f"🔄 LIVE LLM STREAM | Model: {model} | Temperature: {data['temperature']:.2f}")
        print(f"{'='*78}")
        
        # Print abbreviated prompt in a box
        print("\n📝 PROMPT SUMMARY:")
        print(f"┌{'─'*76}┐")
        prompt_lines = prompt.strip().split('\n')
        if len(prompt_lines) > 8:
            for line in prompt_lines[:4]:
                truncated = line.strip()[:70] + ("..." if len(line.strip()) > 70 else "")
                print(f"│ {truncated:<74} │")
            print(f"│ {'...':<74} │")
            for line in prompt_lines[-3:]:
                truncated = line.strip()[:70] + ("..." if len(line.strip()) > 70 else "")
                print(f"│ {truncated:<74} │")
        else:
            for line in prompt_lines:
                truncated = line.strip()[:70] + ("..." if len(line.strip()) > 70 else "")
                print(f"│ {truncated:<74} │")
        print(f"└{'─'*76}┘")
        
        print(f"\n{'⏳'} STREAMING RESPONSE... \n")
        print(f"┌{'─'*76}┐")
        
        start_time = time.time()
        accumulated_content = ""
        accumulated_json = ""
        json_complete = False
        open_braces = 0
        close_braces = 0
        
        try:
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    response = self.session.post(
                        self.api_url,
                        headers=self.headers,
                        json=data,
                        timeout=30,
                        stream=True
                    )
                    response.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries:
                        print(f"│ {'⚠️  Retrying connection...':<74} │")
                        time.sleep(2)
                    else:
                        print(f"│ {'❌ Connection failed!':<74} │")
                        print(f"└{'─'*76}┘")
                        return self._get_fallback_strategy()
            
            # Process streaming response
            line_length = 0
            for line in response.iter_lines():
                if line:
                    try:
                        # Skip "data: " prefix
                        line_text = line.decode('utf-8')
                        if line_text.startswith("data: "):
                            line_text = line_text[6:]
                        if line_text == "[DONE]":
                            continue
                            
                        # Parse JSON chunk
                        chunk = json.loads(line_text)
                        if 'choices' in chunk and chunk['choices']:
                            delta = chunk['choices'][0].get('delta', {})
                            if 'content' in delta:
                                content = delta['content']
                                accumulated_content += content
                                
                                # Count braces to track JSON completeness
                                open_braces += content.count('{')
                                close_braces += content.count('}')
                                
                                # Print content with word wrap
                                while len(content) > 0:
                                    available_space = 74 - line_length
                                    if available_space <= 0:
                                        print(" │")
                                        print("│ ", end="")
                                        line_length = 0
                                        available_space = 74
                                    
                                    chunk_to_print = content[:available_space]
                                    content = content[available_space:]
                                    print(chunk_to_print, end="", flush=True)
                                    line_length += len(chunk_to_print)
                                
                                # Try to extract JSON as it's coming in
                                if open_braces > 0 and open_braces == close_braces and not json_complete:
                                    try:
                                        cleaned = self._clean_json_response(accumulated_content)
                                        json.loads(cleaned)  # Just to validate
                                        accumulated_json = cleaned
                                        json_complete = True
                                    except json.JSONDecodeError:
                                        # Not complete JSON yet, keep accumulating
                                        pass
                    except Exception as e:
                        # Silently continue on parsing errors
                        pass
            
            # Finish the line if needed
            if line_length > 0:
                print(" " * (74 - line_length) + " │")
            
            elapsed_time = time.time() - start_time
            print(f"└{'─'*76}┘")
            print(f"\n✅ STREAMING COMPLETE in {elapsed_time:.2f} seconds\n")
            
            # If we couldn't extract valid JSON during streaming, try one more time
            if not json_complete:
                try:
                    cleaned = self._clean_json_response(accumulated_content)
                    json.loads(cleaned)
                    accumulated_json = cleaned
                    json_complete = True
                except json.JSONDecodeError:
                    pass
            
            # Print the final result
            if json_complete:
                parsed = json.loads(accumulated_json)
                print(f"📊 PARSED JSON RESULT:")
                print(f"┌{'─'*76}┐")
                formatted_json = json.dumps(parsed, indent=2)
                for line in formatted_json.split('\n'):
                    truncated = line[:70] + ("..." if len(line) > 70 else "")
                    print(f"│ {truncated:<74} │")
                print(f"└{'─'*76}┘")
                print(f"\n{'='*78}\n")
                return accumulated_json
            else:
                print(f"⚠️  WARNING: Could not parse complete JSON, using fallback")
                print(f"\n{'='*78}\n")
                return self._get_fallback_strategy()
                
        except Exception as e:
            print(f"└{'─'*76}┘")
            print(f"\n❌ ERROR: Streaming failed: {e}")
            print(f"\n{'='*78}\n")
            return self._get_fallback_strategy()

    def record_strategy_performance(self, strategy: dict, performance_metrics: dict) -> None:
        """Record how well a strategy performed to improve future suggestions"""
        self.strategy_history.append({
            "strategy": strategy,
            "performance": performance_metrics,
            "timestamp": time.time()
        })
        
        # Periodically send batch feedback to LLM for learning
        if len(self.strategy_history) >= 10:
            self._send_feedback_to_llm()
            self.strategy_history = []

    def evaluate_strategies_concurrently(self, strategies: list, evaluate_func) -> list:
        """Evaluate multiple strategies concurrently"""
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_strategy = {
                executor.submit(evaluate_func, strategy): strategy 
                for strategy in strategies
            }
            
            for future in concurrent.futures.as_completed(future_to_strategy):
                strategy = future_to_strategy[future]
                try:
                    result = future.result()
                    results.append((strategy, result))
                except Exception as e:
                    print(f"Strategy evaluation failed: {e}")
                
        return sorted(results, key=lambda x: x[1], reverse=True)

    def _validate_strategy(self, strategy: dict) -> bool:
        """Validate that a strategy has all required fields and valid values"""
        required_fields = ["mutation_rate_modifier", "operation_focus"]
        
        if not all(field in strategy for field in required_fields):
            return False
            
        # Validate mutation_rate_modifier is within reasonable bounds
        if not -0.5 <= strategy["mutation_rate_modifier"] <= 0.5:
            return False
            
        # Validate operation_focus is one of allowed values
        valid_focuses = ["balanced", "rotation", "swap", "position"]
        if strategy["operation_focus"] not in valid_focuses:
            return False
            
        return True

    def _create_batch_prompt(self, population_metrics: list, batch_size: int) -> str:
        """Create a prompt to request multiple strategies at once"""
        prompt = f"""
        I need {batch_size} different mutation strategies for a genetic algorithm optimization.
        
        Current population metrics:
        """
        
        for i, metric in enumerate(population_metrics[:3]):  # Include up to 3 recent metrics
            prompt += f"""
            Metric {i+1}:
            - Fitness: {metric.get('fitness', 'N/A')}
            - Diversity: {metric.get('diversity', 'N/A')}
            - Generation: {metric.get('generation', 'N/A')}
            - Stagnation: {metric.get('stagnation_count', 0)} generations
            """
        
        prompt += f"""
        Please provide {batch_size} different mutation strategies as a JSON object with the following structure:
        {{
            "strategies": [
                {{
                    "mutation_rate_modifier": <float between -0.5 and 0.5>,
                    "operation_focus": <"balanced", "rotation", "swap", or "position">,
                    "explanation": <brief explanation>
                }},
                ... (repeat for {batch_size} strategies)
            ]
        }}
        """
        
        return prompt

    def _send_feedback_to_llm(self) -> None:
        """Send performance feedback to improve future strategy suggestions"""
        if not self.strategy_history:
            return
            
        # Sort strategies by performance
        sorted_strategies = sorted(
            self.strategy_history, 
            key=lambda x: x["performance"].get("fitness_improvement", 0),
            reverse=True
        )
        
        # Create a prompt with the performance data
        prompt = """
        I'm providing performance data for previous mutation strategies in our container loading optimization.
        Please analyze this data and learn which strategies work best in which situations.
        
        Top performing strategies:
        """
        
        # Add top 3 strategies
        for i, strategy_data in enumerate(sorted_strategies[:3]):
            strategy = strategy_data["strategy"]
            performance = strategy_data["performance"]
            
            prompt += f"""
            Strategy {i+1}:
            - Mutation Rate Modifier: {strategy.get("mutation_rate_modifier")}
            - Operation Focus: {strategy.get("operation_focus")}
            - Fitness Improvement: {performance.get("fitness_improvement", "N/A")}
            - Space Utilization: {performance.get("space_utilization", "N/A")}
            - Generation: {performance.get("generation", "N/A")}
            """
            
        # Add worst strategy for comparison
        if len(sorted_strategies) > 3:
            worst = sorted_strategies[-1]
            prompt += f"""
            Worst performing strategy:
            - Mutation Rate Modifier: {worst["strategy"].get("mutation_rate_modifier")}
            - Operation Focus: {worst["strategy"].get("operation_focus")}
            - Fitness Improvement: {worst["performance"].get("fitness_improvement", "N/A")}
            - Space Utilization: {worst["performance"].get("space_utilization", "N/A")}
            - Generation: {worst["performance"].get("generation", "N/A")}
            """
            
        prompt += """
        No response is needed. This information is for your learning only.
        """
        
        # Log the feedback
        self.logger.info(f"Sending feedback to LLM based on {len(self.strategy_history)} strategies")
        self.logger.info(f"Top strategy performance: {sorted_strategies[0]['performance'].get('fitness_improvement', 0)}")
        
        # For the feedback, we don't need a response, just send the data
        try:
            self.session.post(
                self.api_url,
                headers=self.headers,
                json={
                    "model": "llama-3.3-70b-versatile",  # Use smaller model for feedback
                    "messages": [
                        {"role": "system", "content": "You are an AI learning from feedback."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1  # Minimal response needed
                },
                timeout=10
            )
        except Exception as e:
            self.logger.warning(f"Failed to send feedback: {e}")

    def _extract_generation_from_prompt(self, prompt: str) -> int:
        """Extract the current generation number from a prompt"""
        # Look for common patterns that indicate generation number
        patterns = [
            r"generation(?:\s+#?)?\s*[:=]?\s*(\d+)",  # generation: 42, generation #42
            r"at generation\s+(\d+)",                 # at generation 42
            r"current generation\s*[:=]?\s*(\d+)",    # current generation: 42
            r"gen\s*[:=]?\s*(\d+)"                    # gen: 42
        ]
        
        prompt_lower = prompt.lower()
        for pattern in patterns:
            import re
            matches = re.search(pattern, prompt_lower)
            if matches:
                try:
                    return int(matches.group(1))
                except (ValueError, IndexError):
                    pass
        
        # Default to middle generation if not found
        return 50

    async def generate_async(self, prompt: str, model: str = "llama-3.3-70b-specdec", max_tokens: int = 300) -> str:
        """Asynchronous version of generate to improve throughput"""
        if not self.enabled:
            return self._get_fallback_strategy()
            
        # Add system prompt to enforce JSON response
        data = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant that ALWAYS responds in valid JSON format. Your responses should contain ONLY the JSON object, with no additional text, explanations, or markdown."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3  # Lower temperature for more consistent JSON formatting
        }
        
        # Adjust temperature based on optimization phase
        current_generation = self._extract_generation_from_prompt(prompt)
        max_generations = 100  # Estimate
        
        if current_generation < max_generations * 0.3:
            data["temperature"] = 0.5  # Early: More exploration
        elif current_generation < max_generations * 0.7:
            data["temperature"] = 0.3  # Middle: Balanced
        else:
            data["temperature"] = 0.1  # Late: More exploitation
        
        print(f"\n{'='*60}")
        print(f"🧠 QUERYING LLM ASYNC: Asking Groq Cloud for adaptive mutation strategy...")
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
        
        print("\n⏳ WAITING FOR ASYNC RESPONSE...")
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=self.headers,
                    json=data,
                    timeout=30
                ) as response:
                    result = await response.json()
                    elapsed_time = time.time() - start_time
                    print(f"✅ ASYNC RESPONSE RECEIVED in {elapsed_time:.2f} seconds")
                    
                    content = result["choices"][0]["message"]["content"]
                    
                    # Try to clean and parse the response
                    cleaned_content = self._clean_json_response(content)
                    
                    print("\n📊 LLM RESPONSE:")
                    try:
                        parsed = json.loads(cleaned_content)
                        print(json.dumps(parsed, indent=2))
                        print(f"\n{'='*60}\n")
                        return cleaned_content
                    except json.JSONDecodeError:
                        print(f"\n⚠️  WARNING: Invalid JSON response, using fallback")
                        print(f"\n{'='*60}\n")
                        return self._get_fallback_strategy()
                    
        except Exception as e:
            print(f"\n❌ ERROR: Async Groq API request failed: {e}")
            print(f"\n{'='*60}\n")
            return self._get_fallback_strategy()

def get_llm_client(api_key=None):
    """Get an instance of the Groq LLM client"""
    return GroqClient(api_key)