"""
Model Utilities for GPU Service
Helper functions for model management and text processing
"""

import re
import uuid
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime

from .logger import logger


def generate_request_id() -> str:
    """Generate unique request ID"""
    return f"req_{uuid.uuid4().hex[:12]}"


def generate_response_id() -> str:
    """Generate unique response ID"""
    return f"resp_{uuid.uuid4().hex[:12]}"


def generate_batch_id() -> str:
    """Generate unique batch ID"""
    return f"batch_{uuid.uuid4().hex[:12]}"


def calculate_tokens(text: str) -> int:
    """
    Estimate token count for text
    Simple approximation: ~4 characters per token for English text
    """
    if not text:
        return 0
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Rough estimation: 4 characters per token
    # This is a simplification - actual tokenization depends on the model
    estimated_tokens = len(text) // 4
    
    # Minimum 1 token for non-empty text
    return max(1, estimated_tokens)


def validate_model_name(model_name: str) -> bool:
    """Validate model name format"""
    if not model_name:
        return False
    
    # Basic validation for OLLAMA model names
    # Format: family:size (e.g., gemma2:9b, llama2:7b)
    pattern = r'^[a-zA-Z0-9_-]+:[a-zA-Z0-9_.-]+$'
    return bool(re.match(pattern, model_name))


def format_model_size(size_str: str) -> str:
    """Format model size string"""
    if not size_str:
        return "Unknown"
    
    # Convert to uppercase and ensure 'B' suffix
    size_str = size_str.upper()
    if not size_str.endswith('B'):
        size_str += 'B'
    
    return size_str


def parse_model_name(model_name: str) -> Dict[str, str]:
    """Parse model name into components"""
    if ':' not in model_name:
        return {
            "family": model_name,
            "size": "unknown",
            "full_name": model_name
        }
    
    family, size = model_name.split(':', 1)
    return {
        "family": family,
        "size": size,
        "full_name": model_name
    }


def estimate_model_memory(model_size: str) -> float:
    """Estimate memory usage for model size"""
    size_map = {
        "7b": 14.0,   # ~14GB for 7B model
        "9b": 18.0,   # ~18GB for 9B model
        "13b": 26.0,  # ~26GB for 13B model
        "27b": 54.0,  # ~54GB for 27B model
        "70b": 140.0, # ~140GB for 70B model
    }
    
    size_lower = model_size.lower().replace('b', '')
    return size_map.get(f"{size_lower}b", 8.0)  # Default 8GB


def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    return text.strip()


def truncate_text(text: str, max_length: int) -> str:
    """Truncate text to maximum length"""
    if len(text) <= max_length:
        return text
    
    # Try to truncate at word boundary
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.8:  # If we can save 80% of the text
        return truncated[:last_space] + "..."
    else:
        return truncated + "..."


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extract keywords from text for caching/indexing"""
    if not text:
        return []
    
    # Simple keyword extraction
    # Remove punctuation and convert to lowercase
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Remove common stop words
    stop_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
        'after', 'above', 'below', 'between', 'among', 'this', 'that', 'these',
        'those', 'what', 'which', 'who', 'when', 'where', 'why', 'how', 'all',
        'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
        'only', 'own', 'same', 'than', 'too', 'very', 'can', 'will', 'just'
    }
    
    keywords = [word for word in words if word not in stop_words]
    
    # Count frequency and return most common
    word_freq = {}
    for word in keywords:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency and return top keywords
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:max_keywords]]


def create_cache_key(prompt: str, model: str, options: Dict[str, Any]) -> str:
    """Create cache key for request"""
    # Create a hash of the request parameters
    key_data = {
        "prompt": prompt,
        "model": model,
        "options": options
    }
    
    # Convert to string and hash
    key_string = str(sorted(key_data.items()))
    hash_object = hashlib.md5(key_string.encode())
    return f"inference:{hash_object.hexdigest()}"


def format_processing_time(seconds: float) -> str:
    """Format processing time for display"""
    if seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"


def validate_generation_options(options: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize generation options"""
    validated = {}
    
    # Temperature
    if "temperature" in options:
        temp = float(options["temperature"])
        validated["temperature"] = max(0.0, min(2.0, temp))
    
    # Top-p
    if "top_p" in options:
        top_p = float(options["top_p"])
        validated["top_p"] = max(0.0, min(1.0, top_p))
    
    # Top-k
    if "top_k" in options:
        top_k = int(options["top_k"])
        validated["top_k"] = max(1, min(100, top_k))
    
    # Max tokens
    if "max_tokens" in options:
        max_tokens = int(options["max_tokens"])
        validated["num_predict"] = max(1, min(8192, max_tokens))
    
    # Stop sequences
    if "stop_sequences" in options and options["stop_sequences"]:
        stop_sequences = options["stop_sequences"]
        if isinstance(stop_sequences, list):
            validated["stop"] = stop_sequences[:10]  # Limit to 10 stop sequences
    
    # Seed
    if "seed" in options and options["seed"] is not None:
        validated["seed"] = int(options["seed"])
    
    return validated


def get_model_info_from_name(model_name: str) -> Dict[str, Any]:
    """Get model information from name"""
    parsed = parse_model_name(model_name)
    
    return {
        "name": model_name,
        "family": parsed["family"],
        "size": format_model_size(parsed["size"]),
        "estimated_memory": estimate_model_memory(parsed["size"]),
        "context_length": get_context_length(parsed["family"]),
        "parameters": get_parameter_count(parsed["size"])
    }


def get_context_length(model_family: str) -> int:
    """Get context length for model family"""
    context_lengths = {
        "gemma2": 8192,
        "llama2": 4096,
        "llama3": 8192,
        "mistral": 8192,
        "codellama": 16384,
        "phi": 2048
    }
    
    return context_lengths.get(model_family.lower(), 4096)


def get_parameter_count(size_str: str) -> int:
    """Get parameter count from size string"""
    size_lower = size_str.lower().replace('b', '')
    
    try:
        if 'b' in size_str.lower():
            return int(float(size_lower) * 1_000_000_000)
        elif 'm' in size_str.lower():
            return int(float(size_lower.replace('m', '')) * 1_000_000)
        else:
            return int(float(size_lower) * 1_000_000_000)  # Assume billions
    except (ValueError, TypeError):
        return 0
