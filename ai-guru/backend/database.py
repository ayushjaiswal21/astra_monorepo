from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import config

client = None
db = None
chat_collection = None
learning_collection = None
feedback_collection = None

try:
    # Configure MongoDB client with proper settings
    client = MongoClient(
        config.MONGODB_URI,
        serverSelectionTimeoutMS=5000,  # Shorter timeout
        connectTimeoutMS=5000,
        socketTimeoutMS=5000,
        maxPoolSize=50, # Allow more connections
        minPoolSize=5
    )
    # Test the connection
    client.admin.command('ping')
    print("✅ MongoDB connection successful")
    db = client.guru_multibot
    chat_collection = db.chat_history
    learning_collection = db.learned_patterns
    feedback_collection = db.user_feedback

except ConnectionFailure as e:
    print(f"[ERROR] MongoDB connection failed: {e}")
    print("[INFO] Fallback: Application will not be able to persist data.")
    # In a real application, you might want to exit or have a more robust fallback.
except Exception as e:
    print(f"[ERROR] An unexpected error occurred with MongoDB: {e}")

def get_db():
    return db

def get_chat_collection():
    return chat_collection

def get_learning_collection():
    return learning_collection

def get_feedback_collection():
    return feedback_collection

def is_db_available():
    return client is not None and db is not None
