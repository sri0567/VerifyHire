import re
from html import unescape

def clean_description(description: str, max_length: int = 1500):
    """
    Aggressively clean and shorten job description
    - Removes ALL HTML tags and attributes
    - Removes links, images, scripts
    - Decodes HTML entities
    - Compresses whitespace
    - Truncates to reasonable length
    """
    if not description:
        return ""
    
    # Remove script and style tags and their content
    description = re.sub(r'<script[^>]*>.*?</script>', ' ', description, flags=re.DOTALL | re.IGNORECASE)
    description = re.sub(r'<style[^>]*>.*?</style>', ' ', description, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove all HTML tags (including those with attributes)
    description = re.sub(r'<[^>]+>', ' ', description)
    
    # Remove common HTML entities
    description = unescape(description)
    
    # Remove URLs
    description = re.sub(r'https?://\S+|www\.\S+', ' ', description)
    
    # Remove email addresses
    description = re.sub(r'\S+@\S+\.\S+', ' ', description)
    
    # Remove markdown links [text](url)
    description = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', description)
    
    # Remove multiple spaces, newlines, tabs
    description = re.sub(r'\s+', ' ', description)
    
    # Remove any remaining special characters (keep only basic punctuation)
    description = re.sub(r'[^\w\s\.\,\!\?\-\']', ' ', description)
    
    # Strip leading/trailing spaces
    description = description.strip()
    
    # Truncate to max length
    if len(description) > max_length:
        # Try to cut at last sentence or space
        truncated = description[:max_length]
        last_period = truncated.rfind('.')
        last_space = truncated.rfind(' ')
        
        if last_period > max_length * 0.7:  # Cut at sentence if possible
            description = truncated[:last_period + 1]
        elif last_space > max_length * 0.7:  # Otherwise cut at space
            description = truncated[:last_space]
        else:
            description = truncated + "..."
    
    return description

def extract_summary(description: str, max_length: int = 500):
    """
    Extract a very short summary from the description
    - Takes first few sentences
    """
    if not description:
        return ""
    
    # Clean first
    cleaned = clean_description(description, max_length=2000)
    
    # Split into sentences
    sentences = re.split(r'[.!?]+', cleaned)
    
    # Take first 2-3 sentences
    summary = '. '.join(sentences[:3]).strip()
    
    # Add period if missing
    if summary and not summary.endswith('.'):
        summary += '.'
    
    # Truncate if still too long
    if len(summary) > max_length:
        summary = summary[:max_length] + "..."
    
    return summary

SCAM_PHRASES = [
    "quick money",
    "training fee",
    "whatsapp interview",
    "crypto payment",
    "telegram only",
]


def detect_scam_phrases(description: str):
    description_lower = description.lower()

    found_flags = []

    for phrase in SCAM_PHRASES:
        if phrase in description_lower:
            found_flags.append(phrase)

    return found_flags


def check_remote_validity(description: str):
   
    if not description:
        return False
    
    text = description.lower()
    
    # Strong remote indicators
    remote_indicators = [
        "remote",
        "work from home",
        "wfh",
        "work remotely",
        "anywhere in the world",
        "100% remote",
        "fully remote",
        "distributed team",
        "work wherever you want",
        "home-based",
        "virtual position"
    ]
    
   
    office_indicators = [
        "must relocate",
        "onsite required",
        "in-office",
        "hybird",
        "in office",
        "must be located in",
        "must live in",
        "hybrid schedule",
        "in-person",
        "office-based",
        "not remote",
        "this is not a remote position"
    ]
    
   
    for indicator in office_indicators:
        if indicator in text:
            return False
    
    
    for indicator in remote_indicators:
        if indicator in text:
            return True
    
   
    return False


def calculate_score(flags, verified_remote):
    score = 100

    score -= len(flags) * 20

    if not verified_remote:
        score -= 15

    if score < 0:
        score = 0

    return score