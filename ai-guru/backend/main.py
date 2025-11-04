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
from models import ChatRequest, FeedbackRequest
from collections import defaultdict
from datetime import timedelta
import langdetect
from langdetect import detect, detect_langs, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

import services.gemini_service as gemini_service
import utils
import database
import config

# Set seed for consistent language detection

# Configure Gemini
genai.configure(api_key=config.GEMINI_API_KEY)

# Initialize the generative models
text_model = genai.GenerativeModel('gemini-pro')
vision_model = genai.GenerativeModel('gemini-pro-vision')



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
rate_limiter = RateLimiter(max_requests=config.RATE_LIMIT_MAX_REQUESTS, time_window=config.RATE_LIMIT_TIME_WINDOW)

# Allowed MIME types for image uploads
allowed_types = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp'
]




def store_interaction(input_type, user_input, bot_response, session_id=None, language_code=None, user_feedback=None):
    # Generate session_id if not provided
    if not session_id:
        session_id = str(uuid.uuid4())[:8]  # Short session ID
    
    interaction_id = None
    
    # Only store in MongoDB if connection is available
    if database.is_db_available():
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
                "language_name": utils.LANGUAGE_NAMES.get(language_code, 'Unknown') if language_code else None,
                "timestamp": datetime.utcnow(),
                "user_feedback": user_feedback,  # Store user feedback for learning
                "response_length": len(bot_response) if bot_response else 0,
                "input_patterns": analyze_input_patterns(user_input),
                "response_format": detect_response_format(bot_response),
                "interaction_context": extract_context_features(user_input, bot_response)
            }
            
            # Insert into MongoDB
            database.get_chat_collection().insert_one(document)
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
    if not database.is_db_available():
        return
    try:
        chat_collection = database.get_chat_collection()
        # Analyze recent interactions for learning patterns
        recent_interactions = list(chat_collection.find({
            "session_id": interaction_data["session_id"]
        }).sort("timestamp", -1).limit(5))
        
        # Learn user preferences for this session
        user_preferences = analyze_user_preferences(recent_interactions)
        
        # Store learned patterns in a separate collection for future use
        learning_collection = database.get_learning_collection()
        if learning_collection is not None:
            
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
    if not database.is_db_available():
        return {}
    try:
        learning_collection = database.get_learning_collection()
        if learning_collection is None:
            return {}
        
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
    # response.headers["X-Frame-Options"] = "DENY"
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
        detected_lang, confidence, should_display = utils.detect_language(text)
        language_name = utils.LANGUAGE_NAMES.get(detected_lang, 'Unknown')
        
        # Extract session_id from request
        session_id = request.session_id
        
        # Get learned user preferences for personalization
        learned_prefs = get_learned_preferences(session_id) if session_id else {}
        
        # Get recent conversation context to understand conversation flow
        recent_context = ""
        if session_id and database.is_db_available():
            try:
                recent_messages = list(database.get_chat_collection().find({
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
        
        # Generate response using the Gemini service
        print("Calling Gemini service...")
        bot_response = gemini_service.generate_text_response(
            text, recent_context, learned_prefs, detected_lang, language_name, should_display
        )
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
    except HTTPException as http_exc:
        # Re-raise HTTPException directly
        raise http_exc
    except Exception as e:
        print(f"An unexpected error occurred in chat endpoint: {str(e)}")
        import traceback
        print(traceback.format_exc())
        
        # Handle specific known errors and map to appropriate HTTP responses
        error_message = str(e).lower()
        status_code = 500
        error_detail = "An internal server error occurred while processing your request."

        if "quota" in error_message or "429" in error_message:
            status_code = 429
            error_detail = "API quota exceeded. Please try again later or check your billing settings."
        elif "model not found" in error_message or "404" in error_message:
            status_code = 404
            error_detail = "The requested model is not available. Please check the API configuration."
        elif "api key" in error_message or "authentication" in error_message:
            status_code = 401
            error_detail = "Invalid API key. Please check your Gemini API key configuration."
        
        raise HTTPException(status_code=status_code, detail=error_detail)

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
        if image.size > config.MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File too large. Max size: {config.MAX_FILE_SIZE // 1024 // 1024}MB")
        
        if image.content_type not in allowed_types:
            raise HTTPException(status_code=415, detail="Unsupported file type. Use JPEG, PNG, GIF, or WebP")
        
        if not text:
            text = "Describe this image."
        
        # Detect input language with confidence
        detected_lang, confidence, should_display = utils.detect_language(text)
        language_name = utils.LANGUAGE_NAMES.get(detected_lang, 'Unknown')
        
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
        
        # Generate response using the Gemini service
        bot_response = gemini_service.generate_image_response(
            pil_image, text, detected_lang, language_name, should_display
        )
        
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
    except HTTPException as http_exc:
        # Re-raise HTTPException directly
        raise http_exc
    except Exception as e:
        print(f"An unexpected error occurred in image_chat endpoint: {str(e)}")
        # Optionally log traceback here
        raise HTTPException(status_code=500, detail="An internal server error occurred while processing the image.")

# Endpoint to fetch all chat history grouped by sessions
@app.get("/chat-history")
def get_chat_history():
    try:
        # Return empty sessions if MongoDB is not available
        if not database.is_db_available():
            return {"sessions": [], "status": "MongoDB unavailable - using temporary session storage"}
        
        chat_collection = database.get_chat_collection()
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
        print(f"An unexpected error occurred while fetching chat history: {str(e)}")
        # Optionally log traceback here
        raise HTTPException(status_code=500, detail="An internal server error occurred while fetching chat history.")
    return {"sessions": grouped_history}

# Endpoint to delete a specific chat history entry
@app.delete("/chat-history/{chat_id}")
def delete_chat_history(chat_id: str):
    if not database.is_db_available():
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        chat_collection = database.get_chat_collection()
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
        print(f"An unexpected error occurred while deleting chat history: {str(e)}")
        # Optionally log traceback here
        raise HTTPException(status_code=500, detail="An internal server error occurred while deleting chat history.")

# Endpoint to delete all chat history
@app.delete("/chat-history")
def delete_all_chat_history():
    if not database.is_db_available():
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        result = database.get_chat_collection().delete_many({})
        deleted_count = result.deleted_count
        
        return {"success": True, "message": f"Deleted {deleted_count} chat history entries"}
    except Exception as e:
        print(f"An unexpected error occurred while deleting all chat history: {str(e)}")
        # Optionally log traceback here
        raise HTTPException(status_code=500, detail="An internal server error occurred while deleting all chat history.")

# Endpoint to delete an entire session
@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    if not database.is_db_available():
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        chat_collection = database.get_chat_collection()
        # Check if the session exists
        count = chat_collection.count_documents({"session_id": session_id})
        
        if count == 0:
            return {"success": False, "message": "Session not found"}
        
        # Delete all messages in the session
        result = chat_collection.delete_many({"session_id": session_id})
        deleted_count = result.deleted_count
        
        # Also delete learned patterns for this session
        learning_collection = database.get_learning_collection()
        if learning_collection:
            learning_collection.delete_one({"session_id": session_id})
        
        return {"success": True, "message": f"Session deleted successfully. {deleted_count} messages removed."}
    except Exception as e:
        print(f"An unexpected error occurred while deleting session: {str(e)}")
        # Optionally log traceback here
        raise HTTPException(status_code=500, detail="An internal server error occurred while deleting session.")

# User feedback system for continuous learning
@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest, http_request: Request):
    """Allow users to provide feedback on AI responses for continuous learning"""
    if not database.is_db_available():
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        # Security: Rate limiting for feedback
        await rate_limiter.check_rate_limit(http_request.client.host)
        
        chat_collection = database.get_chat_collection()
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
        print(f"An unexpected error occurred while processing feedback: {str(e)}")
        # Optionally log traceback here
        raise HTTPException(status_code=500, detail="An internal server error occurred while processing feedback.")

@app.get("/feedback-test")
def test_feedback_endpoint():
    """Test endpoint to verify feedback system is working"""
    return {"status": "Feedback endpoint is working!", "timestamp": datetime.utcnow().isoformat()}

def learn_from_feedback(interaction, feedback_data):
    """Learn from user feedback to improve future responses"""
    if not database.is_db_available():
        return
    try:
        feedback_collection = database.get_feedback_collection()
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
    if not database.is_db_available():
        return
    try:
        learning_collection = database.get_learning_collection()
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
    if not database.is_db_available():
        return {"status": "Database unavailable"}
    try:
        learning_collection = database.get_learning_collection()
        feedback_collection = database.get_feedback_collection()
        
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
    if not database.is_db_available():
        return "Database unavailable"
    try:
        feedback_collection = database.get_feedback_collection()
        
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

# Analytics endpoint for aggregated data
@app.get("/analytics")
def get_analytics():
    """Get aggregated analytics data for chat interactions"""
    if not database.is_db_available():
        return {"error": "Database unavailable"}
    try:
        chat_collection = database.get_chat_collection()
        
        # Total interactions
        total_interactions = chat_collection.count_documents({})
        
        # Unique sessions
        unique_sessions = len(chat_collection.distinct("session_id"))
        
        # Total feedback
        feedback_collection = database.get_feedback_collection()
        total_feedback = feedback_collection.count_documents({}) if feedback_collection else 0
        
        # Interactions over time (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_interactions = chat_collection.count_documents({"timestamp": {"$gte": thirty_days_ago}})
        
        # Average response length
        avg_response_length = 0
        if total_interactions > 0:
            pipeline = [
                {"$group": {"_id": None, "avg_length": {"$avg": {"$strLenCP": "$bot_response"}}}}
            ]
            result = list(chat_collection.aggregate(pipeline))
            if result:
                avg_response_length = round(result[0].get("avg_length", 0), 2)
        
        # Feedback breakdown
        feedback_breakdown = {}
        if feedback_collection:
            pipeline = [
                {"$group": {"_id": "$feedback_type", "count": {"$sum": 1}}}
            ]
            feedback_results = list(feedback_collection.aggregate(pipeline))
            feedback_breakdown = {item["_id"]: item["count"] for item in feedback_results}
        
        return {
            "total_interactions": total_interactions,
            "unique_sessions": unique_sessions,
            "total_feedback": total_feedback,
            "recent_interactions": recent_interactions,
            "avg_response_length": avg_response_length,
            "feedback_breakdown": feedback_breakdown
        }
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting AI Guru Multibot Backend...")
    print("📡 API Documentation: http://localhost:8001/docs")
    print("🔗 Chat API: http://localhost:8001/chat")
    print("🧪 Test Gemini: http://localhost:8001/test-gemini")
    uvicorn.run(app, host="0.0.0.0", port=8001)
