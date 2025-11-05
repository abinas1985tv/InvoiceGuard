import google.generativeai as genai
import os
from typing import List
import time
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ResponseWrapper:
    """Wrapper class that acts like a string but also has a .text attribute for testing compatibility"""
    def __init__(self, text: str):
        self._text = text
    
    @property
    def text(self):
        return self._text
    
    def __str__(self):
        return self._text
    
    def strip(self):
        return self._text.strip()
    
    def startswith(self, prefix):
        return self._text.startswith(prefix)
    
    def replace(self, old, new):
        return self._text.replace(old, new)

class GeminiMultiKeyClient:
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.current_key_index = 0
        self.models = {}
        
        # Initialize models for each API key
        for i, key in enumerate(api_keys):
            genai.configure(api_key=key)
            self.models[i] = genai.GenerativeModel('gemini-2.0-flash')
    
    def rotate_key(self):
        """Rotate to the next API key"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
    
    def generate_content(self, prompt: str, max_retries: int = 3):
        """Generate content with automatic key rotation on failure
        Returns a ResponseWrapper object with a .text attribute for compatibility"""
        for _ in range(max_retries):
            try:
                # Configure the current API key
                genai.configure(api_key=self.api_keys[self.current_key_index])
                model = self.models[self.current_key_index]
                
                response = model.generate_content(prompt)
                return ResponseWrapper(response.text)
                
            except Exception:
                #print(f"Error with key {self.current_key_index}: {e}")
                self.rotate_key()
                time.sleep(1)  # Brief pause before retry
        
        return None


def load_api_keys_from_env() -> List[str]:
    """Load multiple API keys from environment variables"""
    keys = []
    
    # Try to load multiple keys (GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.)
    i = 1
    while True:
        key = os.getenv(f'GEMINI_API_KEY_{i}')
        if key:
            keys.append(key)
            i += 1
        else:
            break
    
    # Fallback to single key if no numbered keys found
    if not keys:
        single_key = os.getenv('GEMINI_API_KEY')
        if single_key:
            keys.append(single_key)
    #print(keys)
    return keys


# Module-level shared model instance for all genAI functions
# Initialize lazily when first accessed
_shared_model = None

def get_model() -> GeminiMultiKeyClient:
    """Get or create the shared Gemini model instance"""
    global _shared_model
    
    if _shared_model is None:
        api_keys = load_api_keys_from_env()
        if not api_keys:
            raise ValueError("No Gemini API keys found. Please set GEMINI_API_KEY or GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.")
        _shared_model = GeminiMultiKeyClient(api_keys)
    
    return _shared_model
