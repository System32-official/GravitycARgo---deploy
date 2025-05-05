"""
Fallback module for groq package.
This provides minimal functionality to prevent import errors if the groq package is missing.
"""
import logging

logging.warning("Using fallback groq module. Full groq functionality may not be available.")

class GroqClient:
    def __init__(self, api_key=None):
        self.api_key = api_key
        logging.warning("GroqClient fallback initialized - using direct API calls instead")

# Export common names to mimic the groq module
__all__ = ['GroqClient']
