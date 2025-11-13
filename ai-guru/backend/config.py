import os
from dotenv import load_dotenv

# Load environment variables from .env and .env.test (test overrides)
load_dotenv()
load_dotenv('.env.test')

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

# --- Validation / Mode Selection ---
# Prefer mock mode when a mock base URL is provided OR when no API key is set.
USE_MOCK = bool(os.getenv('GEMINI_API_BASE_URL')) or not GEMINI_API_KEY
# No hard failure when GEMINI_API_KEY is missing; the app can run in mock mode.
