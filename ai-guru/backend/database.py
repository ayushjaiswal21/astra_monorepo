import logging
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import config

# This module prints emoji status messages (e.g. "✅ MongoDB connection
# successful"). Fixed in main.py's entry point earlier, but any OTHER
# script that imports this module directly (e.g. services/rag_service.py's
# own __main__ self-test) hits the same UnicodeEncodeError on a non-UTF-8
# console, before main.py ever runs. Fixing it here, at the actual shared
# import point, instead of in every individual entry script.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8', errors='replace')

logger = logging.getLogger(__name__)

client = None
db = None
chat_collection = None
learning_collection = None
feedback_collection = None
rag_collection = None

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
    rag_collection = db.rag_documents

    # session_id is the common filter field for chat history lookups,
    # conversation context, and session deletes; timestamp is sorted on
    # heavily (recent context, chat-history grouping). Neither had an index.
    chat_collection.create_index("session_id")
    chat_collection.create_index("timestamp")
    learning_collection.create_index("session_id")
    feedback_collection.create_index("session_id")
    # document_id is the filter field for every RAG indexing/retrieval lookup.
    rag_collection.create_index("document_id")

except ConnectionFailure as e:
    logger.error("MongoDB connection failed: %s -- running in DEGRADED mode (personalization/learning disabled, chat still works)", e)
    # In a real application, you might want to exit or have a more robust fallback.
except Exception as e:
    logger.error("An unexpected error occurred with MongoDB: %s -- running in DEGRADED mode (personalization/learning disabled)", e)

def get_chat_collection():
    return chat_collection

def get_learning_collection():
    return learning_collection

def get_feedback_collection():
    return feedback_collection

def get_rag_collection():
    return rag_collection

def is_db_available():
    return client is not None and db is not None
