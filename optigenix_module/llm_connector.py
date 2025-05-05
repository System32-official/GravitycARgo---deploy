"""
LLM Connector module for integrating with large language models
Handles API requests, error handling, and response processing
"""
import os
import json
import requests
import time
from typing import Optional, Dict, Any, Union
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default API settings (override with environment variables)
DEFAULT_API_URL = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
DEFAULT_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

def get_llm_completion(
    prompt: str, 
    temperature: float = 0.4, 
    max_tokens: int = 1000,
    api_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    retry_count: int = 3,
    retry_delay: float = 2.0
) -> Optional[str]:
    """
    Get a completion from the LLM API
    
    Args:
        prompt (str): The prompt to send to the LLM
        temperature (float): Controls randomness (0.0 to 1.0)
        max_tokens (int): Maximum number of tokens to generate
        api_url (str, optional): Override the default API URL
        api_key (str, optional): Override the default API key
        model (str, optional): Override the default model
        retry_count (int): Number of retries on failure
        retry_delay (float): Delay between retries in seconds
        
    Returns:
        Optional[str]: The LLM completion text or None on failure
    """
    url = api_url or DEFAULT_API_URL
    key = api_key or DEFAULT_API_KEY
    model_name = model or DEFAULT_MODEL
    
    if not key:
        logger.error("No API key provided. Set OPENAI_API_KEY environment variable.")
        return None
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    }
    
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    for attempt in range(retry_count):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    logger.error(f"Unexpected API response format: {result}")
            else:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                
                # Handle rate limits with longer backoff
                if response.status_code == 429:
                    retry_delay = min(retry_delay * 2, 60)  # Exponential backoff, max 60s
                
        except requests.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
        
        # Don't sleep after the last attempt
        if attempt < retry_count - 1:
            logger.info(f"Retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{retry_count})")
            time.sleep(retry_delay)
    
    return None

def validate_json_response(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract and validate JSON from LLM response text
    
    Args:
        text (str): The LLM response text that should contain JSON
        
    Returns:
        Optional[Dict[str, Any]]: Parsed JSON object or None if invalid
    """
    try:
        # First try direct parsing in case the response is clean JSON
        return json.loads(text)
    except json.JSONDecodeError:
        # Look for JSON block if direct parsing fails
        try:
            # Find content between triple backticks ```json and ```
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # Try to find any JSON-like content with curly braces
            json_match = re.search(r'(\{[\s\S]*\})', text)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
                
        except (json.JSONDecodeError, AttributeError):
            logger.error("Failed to extract valid JSON from LLM response")
            
    return None

def get_llm_client():
    """
    Returns a configured LLM client for making requests
    
    Returns:
        GroqClient: A client instance for making LLM requests
    """
    print("\n===============================================")
    print("✅ LLM Connector initialized with Groq Cloud")
    print("==================================================\n")
    return GroqClient()

class GroqClient:
    """Simple client for Groq Cloud API"""
    
    def __init__(self):
        """Initialize the Groq client with API key"""
        self.api_key = os.getenv("GROQ_API_KEY", DEFAULT_API_KEY)
        self.api_url = os.getenv("GROQ_API_URL", DEFAULT_API_URL)
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        
        logger.info(f"Initialized Groq client with model: {self.model}")
        
    def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 800) -> str:
        """
        Generate a response from the LLM
        
        Args:
            prompt (str): The prompt to send
            temperature (float): Controls randomness
            max_tokens (int): Maximum response length
            
        Returns:
            str: The generated response text
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    logger.error(f"Unexpected API response format: {result}")
            else:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            
        return ""
