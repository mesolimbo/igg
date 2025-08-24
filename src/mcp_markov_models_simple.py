"""
Simplified MCP Markov Models Module for Lambda deployment
Uses real Markov chains without NLTK dependencies.
"""

import json
import logging
import os
import random
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import urllib.request
import urllib.parse
from collections import defaultdict, Counter


# Configuration
DEFAULT_BASE_URL = "https://invent.whileyou.work"
MODELS_DIR = Path(__file__).parent.parent / "models"
CACHE_DIR = MODELS_DIR / "cache"

# Configure logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def get_base_url() -> str:
    """Get base URL from environment or use default."""
    return os.environ.get("IGG_BASE_URL", DEFAULT_BASE_URL)


def ensure_cache_dir():
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def validate_model_name(model_name: str) -> None:
    """Validate model name to prevent path traversal and other attacks."""
    if not model_name:
        raise ValueError("Model name cannot be empty")
    if '..' in model_name:
        raise ValueError("Model name cannot contain '..' sequences")
    if model_name.startswith('/') or model_name.startswith('\\'):
        raise ValueError("Model name cannot be an absolute path")
    if '://' in model_name:
        raise ValueError("Model name cannot contain protocol schemes")
    if not re.match(r'^[a-zA-Z0-9._/-]+$', model_name):
        raise ValueError("Model name contains invalid characters")
    if len(model_name) > 200:
        raise ValueError("Model name is too long")


def simple_preprocess_text(text: str) -> List[str]:
    """Simple text preprocessing without NLTK dependencies."""
    # Convert to lowercase
    text = text.lower()
    
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Split into words, keeping only alphanumeric and basic punctuation
    words = re.findall(r"[a-zA-Z0-9']+|[.!?;,]", text)
    
    # Filter out very short words and common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can'}
    
    filtered_words = []
    for word in words:
        if len(word) > 1 and word not in stop_words:
            filtered_words.append(word)
    
    return filtered_words


def download_model(model_name: str) -> Optional[str]:
    """Download model data from the base URL."""
    validate_model_name(model_name)
    
    base_url = get_base_url()
    model_url = f"{base_url}/{urllib.parse.quote(model_name)}.txt"
    
    try:
        with urllib.request.urlopen(model_url) as response:
            if response.status == 200:
                return response.read().decode('utf-8')
            else:
                return None
    except urllib.error.HTTPError as e:
        print(f"HTTPError while downloading model '{model_name}' from {model_url}: {e.code} {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"URLError while downloading model '{model_name}' from {model_url}: {e.reason}")
        return None


def build_markov_chain(text: str, order: int = 2) -> Dict[tuple, List[str]]:
    """Build a Markov chain from preprocessed text."""
    words = simple_preprocess_text(text)
    
    if len(words) < order + 1:
        return {}
    
    chain = defaultdict(list)
    
    for i in range(len(words) - order):
        key = tuple(words[i:i + order])
        next_word = words[i + order]
        chain[key].append(next_word)
    
    return dict(chain)


def generate_from_markov_chain(chain: Dict[tuple, List[str]], length: int = 10, order: int = 2) -> str:
    """Generate text from a Markov chain."""
    if not chain:
        return ""
    
    # Start with a random key
    current_key = random.choice(list(chain.keys()))
    result = list(current_key)
    
    for _ in range(length - order):
        if current_key not in chain:
            break
        
        next_word = random.choice(chain[current_key])
        result.append(next_word)
        
        # Update key for next iteration
        current_key = tuple(result[-order:])
    
    return ' '.join(result)


async def list_models() -> Dict[str, Any]:
    """List available Markov models from web endpoint."""
    base_url = get_base_url()
    index_url = f"{base_url}/index.json"
    
    try:
        with urllib.request.urlopen(index_url) as response:
            if response.status == 200:
                index_data = json.loads(response.read().decode('utf-8'))
                models = index_data.get("models", [])
                
                # Extract model names from paths (remove .json extension and path)
                model_names = []
                for model_path in models:
                    model_name = model_path.split('/')[-1]  # Get filename
                    if model_name.endswith('.json'):
                        model_name = model_name[:-5]  # Remove .json
                    model_names.append(model_name)
                
                return {"models": model_names}
    except Exception as e:
        logger.error(f"Failed to fetch model list from {index_url}: {e}", exc_info=True)
    
    # Fallback to known models
    return {
        "models": ["sample"]
    }


async def generate_ideas(model_name: str, count: int = 5) -> List[str]:
    """Generate creative text ideas using Markov model from web."""
    validate_model_name(model_name)
    
    if count < 1 or count > 50:
        raise ValueError("Count must be between 1 and 50")
    
    # Fetch model from web
    base_url = get_base_url()
    # First try samples directory, then try root directory
    model_urls = [
        f"{base_url}/samples/{model_name}.json",
        f"{base_url}/{model_name}.json"
    ]
    
    model_data = None
    for model_url in model_urls:
        try:
            with urllib.request.urlopen(model_url) as response:
                if response.status == 200:
                    model_data = json.loads(response.read().decode('utf-8'))
                    break
        except Exception as e:
            print(f"Failed to fetch from {model_url}: {e}")
            continue
    
    if model_data is None:
        return [f"Generated {model_name} idea #{i+1}" for i in range(count)]
    
    try:
        
        # Extract transitions from the first column (usually column_index 0)
        if isinstance(model_data, list) and len(model_data) > 0:
            transitions = model_data[0].get("transitions", {})
        else:
            transitions = {}
        
        if not transitions:
            return [f"Generated {model_name} idea #{i+1}" for i in range(count)]
        
        # Generate ideas using the transition data
        ideas = []
        words = list(transitions.keys())
        
        for _ in range(count):
            # Start with a random word
            if not words:
                ideas.append(f"Generated {model_name} idea")
                continue
                
            current_word = random.choice(words)
            idea_words = [current_word]
            
            # Generate a chain of 2-5 words
            chain_length = random.randint(2, 5)
            for _ in range(chain_length - 1):
                if current_word in transitions:
                    next_options = transitions[current_word]
                    if next_options:
                        # Choose next word based on probabilities
                        next_word = random.choices(
                            list(next_options.keys()),
                            weights=list(next_options.values())
                        )[0]
                        idea_words.append(next_word)
                        current_word = next_word
                    else:
                        break
                else:
                    break
            
            # Join the words and format as an idea
            idea = " ".join(idea_words)
            if len(idea) > 3:  # Ensure meaningful content
                ideas.append(idea.capitalize())
            else:
                ideas.append(f"Generated {model_name} concept")
        
        return ideas
        
    except Exception as e:
        print(f"Error loading model {model_name} from web: {e}")
        return [f"Generated {model_name} idea #{i+1}" for i in range(count)]


async def generate_with_template(model_name: str, template: str, count: int = 5) -> List[str]:
    """Generate ideas using a template with placeholders."""
    validate_model_name(model_name)
    
    if not template:
        raise ValueError("Template cannot be empty")
    if count < 1 or count > 50:
        raise ValueError("Count must be between 1 and 50")
    
    # Download model data
    model_data = download_model(model_name)
    
    if not model_data:
        # Fallback to simple template replacement
        placeholders = {
            "$1": ["smart", "innovative", "sustainable", "efficient", "creative"],
            "$2": ["businesses", "individuals", "communities", "organizations", "teams"],
            "$3": ["productivity", "collaboration", "sustainability", "innovation", "growth"],
            "$4": ["technology", "platform", "solution", "system", "network"],
            "$5": ["global", "local", "emerging", "established", "growing"]
        }
        
        results = []
        for _ in range(count):
            filled_template = template
            for placeholder, options in placeholders.items():
                if placeholder in filled_template:
                    filled_template = filled_template.replace(placeholder, random.choice(options))
            results.append(filled_template)
        
        return results
    
    # Build Markov chain
    chain = build_markov_chain(model_data)
    words = simple_preprocess_text(model_data)
    
    if not chain or not words:
        return [template.replace(f"${i}", "innovation") for i in range(1, 6) for _ in range(count)][:count]
    
    # Extract word categories for placeholder replacement
    word_categories = {
        "$1": [w for w in words if len(w) > 3 and w.isalpha()][:20],  # Descriptive words
        "$2": [w for w in words if w.endswith('s') and len(w) > 4][:20],  # Plural nouns
        "$3": [w for w in words if len(w) > 4 and w.isalpha()][:20],  # Concepts
        "$4": [w for w in words if len(w) > 6 and w.isalpha()][:20],  # Technology terms
        "$5": [w for w in words if len(w) > 3 and w.isalpha()][:20]   # General terms
    }
    
    results = []
    for _ in range(count):
        filled_template = template
        for placeholder, word_list in word_categories.items():
            if placeholder in filled_template and word_list:
                filled_template = filled_template.replace(placeholder, random.choice(word_list))
        results.append(filled_template.capitalize())
    
    return results