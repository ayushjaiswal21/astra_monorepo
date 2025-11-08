import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Application Settings ---
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
DEBUG_MODE = os.getenv('FLASK_DEBUG', 'True').lower() in ["true", "1", "t"]

# --- Security & Rate Limiting ---
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 10485760))  # 10MB default
RATE_LIMIT_MAX_REQUESTS = int(os.getenv('RATE_LIMIT_MAX_REQUESTS', 30))
RATE_LIMIT_TIME_WINDOW = int(os.getenv('RATE_LIMIT_TIME_WINDOW', 60))

# --- API Keys & URIs ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')  # Default MongoDB URI

# --- Validation ---
# Ensure critical environment variables are set
REQUIRED_ENV_VARS = ['GEMINI_API_KEY']  # Only GEMINI_API_KEY is required, MongoDB is optional
missing_vars = [var for var in REQUIRED_ENV_VARS if not globals().get(var)]
if missing_vars:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing_vars)}")
