"""
MCP Markov Models Module
Handles model downloading, caching, and text generation for IGG MCP server.
"""

import json
import os
import random
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import urllib.request
import urllib.parse

# Simple text preprocessing without external dependencies
def preprocess_text(text):
    """Simple text preprocessing without NLTK dependencies."""
    # Remove non-alphanumeric characters (keep letters and numbers)
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    # Strip leading and trailing whitespace
    text = text.strip()
    return text


# Configuration - will be loaded from environment or config file
DEFAULT_BASE_URL = "https://invent.whileyou.work"
MODELS_DIR = Path(__file__).parent.parent / "models"
CACHE_DIR = MODELS_DIR / "cache"


def get_base_url() -> str:
    """Get base URL from environment or use default."""
    return os.environ.get("IGG_BASE_URL", DEFAULT_BASE_URL)


def validate_model_name(model_name: str) -> None:
    """Validate model name to prevent path traversal and other attacks."""
    if not model_name:
        raise ValueError("Model name cannot be empty")
    
    # Prevent path traversal attacks
    if '..' in model_name:
        raise ValueError("Model name cannot contain '..' sequences")
    
    # Prevent absolute paths
    if model_name.startswith('/') or model_name.startswith('\\'):
        raise ValueError("Model name cannot be an absolute path")
    
    # Prevent protocol schemes that could be used for SSRF
    if '://' in model_name:
        raise ValueError("Model name cannot contain protocol schemes")
    
    # Allow only safe characters: alphanumeric, hyphens, underscores, forward slashes, and dots
    if not re.match(r'^[a-zA-Z0-9._/-]+$', model_name):
        raise ValueError("Model name contains invalid characters")
    
    # Ensure it has a reasonable length limit
    if len(model_name) > 200:
        raise ValueError("Model name is too long")


async def fetch_url(url: str) -> Dict[str, Any]:
    """Fetch JSON data from URL."""
    try:
        with urllib.request.urlopen(url) as response:
            data = response.read().decode('utf-8')
            return json.loads(data)
    except Exception as e:
        raise Exception(f"Failed to fetch {url}: {str(e)}")


async def list_models() -> Dict[str, Any]:
    """List available models from the web endpoint."""
    base_url = get_base_url()
    index_url = f"{base_url}/index.json"
    
    try:
        index_data = await fetch_url(index_url)
        models = index_data.get("models", [])
        
        # Extract model names from paths (remove .json extension and path)
        model_names = []
        for model_path in models:
            model_name = model_path.split('/')[-1]  # Get filename
            if model_name.endswith('.json'):
                model_name = model_name[:-5]  # Remove .json
            model_names.append(model_name)
        
        return {
            "base_url": base_url,
            "models": model_names
        }
    except Exception as e:
        # Fallback to known models
        return {
            "base_url": base_url,
            "models": ["sample"]
        }


async def load_model(model_name: str) -> List[Dict[str, Any]]:
    """Load a model from web (no caching for Lambda)."""
    validate_model_name(model_name)
    
    # Get the actual model paths from index
    base_url = get_base_url()
    index_url = f"{base_url}/index.json"
    
    try:
        index_data = await fetch_url(index_url)
        models = index_data.get("models", [])
        
        # Find the model path that matches our model name
        model_path = None
        for path in models:
            filename = path.split('/')[-1]  # Get filename
            if filename == f"{model_name}.json":
                model_path = path
                break
        
        if not model_path:
            raise Exception(f"Model '{model_name}' not found in index")
        
        # Load the model
        model_url = f"{base_url}/{model_path}"
        return await fetch_url(model_url)
        
    except Exception as e:
        raise Exception(f"Failed to load model '{model_name}': {str(e)}")


def weighted_random_choice(items: List[str], weights: List[float]) -> str:
    """Select item based on weighted probabilities."""
    if not items or not weights:
        raise ValueError("Items and weights cannot be empty")
    
    cumulative_weights = []
    for i, weight in enumerate(weights):
        cumulative_weights.append(weight + (cumulative_weights[i-1] if i > 0 else 0))
    
    random_val = random.random() * cumulative_weights[-1]
    for i, cum_weight in enumerate(cumulative_weights):
        if random_val <= cum_weight:
            return items[i]
    
    return items[-1]  # Fallback


def sample_phrase_length(max_length: int) -> int:
    """Sample target phrase length between 2 and max_length."""
    return random.randint(2, max_length)


def select_start_word(start_words_prob: Dict[str, float]) -> str:
    """Select starting word based on probabilities."""
    start_words = list(start_words_prob.keys())
    start_weights = list(start_words_prob.values())
    return weighted_random_choice(start_words, start_weights)


def select_next_word(current_word: str, transitions: Dict[str, Dict[str, float]], 
                    vocabulary: set) -> Optional[str]:
    """Select next word based on current word or randomly (5% chance)."""
    random_chance = random.random()
    if random_chance < 0.05:  # 5% chance for random word
        return select_random_word(vocabulary)
    else:
        next_words_prob = transitions.get(current_word)
        if not next_words_prob:
            return None
        
        next_words = list(next_words_prob.keys())
        next_weights = list(next_words_prob.values())
        return weighted_random_choice(next_words, next_weights)


def is_end_word(word: str, end_words: Dict[str, float]) -> bool:
    """Check if word can be an end word."""
    return word in end_words


def select_random_end_word(end_words_prob: Dict[str, float]) -> str:
    """Select random end word based on probabilities."""
    end_words = list(end_words_prob.keys())
    end_weights = list(end_words_prob.values())
    return weighted_random_choice(end_words, end_weights)


def select_random_word(vocabulary: set) -> str:
    """Select random word from vocabulary."""
    words = list(vocabulary)
    return random.choice(words)


def generate_phrase(model: Dict[str, Any]) -> str:
    """Generate a single phrase using a Markov model."""
    transitions = model["transitions"]
    start_words = model["start_words"]
    end_words = model["end_words"]
    lengths = model["lengths"]
    
    # Determine max observed length
    max_length = max(int(k) for k in lengths.keys())
    target_length = sample_phrase_length(max_length)
    
    current_word = select_start_word(start_words)
    phrase = [current_word]
    
    # Build vocabulary set
    vocabulary = set()
    vocabulary.update(transitions.keys())
    vocabulary.update(end_words.keys())
    vocabulary.update(start_words.keys())
    
    max_attempts = 1000
    attempts = 0
    
    while attempts < max_attempts:
        attempts += 1
        
        next_word = select_next_word(current_word, transitions, vocabulary)
        if not next_word:
            break  # No transitions from current word
        
        phrase.append(next_word)
        current_word = next_word
        
        # Check if we've reached target length
        if len(phrase) >= target_length:
            if is_end_word(current_word, end_words):
                break  # Good ending point
        
        # Prevent infinite loops
        if len(phrase) >= max_length:
            return generate_phrase(model)  # Recurse for new attempt
    
    # Ensure last word is an end word
    if not is_end_word(current_word, end_words):
        # Try to find end word from current transitions
        current_transitions = transitions.get(current_word, {})
        possible_end_words = [word for word in current_transitions.keys() 
                            if is_end_word(word, end_words)]
        
        if possible_end_words:
            end_word_weights = [current_transitions[word] for word in possible_end_words]
            current_word = weighted_random_choice(possible_end_words, end_word_weights)
            phrase.append(current_word)
        else:
            # Append random end word
            random_end_word = select_random_end_word(end_words)
            phrase.append(random_end_word)
    
    return " ".join(phrase)


async def generate_ideas(model_name: str, count: int = 5) -> List[str]:
    """Generate ideas using a specific model."""
    try:
        markov_models = await load_model(model_name)
        ideas = []
        
        for _ in range(count):
            # Generate phrase from each column/model
            row_phrases = []
            for model in markov_models:
                phrase = generate_phrase(model)
                row_phrases.append(phrase)
            
            # Join phrases with space
            idea = " ".join(row_phrases)
            ideas.append(idea)
        
        return ideas
    except Exception as e:
        raise Exception(f"Failed to generate ideas: {str(e)}")


async def generate_with_template(model_name: str, template: str, count: int = 5) -> List[str]:
    """Generate ideas using a template with placeholders."""
    try:
        markov_models = await load_model(model_name)
        ideas = []
        
        # Find placeholders in template ($1, $2, etc.)
        placeholders = re.findall(r'\$(\d+)', template)
        if not placeholders:
            raise ValueError("Template must contain placeholders like $1, $2, etc.")
        
        max_placeholder = max(int(p) for p in placeholders)
        if max_placeholder > len(markov_models):
            raise ValueError(f"Template requires {max_placeholder} models but only {len(markov_models)} available")
        
        for _ in range(count):
            # Generate phrases for each model
            generated_phrases = []
            for model in markov_models:
                phrase = generate_phrase(model)
                generated_phrases.append(phrase)
            
            # Fill template with generated phrases
            filled_template = template
            for i, phrase in enumerate(generated_phrases, 1):
                placeholder = f"${i}"
                filled_template = filled_template.replace(placeholder, phrase)
            
            ideas.append(filled_template)
        
        return ideas
    except Exception as e:
        raise Exception(f"Failed to generate templated ideas: {str(e)}")
