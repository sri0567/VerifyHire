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

def extract_summary(description: str, max_length: int = 1000):
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


def check_remote_validity(description: str) -> bool:
    """
    Improved remote job detection with scoring system and better pattern matching
    
    Returns:
        bool: True if likely remote, False if likely office-based
    """
    if not description:
        return False
    
    text = description.lower()
    
    # Strong remote indicators (high weight)
    strong_remote_indicators = [
        ("100% remote", 3),
        ("fully remote", 3),
        ("work from anywhere", 3),
        ("remote-first", 3),
        ("remote first", 3),
        ("distributed team", 2),
        ("anywhere in the world", 3),
        ("global remote", 2),
        ("work from home permanently", 3),
    ]
    
    # Moderate remote indicators
    moderate_remote_indicators = [
        "remote",
        "work from home",
        "wfh",
        "work remotely",
        "home-based",
        "virtual position",
        "telecommute",
        "remote work",
        "location independent",
        "work wherever you want",
        "no office",
        "fully distributed",
    ]
    
    # Office-based indicators (negative weight)
    office_indicators = [
        ("must relocate", 3),
        ("onsite required", 3),
        ("in-office", 2),
        ("in office", 2),
        ("driving",2),
        ("must be located in", 2),
        ("must live in", 2),
        ("hybrid schedule", 2),
        ("in-person", 2),
        ("office-based", 2),
        ("not remote", 3),
        ("this is not a remote position", 3),
        ("relocation required", 2),
        ("on-site", 2),
        ("onsite", 2),
        ("work from office", 2),
        ("attendance required", 1),
    ]
    
    # Location-specific indicators (context matters)
    location_indicators = [
        "must be based in",
        "must reside in",
        "local candidates only",
        "within commuting distance",
        "relocate to",
        "location"
    ]
    
    # Calculate score
    remote_score = 0
    office_score = 0
    
    # Check strong remote indicators
    for indicator, weight in strong_remote_indicators:
        if indicator in text:
            remote_score += weight
    
    # Check moderate remote indicators
    for indicator in moderate_remote_indicators:
        if indicator in text:
            # Check for negations
            if f"not {indicator}" in text or f"no {indicator}" in text:
                office_score += 2
            else:
                remote_score += 1
    
    # Check office indicators
    for indicator, weight in office_indicators:
        if indicator in text:
            office_score += weight
    
    # Check location requirements (indicates office-based)
    for indicator in location_indicators:
        if indicator in text:
            office_score += 2
    
    # Special case: If job mentions specific city/office location but also remote
    location_words = ['new york', 'san francisco', 'london', 'berlin', 'singapore', 'tokyo']
    city_mentioned = any(city in text for city in location_words)
    
    # If city mentioned but no strong remote indicators, likely office-based
    if city_mentioned and remote_score < 2:
        office_score += 1
    
    # Decision logic
    # Strong remote signals override everything
    if "100% remote" in text or "fully remote" in text:
        return True
    
    # If strong office signals, return False
    if office_score >= 3:
        return False
    
    # If remote score is high enough, return True
    if remote_score >= 2:
        return True
    
    # Default to False if uncertain
    return False

def calculate_score(flags, verified_remote):
    score = 100

    score -= len(flags) * 20

    if not verified_remote:
        score -= 15

    if score < 0:
        score = 0

    return score