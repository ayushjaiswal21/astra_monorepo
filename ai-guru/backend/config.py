import os
from dotenv import load_dotenv

# Load environment variables from .env and .env.test (test overrides)
load_dotenv()
load_dotenv('.env.test')

# --- Security & Rate Limiting ---
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 10485760))  # 10MB default
RATE_LIMIT_MAX_REQUESTS = int(os.getenv('RATE_LIMIT_MAX_REQUESTS', 30))
RATE_LIMIT_TIME_WINDOW = int(os.getenv('RATE_LIMIT_TIME_WINDOW', 60))

# --- API Keys & URIs ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
# Free, no-card fallback when Gemini's key/billing isn't usable (same provider
# astra's course generator falls back to) - see services/gemini_service.py.
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'nvidia/nemotron-3.5-lightning:free')
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')  # Default MongoDB URI

# --- SSO (cross-app handoff from Astra Auth) ---
# Must match the Flask Astra Auth app's SSO_SHARED_SECRET exactly (same dev default).
SSO_SHARED_SECRET = os.getenv('SSO_SHARED_SECRET', 'dev-sso-shared-secret-change-in-production')

# --- Validation / Mode Selection ---
# True only when there's no real provider at all (neither Gemini nor
# OpenRouter) to answer with, or a test mock server URL was explicitly
# given. Used for reporting ("mock_mode" in chat responses) - the actual
# Gemini -> OpenRouter -> mock fallback chain lives in gemini_service.py.
USE_MOCK = bool(os.getenv('GEMINI_API_BASE_URL')) or not (GEMINI_API_KEY or OPENROUTER_API_KEY)
# No hard failure when GEMINI_API_KEY is missing; the app can run in mock mode.
