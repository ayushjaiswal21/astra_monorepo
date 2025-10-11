import re
from langdetect import detect, detect_langs, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

# Set seed for consistent language detection
DetectorFactory.seed = 0

# Language names mapping for better user experience
LANGUAGE_NAMES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French', 
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'zh': 'Chinese',
    'ja': 'Japanese',
    'ko': 'Korean',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'bn': 'Bengali',
    'ur': 'Urdu',
    'te': 'Telugu',
    'ta': 'Tamil',
    'ml': 'Malayalam',
    'kn': 'Kannada',
    'gu': 'Gujarati',
    'pa': 'Punjabi',
    'mr': 'Marathi',
    'ne': 'Nepali',
    'si': 'Sinhala',
    'th': 'Thai',
    'vi': 'Vietnamese',
    'id': 'Indonesian',
    'ms': 'Malay',
    'tl': 'Filipino',
    'nl': 'Dutch',
    'sv': 'Swedish',
    'da': 'Danish',
    'no': 'Norwegian',
    'fi': 'Finnish',
    'pl': 'Polish',
    'cs': 'Czech',
    'sk': 'Slovak',
    'hu': 'Hungarian',
    'ro': 'Romanian',
    'bg': 'Bulgarian',
    'hr': 'Croatian',
    'sr': 'Serbian',
    'sl': 'Slovenian',
    'et': 'Estonian',
    'lv': 'Latvian',
    'lt': 'Lithuanian',
    'uk': 'Ukrainian',
    'be': 'Belarusian',
    'mk': 'Macedonian',
    'mt': 'Maltese',
    'ga': 'Irish',
    'cy': 'Welsh',
    'eu': 'Basque',
    'ca': 'Catalan',
    'gl': 'Galician',
    'tr': 'Turkish',
    'az': 'Azerbaijani',
    'kk': 'Kazakh',
    'ky': 'Kyrgyz',
    'uz': 'Uzbek',
    'mn': 'Mongolian',
    'fa': 'Persian',
    'ps': 'Pashto',
    'ku': 'Kurdish',
    'he': 'Hebrew',
    'yi': 'Yiddish',
    'am': 'Amharic',
    'ti': 'Tigrinya',
    'or': 'Odia',
    'as': 'Assamese',
    'my': 'Myanmar',
    'km': 'Khmer',
    'lo': 'Lao',
    'ka': 'Georgian',
    'hy': 'Armenian',
    'is': 'Icelandic',
    'fo': 'Faroese',
    'sq': 'Albanian',
    'el': 'Greek',
    'la': 'Latin',
    'sw': 'Swahili',
    'zu': 'Zulu',
    'xh': 'Xhosa',
    'af': 'Afrikaans',
    'yo': 'Yoruba',
    'ig': 'Igbo',
    'ha': 'Hausa',
}

def detect_language(text: str) -> tuple:
    """
    Detect the language of input text with confidence, handling mixed languages.
    Returns tuple: (language_code, confidence, should_display)
    """
    try:
        # Clean text for better detection
        cleaned_text = text.strip()
        
        # Return None for very short text to avoid inaccurate detection
        if len(cleaned_text) < 5:
            return ('en', 0.0, False)  # Don't show detection for short text
        
        # Check for Indian scripts first (more reliable than langdetect for mixed text)
        indian_lang = detect_mixed_indian_language(cleaned_text)
        if indian_lang:
            return (indian_lang, 0.95, True)  # High confidence for script detection
        
        # Get language probabilities for other languages
        lang_probs = detect_langs(cleaned_text)
        
        if not lang_probs:
            return ('en', 0.0, False)
        
        # Get the most likely language and its confidence
        top_lang = lang_probs[0]
        language_code = top_lang.lang
        confidence = top_lang.prob
        
        # Filter out commonly mis-detected European languages for Indian English users
        problematic_codes = ['fi', 'da', 'no', 'sv', 'et', 'lv', 'lt', 'so', 'cy', 'eu', 'mt', 'ga', 'is', 'fo', 'ca', 'pt', 'ro', 'sk', 'cs', 'hr', 'sl']
        if language_code in problematic_codes:
            return ('en', 0.0, False)  # Treat as English
        
        # Only show language detection if confidence is high enough
        should_display = confidence > 0.85 and language_code != 'en'
        
        return (language_code, confidence, should_display)
        
    except (LangDetectException, Exception) as e:
        print(f"Language detection error: {e}")
        return ('en', 0.0, False)  # Default to English, don't display

def has_indian_script(text: str) -> bool:
    """Check if text contains Indian language scripts"""
    indian_script_ranges = [
        (0x0900, 0x097F),  # Devanagari (Hindi, Marathi, Nepali)
        (0x0980, 0x09FF),  # Bengali
        (0x0A00, 0x0A7F),  # Gurmukhi (Punjabi)
        (0x0A80, 0x0AFF),  # Gujarati
        (0x0B00, 0x0B7F),  # Oriya
        (0x0B80, 0x0BFF),  # Tamil
        (0x0C00, 0x0C7F),  # Telugu
        (0x0C80, 0x0CFF),  # Kannada
        (0x0D00, 0x0D7F),  # Malayalam
    ]
    
    for char in text:
        char_code = ord(char)
        for start, end in indian_script_ranges:
            if start <= char_code <= end:
                return True
    return False

def detect_mixed_indian_language(text: str) -> str:
    """Detect mixed Indian languages with English"""
    # Check for Telugu script
    if any('\u0c00' <= char <= '\u0c7f' for char in text):
        return 'te'  # Telugu
    
    # Check for Hindi/Devanagari script
    if any('\u0900' <= char <= '\u097f' for char in text):
        return 'hi'  # Hindi
    
    # Check for Bengali script
    if any('\u0980' <= char <= '\u09ff' for char in text):
        return 'bn'  # Bengali
    
    # Check for Tamil script
    if any('\u0b80' <= char <= '\u0bff' for char in text):
        return 'ta'  # Tamil
    
    # Check for Gujarati script
    if any('\u0a80' <= char <= '\u0aff' for char in text):
        return 'gu'  # Gujarati
    
    # Check for Kannada script
    if any('\u0c80' <= char <= '\u0cff' for char in text):
        return 'kn'  # Kannada
    
    # Check for Malayalam script
    if any('\u0d00' <= char <= '\u0d7f' for char in text):
        return 'ml'  # Malayalam
    
    # Check for Punjabi script
    if any('\u0a00' <= char <= '\u0a7f' for char in text):
        return 'pa'  # Punjabi
    
    return None
