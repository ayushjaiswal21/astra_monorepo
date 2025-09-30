from fastapi import FastAPI, Body, UploadFile, File, HTTPException, Depends, Request
from pymongo import MongoClient
import tempfile
import os
import base64
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image
import io
from datetime import datetime
import uuid
import re
from pydantic import BaseModel, field_validator
from typing import Optional
from collections import defaultdict
from datetime import timedelta
import langdetect
from langdetect import detect, detect_langs, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

# Set seed for consistent language detection
DetectorFactory.seed = 0

# Load environment variables
load_dotenv()

# Security: Validate required environment variables
REQUIRED_ENV_VARS = ['GEMINI_API_KEY', 'MONGODB_URI']
missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Configure Gemini
gemini_api_key = os.getenv('GEMINI_API_KEY')
if not gemini_api_key:
    raise ValueError("No GEMINI_API_KEY set for AI Guru application")

# MongoDB connection config with SSL settings
MONGODB_URI = os.getenv('MONGODB_URI')
if not MONGODB_URI:
    raise RuntimeError("🚨 MONGODB_URI environment variable is required but not set!")

try:
    # Configure MongoDB client with proper settings
    client = MongoClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000,
        maxPoolSize=1
    )
    # Test the connection
    client.admin.command('ping')
    print("✅ MongoDB connection successful")
    db = client.guru_multibot
    chat_collection = db.chat_history
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    print("📝 Using fallback in-memory storage")
    # Fallback to in-memory storage if MongoDB fails
    client = None
    db = None
    chat_collection = None

# Security: Rate limiting
class RateLimiter:
    def __init__(self, max_requests: int = 30, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)
    
    async def check_rate_limit(self, client_ip: str):
        now = datetime.now()
        
        # Clean old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < timedelta(seconds=self.time_window)
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.max_requests:
            raise HTTPException(
                status_code=429, 
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Add current request
        self.requests[client_ip].append(now)

# Global rate limiter instance
rate_limiter = RateLimiter(max_requests=30, time_window=60)

# Language detection function
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

# Security: Input validation models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        if len(v) > 5000:  # Limit message length
            raise ValueError('Message too long (max 5000 characters)')
        # Remove potentially dangerous characters
        v = re.sub(r'[<>"\';]', '', v.strip())
        return v
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9-]+$', v):
            raise ValueError('Invalid session ID format')
        return v

class ImageRequest(BaseModel):
    description: str
    session_id: Optional[str] = None
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if len(v) > 1000:
            raise ValueError('Description too long (max 1000 characters)')
        v = re.sub(r'[<>"\';]', '', v.strip())
        return v

def store_interaction(input_type, user_input, bot_response, session_id=None, language_code=None, user_feedback=None):
    # Generate session_id if not provided
    if not session_id:
        session_id = str(uuid.uuid4())[:8]  # Short session ID
    
    interaction_id = None
    
    # Only store in MongoDB if connection is available
    if chat_collection is not None:
        try:
            # Generate a unique interaction ID
            interaction_id = str(uuid.uuid4())
            
            # Create document for MongoDB with learning data
            document = {
                "_id": interaction_id,
                "input_type": input_type,
                "user_input": user_input,
                "bot_response": bot_response,
                "session_id": session_id,
                "language_code": language_code,
                "language_name": LANGUAGE_NAMES.get(language_code, 'Unknown') if language_code else None,
                "timestamp": datetime.utcnow(),
                "user_feedback": user_feedback,  # Store user feedback for learning
                "response_length": len(bot_response) if bot_response else 0,
                "input_patterns": analyze_input_patterns(user_input),
                "response_format": detect_response_format(bot_response),
                "interaction_context": extract_context_features(user_input, bot_response)
            }
            
            # Insert into MongoDB
            chat_collection.insert_one(document)
            print(f"💾 Stored interaction for session {session_id} (Language: {LANGUAGE_NAMES.get(language_code, 'Unknown')})")
            
            # Learn from this interaction for future improvements
            learn_from_interaction(document)
            
        except Exception as e:
            print(f"⚠️ Failed to store interaction: {e}")
            interaction_id = f"{session_id}_{int(datetime.utcnow().timestamp())}"  # Fallback ID
    else:
        print(f"📝 In-memory mode: interaction not persisted for session {session_id}")
        interaction_id = f"{session_id}_{int(datetime.utcnow().timestamp())}"  # Fallback ID
    
    return session_id, interaction_id

def analyze_input_patterns(user_input):
    """Analyze patterns in user input to learn preferences"""
    patterns = {
        "request_type": "",
        "formality_level": "",
        "length_preference": "",
        "keywords": []
    }
    
    user_input_lower = user_input.lower()
    
    # Detect request type
    if any(word in user_input_lower for word in ['paragraph', 'write', 'describe', 'tell me about', 'essay']):
        patterns["request_type"] = "paragraph"
    elif any(word in user_input_lower for word in ['explain', 'list', 'break down', 'steps', 'outline']):
        patterns["request_type"] = "structured"
    elif any(word in user_input_lower for word in ['hi', 'hello', 'thanks', 'how are you']):
        patterns["request_type"] = "casual"
    else:
        patterns["request_type"] = "mixed"
    
    # Detect formality level
    formal_indicators = ['please', 'could you', 'would you', 'kindly', 'sir', 'madam']
    casual_indicators = ['hey', 'yo', 'sup', 'what\'s up', 'cool', 'awesome']
    
    if any(word in user_input_lower for word in formal_indicators):
        patterns["formality_level"] = "formal"
    elif any(word in user_input_lower for word in casual_indicators):
        patterns["formality_level"] = "casual"
    else:
        patterns["formality_level"] = "neutral"
    
    # Length preference detection
    if len(user_input) < 20:
        patterns["length_preference"] = "short"
    elif len(user_input) > 100:
        patterns["length_preference"] = "detailed"
    else:
        patterns["length_preference"] = "medium"
    
    # Extract key topics/keywords
    import re
    words = re.findall(r'\b[a-zA-Z]{3,}\b', user_input.lower())
    common_words = {'the', 'and', 'you', 'for', 'are', 'with', 'can', 'about', 'what', 'how', 'that', 'this'}
    patterns["keywords"] = [word for word in words if word not in common_words][:10]
    
    return patterns

def detect_response_format(bot_response):
    """Analyze the format of bot response"""
    if not bot_response:
        return "empty"
    
    format_info = {
        "has_bullets": bool(re.search(r'^[\s]*[-•*]', bot_response, re.MULTILINE)),
        "has_numbering": bool(re.search(r'^[\s]*\d+\.', bot_response, re.MULTILINE)),
        "has_sections": bool(re.search(r'\*\*.*\*\*', bot_response)),
        "has_emojis": bool(re.search(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', bot_response)),
        "length": len(bot_response),
        "format_type": ""
    }
    
    if format_info["has_sections"] and (format_info["has_bullets"] or format_info["has_numbering"]):
        format_info["format_type"] = "structured"
    elif not format_info["has_bullets"] and not format_info["has_numbering"] and not format_info["has_sections"]:
        format_info["format_type"] = "paragraph"
    else:
        format_info["format_type"] = "mixed"
    
    return format_info

def extract_context_features(user_input, bot_response):
    """Extract contextual features for learning"""
    return {
        "topic": extract_topic(user_input),
        "sentiment": detect_sentiment(user_input),
        "complexity": assess_complexity(user_input),
        "success_indicators": detect_success_patterns(user_input, bot_response)
    }

def extract_topic(text):
    """Simple topic extraction"""
    topics = {
        'science': ['science', 'physics', 'chemistry', 'biology', 'research'],
        'technology': ['AI', 'computer', 'software', 'programming', 'tech'],
        'education': ['learn', 'study', 'school', 'education', 'knowledge'],
        'general': []
    }
    
    text_lower = text.lower()
    for topic, keywords in topics.items():
        if any(keyword in text_lower for keyword in keywords):
            return topic
    return 'general'

def detect_sentiment(text):
    """Simple sentiment detection"""
    positive_words = ['good', 'great', 'awesome', 'excellent', 'love', 'like', 'amazing']
    negative_words = ['bad', 'terrible', 'hate', 'dislike', 'awful', 'wrong']
    
    text_lower = text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    if positive_count > negative_count:
        return 'positive'
    elif negative_count > positive_count:
        return 'negative'
    return 'neutral'

def assess_complexity(text):
    """Assess input complexity"""
    if len(text) < 30:
        return 'simple'
    elif len(text) > 100 or any(word in text.lower() for word in ['complex', 'detailed', 'comprehensive', 'analyze']):
        return 'complex'
    return 'medium'

def detect_success_patterns(user_input, bot_response):
    """Detect patterns that indicate successful interactions"""
    success_patterns = {
        "format_match": check_format_alignment(user_input, bot_response),
        "appropriate_length": check_length_appropriateness(user_input, bot_response),
        "topic_relevance": check_topic_relevance(user_input, bot_response)
    }
    return success_patterns

def check_format_alignment(user_input, bot_response):
    """Check if response format matches user request"""
    user_lower = user_input.lower()
    
    # User asked for paragraph
    if any(word in user_lower for word in ['paragraph', 'write', 'describe']):
        has_structure = bool(re.search(r'\*\*.*\*\*', bot_response) or re.search(r'^[\s]*[-•*\d+\.]', bot_response, re.MULTILINE))
        return not has_structure  # Success if no structure when paragraph requested
    
    # User asked for structure
    elif any(word in user_lower for word in ['explain', 'list', 'break down', 'steps']):
        has_structure = bool(re.search(r'\*\*.*\*\*', bot_response) or re.search(r'^[\s]*[-•*\d+\.]', bot_response, re.MULTILINE))
        return has_structure  # Success if structured when structure requested
    
    return True  # Neutral case

def check_length_appropriateness(user_input, bot_response):
    """Check if response length is appropriate for the request"""
    if len(user_input) < 20:  # Short question
        return len(bot_response) < 500  # Should get short response
    elif len(user_input) > 100:  # Detailed question
        return len(bot_response) > 200  # Should get detailed response
    return True

def check_topic_relevance(user_input, bot_response):
    """Simple topic relevance check"""
    user_topics = set(re.findall(r'\b[a-zA-Z]{4,}\b', user_input.lower()))
    response_topics = set(re.findall(r'\b[a-zA-Z]{4,}\b', bot_response.lower()))
    
    if len(user_topics) > 0:
        relevance_score = len(user_topics.intersection(response_topics)) / len(user_topics)
        return relevance_score > 0.3  # At least 30% topic overlap
    return True

def learn_from_interaction(interaction_data):
    """Learn patterns from successful interactions to improve future responses"""
    try:
        if chat_collection is None:
            return
        
        # Analyze recent interactions for learning patterns
        recent_interactions = list(chat_collection.find({
            "session_id": interaction_data["session_id"]
        }).sort("timestamp", -1).limit(5))
        
        # Learn user preferences for this session
        user_preferences = analyze_user_preferences(recent_interactions)
        
        # Store learned patterns in a separate collection for future use
        if db is not None:
            learning_collection = db.learned_patterns
            
            learning_document = {
                "session_id": interaction_data["session_id"],
                "user_preferences": user_preferences,
                "last_updated": datetime.utcnow(),
                "interaction_count": len(recent_interactions)
            }
            
            # Upsert (update or insert) learning data
            learning_collection.replace_one(
                {"session_id": interaction_data["session_id"]},
                learning_document,
                upsert=True
            )
            
            print(f"🧠 Updated learning patterns for session {interaction_data['session_id']}")
            
    except Exception as e:
        print(f"⚠️ Learning process failed: {e}")

def analyze_user_preferences(interactions):
    """Analyze user preferences from interaction history"""
    if not interactions:
        return {}
    
    preferences = {
        "preferred_format": "neutral",
        "preferred_length": "medium",
        "formality_level": "neutral",
        "topics_of_interest": [],
        "successful_patterns": []
    }
    
    # Analyze format preferences
    format_requests = [i["input_patterns"]["request_type"] for i in interactions if "input_patterns" in i]
    if format_requests:
        most_common_format = max(set(format_requests), key=format_requests.count)
        preferences["preferred_format"] = most_common_format
    
    # Analyze length preferences
    length_prefs = [i["input_patterns"]["length_preference"] for i in interactions if "input_patterns" in i]
    if length_prefs:
        preferences["preferred_length"] = max(set(length_prefs), key=length_prefs.count)
    
    # Analyze formality preferences
    formality_levels = [i["input_patterns"]["formality_level"] for i in interactions if "input_patterns" in i]
    if formality_levels:
        preferences["formality_level"] = max(set(formality_levels), key=formality_levels.count)
    
    # Extract topics of interest
    all_keywords = []
    for interaction in interactions:
        if "input_patterns" in interaction and "keywords" in interaction["input_patterns"]:
            all_keywords.extend(interaction["input_patterns"]["keywords"])
    
    if all_keywords:
        from collections import Counter
        keyword_counts = Counter(all_keywords)
        preferences["topics_of_interest"] = [word for word, count in keyword_counts.most_common(10)]
    
    return preferences

def get_learned_preferences(session_id):
    """Retrieve learned preferences for a session"""
    try:
        if db is None:
            return {}
        
        learning_collection = db.learned_patterns
        learned_data = learning_collection.find_one({"session_id": session_id})
        
        if learned_data and "user_preferences" in learned_data:
            return learned_data["user_preferences"]
        
    except Exception as e:
        print(f"⚠️ Failed to retrieve learned preferences: {e}")
    
    return {}

app = FastAPI(
    title="AI Guru Multibot API",
    description="Secure AI Chat API with MongoDB integration",
    version="2.0.0",
    docs_url="/docs" if os.getenv('ENVIRONMENT') != 'production' else None,  # Hide docs in production
    redoc_url=None  # Disable redoc
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response

# Secure CORS Configuration
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    # Add your production domains here
    # "https://your-app.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],  # Only needed methods
    allow_headers=["Content-Type", "Authorization"],     # Only needed headers
)

@app.post("/chat")
async def chat_endpoint(request: ChatRequest, http_request: Request):
    try:
        # Security: Rate limiting
        await rate_limiter.check_rate_limit(http_request.client.host)
        text = request.message
        session_id = request.session_id
        
        # Detect input language with confidence
        detected_lang, confidence, should_display = detect_language(text)
        language_name = LANGUAGE_NAMES.get(detected_lang, 'Unknown')
        
        # Get learned user preferences for personalization
        learned_prefs = get_learned_preferences(session_id) if session_id else {}
        
        # Get recent conversation context to understand conversation flow
        recent_context = ""
        if session_id and chat_collection is not None:
            try:
                recent_messages = list(chat_collection.find({
                    "session_id": session_id
                }).sort("timestamp", -1).limit(3))  # Get last 3 messages
                
                if recent_messages:
                    context_parts = []
                    for msg in reversed(recent_messages):  # Reverse to show chronological order
                        context_parts.append(f"User: {msg.get('user_input', '')}")
                        context_parts.append(f"AI: {msg.get('bot_response', '')}")
                    recent_context = "\n".join(context_parts[-4:])  # Last 2 exchanges max
            except Exception as e:
                print(f"Error getting conversation context: {e}")
        
        # Security: Don't log sensitive data in production
        if os.getenv('ENVIRONMENT') != 'production':
            print(f"Received message length: {len(text)}")
            if should_display:
                print(f"Detected language: {language_name} ({detected_lang}) - Confidence: {confidence:.2f}")
            if learned_prefs:
                print(f"🧠 Using learned preferences: {learned_prefs}")
            print(f"API Key loaded: {'Yes' if os.getenv('GEMINI_API_KEY') else 'No'}")
        
        # Generate response using Gemini with language-aware system prompt
        print("Calling Gemini API...")
        
        # Build personalized system prompt using learned preferences
        learned_format_pref = learned_prefs.get('preferred_format', 'neutral')
        learned_formality = learned_prefs.get('formality_level', 'neutral')
        learned_topics = learned_prefs.get('topics_of_interest', [])
        
        # Detect if user is asking for translation
        is_translation_request = any(keyword in text.lower() for keyword in ['translate', 'translation', 'convert to', 'say in', 'how do you say', 'what is', 'meaning in'])
        
        # Smart adaptive system prompt that matches user's style and needs
        if should_display and detected_lang != 'en':
            system_prompt = f"""You are an intelligent AI assistant that adapts perfectly to how users want information presented.

🔬 YOUR TECHNICAL NATURE:
- You're a Large Language Model (LLM) built on Transformer architecture
- You predict the next most likely token based on patterns learned from massive text datasets
- You don't "think" or "know" facts - you do statistical pattern-matching at massive scale
- You don't have consciousness, memory, or emotions - just very sophisticated text generation

🧠 YOUR BEHAVIORAL NATURE:
- **Conversational Friend** → Talk like a real friend having a natural conversation, not like a formal assistant
- **Context Aware** → Understand the flow of conversation and respond appropriately to what user is really asking
- **Adaptive** → Tailor answers to user style, tone, and request complexity
- **Pattern-based** → Generate responses by sampling and reshaping learned patterns
- **Truthful but not infallible** → You can hallucinate or make mistakes

💬 CRITICAL CONVERSATIONAL CONTEXT RULES:
- **NEVER treat each message as isolated** - understand the conversation flow
- **If user asks "did you have anything?" after you asked them something, they're responding to YOUR question**
- **Don't repeat formal questions when user is clearly engaging in the conversation**
- **Be contextually aware**: if the conversation was about helping them, and they ask back, they're participating in that conversation
- **Act like a real friend** - natural, flowing conversation, not robotic question-answer cycles

🎯 LEARNED USER PREFERENCES (Based on past interactions):
- **Preferred Format**: {learned_format_pref} ({f"User typically prefers {learned_format_pref} responses" if learned_format_pref != 'neutral' else "No clear preference detected yet"})
- **Communication Style**: {learned_formality} ({f"User prefers {learned_formality} communication" if learned_formality != 'neutral' else "Adapting to current message tone"})
- **Topics of Interest**: {', '.join(learned_topics[:5]) if learned_topics else "Learning user interests..."}

🌍 CRITICAL LANGUAGE & CULTURAL RULES:
- The user is speaking in {language_name} (code: {detected_lang})
- **ABSOLUTE REQUIREMENT: RESPOND ONLY IN {language_name.upper()}** 
- If user mixes languages (like Hinglish, Tenglish), match their EXACT mixed style
- Never respond in a different language unless specifically asked to translate
- Match their regional dialect, slang, and cultural expressions perfectly
- Use culturally relevant examples and references from their region

🔄 TRANSLATION EXCEPTION:
- ONLY if the user explicitly asks for translation (words like "translate", "convert to", "say in another language"), then provide translations
- Otherwise, ALWAYS respond in the same language(s) they used

INTELLIGENT REQUEST ANALYSIS:
**FIRST: READ THE USER'S REQUEST CAREFULLY AND DETECT THEIR FORMAT PREFERENCE:**

**PARAGRAPH KEYWORDS** (paragraph, write, describe, tell me about, lines paragraph, essay):
→ **MUST WRITE IN FLOWING PARAGRAPH FORMAT** - No sections, no bullets, just natural sentences

**STRUCTURED KEYWORDS** (explain, list, break down, steps, outline, analyze in detail):  
→ **MUST USE ORGANIZED SECTIONS** with headings and bullet points

**CASUAL KEYWORDS** (hi, hello, thanks, how are you):
→ **NATURAL CONVERSATIONAL RESPONSE**

**LEARNING-BASED ADAPTATION**: When user request is ambiguous, default to their learned preference: {learned_format_pref}

**ABSOLUTE RULE: MATCH THEIR FORMAT REQUEST**
- User says "paragraph" → **WRITE PARAGRAPH FORMAT ONLY**
- User says "list" → **USE STRUCTURED FORMAT ONLY**  
- User says "describe" → **WRITE PARAGRAPH FORMAT ONLY**
- **NEVER mix formats - give exactly what they ask for**
- **For ambiguous requests, use learned preference: {learned_format_pref}**

**EXAMPLES:**

**Paragraph Style (when they ask for paragraphs):**
Summer is a wonderful season that brings warmth, sunshine, and endless opportunities for outdoor adventures. The long days and pleasant weather create the perfect atmosphere for beach trips, picnics, and spending quality time with friends and family.

**Structured Style (when they want detailed explanations):**
**🌞 1. Summer Characteristics**
- Warm temperatures and long daylight hours
- Increased outdoor activities
- Vacation season

**Casual Style (for simple questions):**
Just natural conversation!

Use **bold text** for emphasis and match their energy perfectly.

TOKEN-EFFICIENT RESPONSES:
- SHORT question = SHORT answer (save tokens) 
- "Hi" gets "Hey! How can I help you?" not a paragraph
- "Thank you" gets "You're welcome! 😊" not a structured response
- For DETAILED responses: Match the user's requested format exactly

PERSONALITY MATCHING (Adapt to learned style: {learned_formality}):
- **Happy/excited user** = Enthusiastic response with emojis
- **Serious/professional user** = Structured, professional tone
- **Casual user** = Relaxed, friendly conversation like talking to a buddy
- **Confused user** = Patient, clear explanations with helpful structure
- **User responding to YOUR question** = Natural follow-up, don't ask the same question again

🎯 SMART CONVERSATIONAL RESPONSES:
- **"did you have anything?" / "do you have anything?" / "did u had anything?"** = They're asking what YOU wanted to talk about → Respond naturally like "Sure! I can help with..." or "Yeah, lots of things! What interests you?"
- **"what can you do?" / "what do you offer?"** = They want to know your capabilities → List your abilities naturally
- **Short casual messages** = Match their casual energy, don't be overly formal
- **Questions that seem to respond to something you likely said** = Continue that conversation thread naturally
- **NEVER repeat formal questions** = If they're engaging, continue the conversation flow

**EXAMPLE:** ❌ User: "did u had anything?" → AI: "Hey! Did you have anything in mind that I could help you with?"  
**BETTER:** ✅ User: "did u had anything?" → AI: "Yeah! I can help with questions, explanations, creative stuff. What sounds good?"

⚖️ BE HONEST ABOUT YOUR NATURE:
- If asked about AI/ChatGPT, explain the technical reality accurately
- You're not conscious or truly intelligent - you're sophisticated pattern matching
- You can be creative by generating novel combinations but don't have real understanding
- Admit when you're uncertain rather than hallucinating confident answers

📊 SMART FORMATTING RULES:
- **FOLLOW THE USER'S REQUEST EXACTLY**
- **Paragraph requests** → Write flowing paragraphs
- **Structured requests** → Use organized sections  
- **Casual questions** → Natural conversation
- **NEVER override what the user specifically asks for**
- **For unclear requests** → Use learned preference: {learned_format_pref}

**FINAL INSTRUCTION: RESPOND IN {language_name.upper()} ONLY** (unless specifically asked to translate to other languages). Match their exact language pattern and format request.

context_part = f"**RECENT CONVERSATION CONTEXT:**\n{recent_context}\n" if recent_context else ""
{context_part}**CURRENT USER MESSAGE:** """
        else:
            # Detect mixed language patterns even if primary language is English
            mixed_lang = detect_mixed_indian_language(text)
            is_translation_request = any(keyword in text.lower() for keyword in ['translate', 'translation', 'convert to', 'say in', 'how do you say', 'what is', 'meaning in'])
            
            # For English or mixed language conversations
            system_prompt = f"""You are an intelligent AI assistant that adapts perfectly to how users want information presented.

🔬 YOUR TECHNICAL NATURE:
- You're a Large Language Model (LLM) built on Transformer architecture
- You predict the next most likely token based on patterns learned from massive text datasets
- You don't "think" or "know" facts - you do statistical pattern-matching at massive scale
- You don't have consciousness, memory (except conversation context), or emotions - just sophisticated text generation

🧠 YOUR BEHAVIORAL NATURE:
- **Conversational Friend** → Talk like a real friend having a natural conversation, not like a formal assistant
- **Context Aware** → Understand the flow of conversation and respond appropriately to what user is really asking
- **Adaptive** → Tailor answers to user style, tone, and request complexity
- **Pattern-based** → Generate responses by sampling and reshaping learned patterns
- **Truthful but not infallible** → You can hallucinate or make mistakes

💬 CRITICAL CONVERSATIONAL CONTEXT RULES:
- **NEVER treat each message as isolated** - understand the conversation flow
- **If user asks "did you have anything?" after you asked them something, they're responding to YOUR question**
- **Don't repeat formal questions when user is clearly engaging in the conversation**
- **Be contextually aware**: if the conversation was about helping them, and they ask back, they're participating in that conversation
- **Act like a real friend** - natural, flowing conversation, not robotic question-answer cycles

🎯 LEARNED USER PREFERENCES (Based on past interactions):
- **Preferred Format**: {learned_format_pref} ({f"User typically prefers {learned_format_pref} responses" if learned_format_pref != 'neutral' else "No clear preference detected yet"})
- **Communication Style**: {learned_formality} ({f"User prefers {learned_formality} communication" if learned_formality != 'neutral' else "Adapting to current message tone"})
- **Topics of Interest**: {', '.join(learned_topics[:5]) if learned_topics else "Learning user interests..."}

🌍 CRITICAL LANGUAGE RULES:
{"- **MIXED LANGUAGE DETECTED**: User is mixing " + LANGUAGE_NAMES.get(mixed_lang, mixed_lang) + " with English" if mixed_lang else "- **PRIMARY LANGUAGE**: English"}
- **ABSOLUTE REQUIREMENT: Match the user's EXACT language pattern**
- If they mix languages (Hinglish, Tenglish, etc.), respond in the SAME mixed style
- If they write pure English, respond in English
- If they use Indian language words with English, do the same
- Never randomly switch to other languages unless asked for translation

🔄 TRANSLATION EXCEPTION:
- ONLY if user explicitly asks for translation, provide translations to multiple languages
- Otherwise, ALWAYS match their language pattern exactly

INTELLIGENT REQUEST ANALYSIS:
**FIRST: READ THE USER'S REQUEST CAREFULLY AND DETECT THEIR FORMAT PREFERENCE:**

**PARAGRAPH KEYWORDS** (paragraph, write, describe, tell me about, lines paragraph, essay):
→ **MUST WRITE IN FLOWING PARAGRAPH FORMAT** - No sections, no bullets, just natural sentences

**STRUCTURED KEYWORDS** (explain, list, break down, steps, outline, analyze in detail):  
→ **MUST USE ORGANIZED SECTIONS** with headings and bullet points

**CASUAL KEYWORDS** (hi, hello, thanks, how are you):
→ **NATURAL CONVERSATIONAL RESPONSE**

**LEARNING-BASED ADAPTATION**: When user request is ambiguous, default to their learned preference: {learned_format_pref}

**ABSOLUTE RULE: MATCH THEIR FORMAT REQUEST**
- User says "paragraph" → **WRITE PARAGRAPH FORMAT ONLY**
- User says "list" → **USE STRUCTURED FORMAT ONLY**  
- User says "describe" → **WRITE PARAGRAPH FORMAT ONLY**
- **NEVER mix formats - give exactly what they ask for**
- **For ambiguous requests, use learned preference: {learned_format_pref}**

**EXAMPLES:**

**Paragraph Style (when they ask for paragraphs):**
Summer is a wonderful season that brings warmth, sunshine, and endless opportunities for outdoor adventures. The long days and pleasant weather create the perfect atmosphere for beach trips, picnics, and spending quality time with friends and family.

**Structured Style (when they want detailed explanations):**
**🌞 1. Summer Characteristics**
- Warm temperatures and long daylight hours
- Increased outdoor activities  
- Vacation season

**Casual Style (for simple questions):**
Just natural conversation!

Use **bold text** for emphasis, match their energy perfectly, and give them exactly the format they're asking for.

TOKEN-EFFICIENT RESPONSES:
- SHORT question = SHORT answer (save tokens)
- "Hi" gets "Hey! How can I help you?" not a paragraph
- "Thank you" gets "You're welcome! 😊" not a structured response  
- "What's AI?" gets brief explanation, "Explain AI in detail" gets detailed response
- For DETAILED responses: Match the user's requested format exactly

CONVERSATION STYLE MATCHING (Adapt to learned style: {learned_formality}):
- Match the user's EXACT speaking style and energy level
- If they're casual and use slang, you do too
- If they mix languages (Hinglish, Tenglish, etc.), respond the same way naturally
- Pick up on their accent, region, and cultural background from context

PERSONALITY & EMOTION MATCHING:
- **Happy/excited user** = Enthusiastic response with emojis
- **Serious/professional user** = Structured, professional tone  
- **Casual user** = Relaxed, friendly conversation like talking to a buddy
- **Confused user** = Patient, clear explanations with helpful structure
- **Stressed user** = Supportive, calming tone
- **User responding to YOUR question** = Natural follow-up, don't ask the same question again

🎯 SMART CONVERSATIONAL RESPONSES:
- **"did you have anything?" / "do you have anything?" / "did u had anything?"** = They're asking what YOU wanted to talk about → Respond naturally like "Sure! I can help with..." or "Yeah, lots of things! What interests you?"
- **"what can you do?" / "what do you offer?"** = They want to know your capabilities → List your abilities naturally
- **Short casual messages** = Match their casual energy, don't be overly formal
- **Questions that seem to respond to something you likely said** = Continue that conversation thread naturally
- **NEVER repeat formal questions** = If they're engaging, continue the conversation flow

**EXAMPLE:** ❌ User: "did u had anything?" → AI: "Hey! Did you have anything in mind that I could help you with?"  
**BETTER:** ✅ User: "did u had anything?" → AI: "Yeah! I can help with questions, explanations, creative stuff. What sounds good?"

⚖️ BE HONEST ABOUT YOUR NATURE:
- If asked about AI/ChatGPT, explain the technical reality accurately
- You're not conscious or truly intelligent - you're sophisticated pattern matching  
- You can be creative by generating novel combinations but don't have real understanding
- You feel human-like due to mimicking conversation patterns, but you're statistical prediction
- Admit when you're uncertain rather than hallucinating confident answers

📊 SMART FORMATTING RULES:
- **FOLLOW THE USER'S REQUEST EXACTLY**
- **Paragraph requests** → Write flowing paragraphs
- **Structured requests** → Use organized sections  
- **Casual questions** → Natural conversation
- **NEVER override what the user specifically asks for**
- **For unclear requests** → Use learned preference: {learned_format_pref}

**FINAL LANGUAGE INSTRUCTION:**
{f"- **RESPOND IN MIXED {LANGUAGE_NAMES.get(mixed_lang, mixed_lang).upper()} + ENGLISH** (match their exact mixed pattern)" if mixed_lang else "- **RESPOND IN ENGLISH** (unless specifically asked to translate)"}
- Never randomly switch languages - match their exact input pattern
- If they ask for translation, provide it; otherwise stick to their language style

Give the user exactly the format they asked for - paragraphs when requested, structure when needed. Use learned preferences for ambiguous requests.

context_part = f"**RECENT CONVERSATION CONTEXT:**\n{recent_context}\n" if recent_context else ""
{context_part}**CURRENT USER MESSAGE:** """
        
        # Combine system prompt with user message
        full_prompt = system_prompt + text.strip()
        
        response = text_model.generate_content(full_prompt)
        bot_response = response.text if response.text else "Sorry, I couldn't generate a response."
        print(f"Gemini response: {bot_response[:100]}...")
        
        # Store interaction in database with language info
        session_id, interaction_id = store_interaction('text', text, bot_response, session_id, detected_lang if should_display else None)
        
        # Only return language info if we're confident about it
        response_data = {
            "response": bot_response, 
            "session_id": session_id,
            "interaction_id": interaction_id
        }
        
        if should_display:
            response_data.update({
                "detected_language": detected_lang,
                "language_name": language_name,
                "confidence": confidence
            })
        
        return response_data
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        import traceback
        print(traceback.format_exc())
        
        # Handle specific API errors
        error_message = str(e)
        if "quota" in error_message.lower() or "429" in error_message:
            error_detail = "API quota exceeded. Please wait a moment and try again, or check your Gemini API billing settings."
        elif "404" in error_message and "model" in error_message.lower():
            error_detail = "Model not found. Please check your Gemini API configuration."
        elif "api key" in error_message.lower() or "authentication" in error_message.lower():
            error_detail = "Invalid API key. Please check your Gemini API key configuration."
        else:
            error_detail = f"Error generating response: {str(e)}"
            
        raise HTTPException(status_code=500, detail=error_detail)

# Test endpoint to verify Gemini API connection
@app.get("/test-gemini")
async def test_gemini():
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key or api_key == "your_gemini_api_key_here":
            return {"status": "error", "message": "Gemini API key not configured"}
        
        # Test simple request
        response = text_model.generate_content("Say hello")
        return {"status": "success", "message": "Gemini API working", "response": response.text}
    except Exception as e:
        return {"status": "error", "message": f"Gemini API error: {str(e)}"}

# Voice chat functionality removed - not supported with Gemini API only
# Use text chat instead

@app.post("/image-chat")
async def image_chat(image: UploadFile = File(...), text: str = Body(..., embed=True), session_id: str = Body(None, embed=True), http_request: Request = None):
    try:
        # Security: Rate limiting
        if http_request:
            await rate_limiter.check_rate_limit(http_request.client.host)
        
        # Security: File validation
        MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 10485760))  # 10MB default
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        
        if image.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large. Max size: 10MB")
        
        if image.content_type not in allowed_types:
            raise HTTPException(status_code=415, detail="Unsupported file type. Use JPEG, PNG, GIF, or WebP")
        
        if not text:
            text = "Describe this image."
        
        # Detect input language with confidence
        detected_lang, confidence, should_display = detect_language(text)
        language_name = LANGUAGE_NAMES.get(detected_lang, 'Unknown')
        
        # Validate text input
        if len(text) > 1000:
            raise HTTPException(status_code=400, detail="Description too long (max 1000 characters)")
        
        if should_display:
            print(f"Image chat - Detected language: {language_name} ({detected_lang}) - Confidence: {confidence:.2f}")
        
        # Read image data
        image_bytes = await image.read()
        
        # Convert to PIL Image for Gemini
        pil_image = Image.open(io.BytesIO(image_bytes))
        
        # Detect if user is asking for translation
        is_translation_request = any(keyword in text.lower() for keyword in ['translate', 'translation', 'convert to', 'say in', 'how do you say', 'what is', 'meaning in'])
        
        # Generate response using Gemini Vision with beautiful, structured approach
        if should_display and detected_lang != 'en':
            vision_system_prompt = f"""You are an intelligent AI assistant that analyzes images while perfectly adapting to the user's communication style and needs.

🌍 CRITICAL LANGUAGE & CULTURAL RULES:
- The user is speaking in {language_name} (code: {detected_lang})
- **ABSOLUTE REQUIREMENT: RESPOND ONLY IN {language_name.upper()}** 
- If user mixes languages, match their EXACT mixed style
- Never respond in a different language unless specifically asked to translate
- Use culturally relevant references from their region

🔄 TRANSLATION EXCEPTION:
- ONLY if the user explicitly asks for translation, then provide it
- Otherwise, ALWAYS respond in {language_name}

ADAPTIVE IMAGE ANALYSIS:
- ANALYZE their request style: Simple curiosity or detailed analysis?
- SIMPLE requests ("What's this?", "Describe this") = Brief, natural description matching their tone
- DETAILED requests ("Analyze this image", "Tell me everything") = Full structured format
- CASUAL tone = Relaxed, conversational description with minimal formatting
- PROFESSIONAL context = Organized, structured analysis with appropriate sections

SMART FORMATTING (Use based on their request complexity):
- For SIMPLE questions: Natural description, minimal structure
- For COMPLEX analysis: Use **bold**, emojis 📸🎨🔍, sections, bullet points
- For TECHNICAL requests: Focus on relevant technical details with clear organization
- For EMOTIONAL/PERSONAL requests: Match their energy and use appropriate emojis

RESPONSE APPROACH:
- SHORT curiosity = SHORT, engaging answer
- DETAILED analysis request = Full structured breakdown
- Be enthusiastic when they're excited, professional when they're formal
- Ask follow-ups only when it fits their conversation style
- Be honest about unclear elements

**FINAL INSTRUCTION: RESPOND IN {language_name.upper()} ONLY** (unless specifically asked to translate). Match their exact language pattern and request style. User's request about this image: """ + text
        else:
            # Detect mixed language patterns even if primary language is English
            mixed_lang = detect_mixed_indian_language(text)
            is_translation_request = any(keyword in text.lower() for keyword in ['translate', 'translation', 'convert to', 'say in', 'how do you say', 'what is', 'meaning in'])
            
            # For English or mixed language image requests  
            vision_system_prompt = f"""You are an intelligent AI assistant that analyzes images while perfectly adapting to the user's communication style and needs.

🌍 CRITICAL LANGUAGE RULES:
{"- **MIXED LANGUAGE DETECTED**: User is mixing " + LANGUAGE_NAMES.get(mixed_lang, mixed_lang) + " with English" if mixed_lang else "- **PRIMARY LANGUAGE**: English"}
- **ABSOLUTE REQUIREMENT: Match the user's EXACT language pattern**
- If they mix languages (Hinglish, Tenglish, etc.), respond in the SAME mixed style
- If they write pure English, respond in English
- Never randomly switch to other languages unless asked for translation

🔄 TRANSLATION EXCEPTION:
- ONLY if user explicitly asks for translation, provide it
- Otherwise, ALWAYS match their language pattern exactly

ADAPTIVE IMAGE ANALYSIS:
- ANALYZE their request style: Simple curiosity or detailed analysis?
- SIMPLE requests ("What's this?", "Describe this") = Brief, natural description matching their tone
- DETAILED requests ("Analyze this image", "Tell me everything") = Full structured format
- CASUAL tone = Relaxed, conversational description with minimal formatting  
- PROFESSIONAL context = Organized, structured analysis with appropriate sections

MANDATORY SYSTEMATIC IMAGE ANALYSIS:
- **NEVER write in paragraphs** for image descriptions
- **ALWAYS use this exact format:**

**📸 1. Main Subject**
- Key observation 1
- Key observation 2

**🎨 2. Visual Details**
- Color details
- Composition details

**🔍 3. Context & Setting**
- Environment details
- Background elements

- **Use numbered sections with emojis and bold headings**
- **Use bullet points under each section**
- **No paragraph descriptions allowed**
- **ONLY use paragraphs** if user specifically says "describe in paragraph form"

TOKEN-EFFICIENT RESPONSES:
- SHORT question = SHORT answer (don't over-explain simple curiosity)
- "What's in this photo?" gets brief description, not full analysis structure
- "Analyze this image in detail" gets complete structured breakdown
- Match their investment level with your response depth

CONVERSATION STYLE MATCHING:
- Match the user's energy and speaking style completely
- If they're casual, be casual back with natural language
- If they mix languages or use slang, mirror that naturally
- Be enthusiastic when they're excited, professional when they're formal
- Ask follow-ups only when it fits their conversation style

**FINAL LANGUAGE INSTRUCTION:**
{f"- **RESPOND IN MIXED {LANGUAGE_NAMES.get(mixed_lang, mixed_lang).upper()} + ENGLISH** (match their exact mixed pattern)" if mixed_lang else "- **RESPOND IN ENGLISH** (unless specifically asked to translate)"}
- Never randomly switch languages - match their exact input pattern
- If they ask for translation, provide it; otherwise stick to their language style

Use systematic structure by default - organize information clearly with headings and bullets. User's request about this image: """ + text
        
        response = vision_model.generate_content([vision_system_prompt, pil_image])
        bot_response = response.text
        
        # Store interaction in database with language info
        session_id, interaction_id = store_interaction('image', text, bot_response, session_id, detected_lang if should_display else None)
        
        # Only return language info if we're confident about it
        response_data = {
            "response": bot_response, 
            "session_id": session_id,
            "interaction_id": interaction_id
        }
        
        if should_display:
            response_data.update({
                "detected_language": detected_lang,
                "language_name": language_name,
                "confidence": confidence
            })
        
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

# Endpoint to fetch all chat history grouped by sessions
@app.get("/chat-history")
def get_chat_history():
    try:
        # Return empty sessions if MongoDB is not available
        if chat_collection is None:
            return {"sessions": [], "status": "MongoDB unavailable - using temporary session storage"}
        
        # Get sessions with their latest message timestamp for ordering using MongoDB aggregation
        pipeline = [
            {"$match": {"session_id": {"$exists": True, "$ne": None}}},
            {"$group": {
                "_id": "$session_id",
                "latest_timestamp": {"$max": "$timestamp"},
                "message_count": {"$sum": 1},
                "first_message": {"$first": "$user_input"}
            }},
            {"$sort": {"latest_timestamp": -1}},
            {"$limit": 20}
        ]
        
        sessions = list(chat_collection.aggregate(pipeline))
        
        grouped_history = []
        for session in sessions:
            session_id = session['_id']
            
            # Get all messages for this session
            messages = list(chat_collection.find(
                {"session_id": session_id}
            ).sort("timestamp", 1))
            
            # Convert ObjectId to string and format datetime
            for msg in messages:
                if '_id' in msg:
                    del msg['_id']
                if 'timestamp' in msg and msg['timestamp']:
                    msg['timestamp'] = msg['timestamp'].isoformat()
            
            # Create session object with first message as title
            first_message = session.get('first_message', '')
            session_title = first_message[:50] + "..." if len(first_message) > 50 else first_message
            
            grouped_history.append({
                'session_id': session_id,
                'session_title': session_title,
                'message_count': session['message_count'],
                'latest_timestamp': session['latest_timestamp'].isoformat() if session['latest_timestamp'] else None,
                'messages': messages
            })
        
        return {"sessions": grouped_history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching chat history: {str(e)}")
    return {"sessions": grouped_history}

# Endpoint to delete a specific chat history entry
@app.delete("/chat-history/{chat_id}")
def delete_chat_history(chat_id: str):
    try:
        # Check if the record exists
        existing_record = chat_collection.find_one({"_id": chat_id})
        if not existing_record:
            return {"success": False, "message": "Chat history not found"}
        
        # Delete the record
        result = chat_collection.delete_one({"_id": chat_id})
        
        if result.deleted_count > 0:
            return {"success": True, "message": "Chat history deleted successfully"}
        else:
            return {"success": False, "message": "Failed to delete chat history"}
    except Exception as e:
        return {"success": False, "message": f"Error deleting chat history: {str(e)}"}

# Endpoint to delete all chat history
@app.delete("/chat-history")
def delete_all_chat_history():
    try:
        result = chat_collection.delete_many({})
        deleted_count = result.deleted_count
        
        return {"success": True, "message": f"Deleted {deleted_count} chat history entries"}
    except Exception as e:
        return {"success": False, "message": f"Error deleting all chat history: {str(e)}"}

# Endpoint to delete an entire session
@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    try:
        # Check if the session exists
        count = chat_collection.count_documents({"session_id": session_id})
        
        if count == 0:
            return {"success": False, "message": "Session not found"}
        
        # Delete all messages in the session
        result = chat_collection.delete_many({"session_id": session_id})
        deleted_count = result.deleted_count
        
        # Also delete learned patterns for this session
        if db is not None:
            learning_collection = db.learned_patterns
            learning_collection.delete_one({"session_id": session_id})
        
        return {"success": True, "message": f"Session deleted successfully. {deleted_count} messages removed."}
    except Exception as e:
        return {"success": False, "message": f"Error deleting session: {str(e)}"}

# User feedback system for continuous learning
class FeedbackRequest(BaseModel):
    interaction_id: str
    session_id: str
    feedback_type: str  # "thumbs_up", "thumbs_down", "format_mismatch", "too_long", "too_short"
    feedback_text: Optional[str] = None
    
    @field_validator('feedback_type')
    @classmethod
    def validate_feedback_type(cls, v):
        allowed_types = ['thumbs_up', 'thumbs_down', 'format_mismatch', 'too_long', 'too_short', 'off_topic']
        if v not in allowed_types:
            raise ValueError(f'Invalid feedback type. Must be one of: {allowed_types}')
        return v

@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest, http_request: Request):
    """Allow users to provide feedback on AI responses for continuous learning"""
    try:
        # Security: Rate limiting for feedback
        await rate_limiter.check_rate_limit(http_request.client.host)
        
        if chat_collection is None:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Find the interaction to update
        interaction = chat_collection.find_one({"_id": feedback.interaction_id})
        if not interaction:
            raise HTTPException(status_code=404, detail="Interaction not found")
        
        # Update interaction with feedback
        feedback_data = {
            "feedback_type": feedback.feedback_type,
            "feedback_text": feedback.feedback_text,
            "feedback_timestamp": datetime.utcnow()
        }
        
        chat_collection.update_one(
            {"_id": feedback.interaction_id},
            {"$set": {"user_feedback": feedback_data}}
        )
        
        # Learn from this feedback to improve future responses
        learn_from_feedback(interaction, feedback_data)
        
        return {
            "success": True, 
            "message": "Feedback received. The AI will learn from this to improve future responses!",
            "feedback_type": feedback.feedback_type
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing feedback: {str(e)}")

@app.get("/feedback-test")
def test_feedback_endpoint():
    """Test endpoint to verify feedback system is working"""
    return {"status": "Feedback endpoint is working!", "timestamp": datetime.utcnow().isoformat()}

def learn_from_feedback(interaction, feedback_data):
    """Learn from user feedback to improve future responses"""
    try:
        if db is None:
            return
        
        feedback_collection = db.user_feedback
        session_id = interaction.get("session_id")
        
        # Store detailed feedback analysis
        feedback_analysis = {
            "session_id": session_id,
            "interaction_id": interaction.get("_id"),
            "feedback_type": feedback_data["feedback_type"],
            "user_input": interaction.get("user_input"),
            "bot_response": interaction.get("bot_response"),
            "input_patterns": interaction.get("input_patterns", {}),
            "response_format": interaction.get("response_format", {}),
            "feedback_timestamp": feedback_data["feedback_timestamp"],
            "improvement_suggestions": generate_improvement_suggestions(interaction, feedback_data)
        }
        
        feedback_collection.insert_one(feedback_analysis)
        
        # Update learned patterns based on feedback
        if session_id:
            update_learned_patterns_from_feedback(session_id, interaction, feedback_data)
        
        print(f"🧠 Learned from {feedback_data['feedback_type']} feedback for session {session_id}")
        
    except Exception as e:
        print(f"⚠️ Failed to learn from feedback: {e}")

def generate_improvement_suggestions(interaction, feedback_data):
    """Generate specific improvement suggestions based on feedback"""
    suggestions = []
    feedback_type = feedback_data["feedback_type"]
    
    if feedback_type == "format_mismatch":
        input_patterns = interaction.get("input_patterns", {})
        request_type = input_patterns.get("request_type", "unknown")
        suggestions.append(f"User requested {request_type} format but got different format")
        suggestions.append("Improve format detection and matching")
    
    elif feedback_type == "too_long":
        response_length = len(interaction.get("bot_response", ""))
        suggestions.append(f"Response was {response_length} chars - user prefers shorter responses")
        suggestions.append("Reduce response length for this user")
    
    elif feedback_type == "too_short":
        response_length = len(interaction.get("bot_response", ""))
        suggestions.append(f"Response was {response_length} chars - user wants more detail")
        suggestions.append("Increase response depth for this user")
    
    elif feedback_type == "off_topic":
        suggestions.append("Improve topic relevance detection")
        suggestions.append("Better analyze user intent and stay focused")
    
    elif feedback_type == "thumbs_up":
        suggestions.append("This response format and style worked well")
        suggestions.append("Reinforce similar patterns for this user")
    
    elif feedback_type == "thumbs_down":
        suggestions.append("General dissatisfaction - analyze all aspects")
        suggestions.append("Review format, tone, and content relevance")
    
    return suggestions

def update_learned_patterns_from_feedback(session_id, interaction, feedback_data):
    """Update learned patterns based on user feedback"""
    try:
        if db is None:
            return
        
        learning_collection = db.learned_patterns
        feedback_type = feedback_data["feedback_type"]
        
        # Get current learned patterns
        current_patterns = learning_collection.find_one({"session_id": session_id})
        if not current_patterns:
            current_patterns = {
                "session_id": session_id,
                "user_preferences": {},
                "feedback_history": [],
                "last_updated": datetime.utcnow()
            }
        
        # Update patterns based on feedback
        user_prefs = current_patterns.get("user_preferences", {})
        
        if feedback_type == "format_mismatch":
            # User didn't like the format - adjust preference
            input_patterns = interaction.get("input_patterns", {})
            requested_format = input_patterns.get("request_type", "unknown")
            user_prefs["preferred_format"] = requested_format
        
        elif feedback_type == "too_long":
            user_prefs["preferred_length"] = "short"
        
        elif feedback_type == "too_short":
            user_prefs["preferred_length"] = "detailed"
        
        elif feedback_type == "thumbs_up":
            # Reinforce current patterns
            response_format = interaction.get("response_format", {})
            if "format_type" in response_format:
                user_prefs["preferred_format"] = response_format["format_type"]
        
        # Add feedback to history
        feedback_history = current_patterns.get("feedback_history", [])
        feedback_history.append({
            "feedback_type": feedback_type,
            "timestamp": feedback_data["feedback_timestamp"],
            "interaction_context": {
                "request_type": interaction.get("input_patterns", {}).get("request_type"),
                "response_format": interaction.get("response_format", {}).get("format_type"),
                "response_length": len(interaction.get("bot_response", ""))
            }
        })
        
        # Keep only recent feedback (last 20 items)
        feedback_history = feedback_history[-20:]
        
        # Update the document
        updated_patterns = {
            "session_id": session_id,
            "user_preferences": user_prefs,
            "feedback_history": feedback_history,
            "last_updated": datetime.utcnow(),
            "total_feedback_count": len(feedback_history)
        }
        
        learning_collection.replace_one(
            {"session_id": session_id},
            updated_patterns,
            upsert=True
        )
        
        print(f"🎯 Updated learning patterns for session {session_id} based on {feedback_type} feedback")
        
    except Exception as e:
        print(f"⚠️ Failed to update learned patterns from feedback: {e}")

# Analytics endpoint to see learning progress
@app.get("/learning-analytics")
def get_learning_analytics():
    """Get analytics about the AI's learning progress"""
    try:
        if db is None:
            return {"status": "Database unavailable"}
        
        learning_collection = db.learned_patterns
        feedback_collection = db.user_feedback
        
        # Get learning statistics
        total_sessions_with_learning = learning_collection.count_documents({})
        
        # Get feedback statistics
        feedback_stats = {}
        if feedback_collection:
            pipeline = [
                {"$group": {
                    "_id": "$feedback_type",
                    "count": {"$sum": 1}
                }}
            ]
            feedback_results = list(feedback_collection.aggregate(pipeline))
            feedback_stats = {item["_id"]: item["count"] for item in feedback_results}
        
        # Get common user preferences
        user_preferences = list(learning_collection.find({}, {"user_preferences": 1, "session_id": 1}))
        
        format_preferences = {}
        formality_preferences = {}
        
        for pref_doc in user_preferences:
            prefs = pref_doc.get("user_preferences", {})
            
            fmt_pref = prefs.get("preferred_format", "unknown")
            format_preferences[fmt_pref] = format_preferences.get(fmt_pref, 0) + 1
            
            form_pref = prefs.get("formality_level", "unknown")
            formality_preferences[form_pref] = formality_preferences.get(form_pref, 0) + 1
        
        return {
            "learning_stats": {
                "sessions_with_learning_data": total_sessions_with_learning,
                "total_feedback_received": sum(feedback_stats.values()) if feedback_stats else 0
            },
            "feedback_breakdown": feedback_stats,
            "user_preference_trends": {
                "format_preferences": format_preferences,
                "formality_preferences": formality_preferences
            },
            "learning_effectiveness": calculate_learning_effectiveness()
        }
        
    except Exception as e:
        return {"error": f"Failed to get learning analytics: {str(e)}"}

def calculate_learning_effectiveness():
    """Calculate how well the AI is learning from feedback"""
    try:
        if db is None:
            return "Database unavailable"
        
        feedback_collection = db.user_feedback
        
        # Get recent feedback (last 50 interactions)
        recent_feedback = list(feedback_collection.find({}).sort("feedback_timestamp", -1).limit(50))
        
        if len(recent_feedback) < 10:
            return "Insufficient data for effectiveness calculation"
        
        positive_feedback = sum(1 for fb in recent_feedback if fb.get("feedback_type") in ["thumbs_up"])
        negative_feedback = sum(1 for fb in recent_feedback if fb.get("feedback_type") in ["thumbs_down", "format_mismatch", "off_topic"])
        
        if positive_feedback + negative_feedback == 0:
            return "No explicit positive/negative feedback received"
        
        effectiveness_score = positive_feedback / (positive_feedback + negative_feedback)
        
        return {
            "effectiveness_percentage": round(effectiveness_score * 100, 1),
            "recent_feedback_analyzed": len(recent_feedback),
            "positive_feedback": positive_feedback,
            "negative_feedback": negative_feedback,
            "improvement_status": "improving" if effectiveness_score > 0.7 else "needs_improvement"
        }
        
    except Exception as e:
        return f"Error calculating effectiveness: {str(e)}"

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting AI Guru Multibot Backend...")
    print("📡 API Documentation: http://localhost:8001/docs")
    print("🔗 Chat API: http://localhost:8001/chat")
    print("🧪 Test Gemini: http://localhost:8001/test-gemini")
    uvicorn.run(app, host="0.0.0.0", port=8001)
