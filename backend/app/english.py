from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

# Set seed for consistent results
DetectorFactory.seed = 0

def is_english(text: str, min_confidence: float = 0.8) -> bool:
    """
    Detect if text is in English
    
    Args:
        text: Text to check
        min_confidence: Minimum confidence threshold (0-1)
    
    Returns:
        True if text is English, False otherwise
    """
    if not text:
        return False
    
    try:
        # Detect language
        language = detect(text)
        return language == 'en'
    except LangDetectException:
        # If detection fails, check for common English patterns
        return has_english_patterns(text)

def has_english_patterns(text: str) -> bool:
    """Fallback method to check for English patterns"""
    # Common English words as indicators
    english_indicators = [
        'the', 'and', 'for', 'you', 'are', 'with', 'have',
        'this', 'that', 'from', 'they', 'will', 'work',
        'remote', 'position', 'company', 'experience'
    ]
    
    text_lower = text.lower()
    english_count = sum(1 for word in english_indicators if word in text_lower)
    
    # If enough common English words, assume English
    return english_count >= 3