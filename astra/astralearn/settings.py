import os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')

# SECURITY WARNING: keep the secret key used in production secret!
# The insecure default is only acceptable for local dev (DEBUG=True); a
# production run (DEBUG=False) with no real SECRET_KEY set fails loudly
# instead of silently shipping with a publicly-known key.
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-secret-key-change-in-production-12345'
    else:
        raise RuntimeError(
            "SECRET_KEY environment variable is required when DEBUG=False (production)."
        )

# ALLOWED_HOSTS: comma-separated via env for production (e.g. your domain and/or
# VM's public IP). Dev default covers localhost; production should always set
# this explicitly - Django refuses unknown Host headers either way.
_allowed_hosts_env = os.getenv('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(',') if h.strip()] or ['localhost', '127.0.0.1']
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# HTTPS/proxy hardening - all default to dev-safe (off) and are opt-in via env
# for production. SECURE_PROXY_SSL_HEADER is required when Django sits behind
# an nginx/load-balancer that terminates TLS and forwards plain HTTP: without
# it, Django thinks every request is insecure and SECURE_SSL_REDIRECT loops
# forever. Only enable USE_X_FORWARDED_PROTO if the proxy actually sets this
# header (standard nginx proxy_set_header X-Forwarded-Proto $scheme) - trusting
# it without a real proxy in front lets a client spoof "I'm HTTPS".
USE_X_FORWARDED_PROTO = os.getenv('USE_X_FORWARDED_PROTO', 'False').lower() in ('true', '1', 't')
if USE_X_FORWARDED_PROTO:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() in ('true', '1', 't')
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 't')
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False').lower() in ('true', '1', 't')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tutor',
    'django_celery_results',
    'httpx',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'astralearn.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'tutor.context_processors.astra_auth_base_url',
            ],
        },
    },
]

WSGI_APPLICATION = 'astralearn.wsgi.application'
ASGI_APPLICATION = 'astralearn.asgi.application'

# Database
DATABASES = {
    'default': dj_database_url.config(
        # In production, set the DATABASE_URL environment variable.
        # e.g., DATABASE_URL=postgres://user:password@host/dbname
        default='sqlite:///db.sqlite3',
        conn_max_age=600
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# The manifest storage requires `collectstatic` to have run first (which
# Procfile's `release:` step does in production) - using it in local dev
# breaks every {% static %} tag with "Missing staticfiles manifest entry"
# the moment you haven't run collectstatic. Only use it when DEBUG=False.
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# CDN Configuration (Optional)
CDN_URL = os.getenv('CDN_URL', '')  # e.g., 'https://cdn.yourdomain.com'
USE_CDN = os.getenv('USE_CDN', 'False').lower() in ('true', '1', 't')

if USE_CDN and CDN_URL:
    # Override static URL to use CDN in production
    STATIC_URL = f'{CDN_URL}/static/'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

if USE_CDN and CDN_URL:
    MEDIA_URL = f'{CDN_URL}/media/'



# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Channels layer (Requires Redis)
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         'CONFIG': {
#             "hosts": [('127.0.0.1', 6379)],
#         },
#     },
# }

# Gemini API Key (for production, use environment variables)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or 'your-gemini-api-key-placeholder'
JUDGE0_API_KEY = os.getenv('JUDGE0_API_KEY') or 'your-judge0-api-key-placeholder'
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434/api/generate')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'phi3:mini')

# OpenRouter (https://openrouter.ai) - a free-tier, no-credit-card LLM API
# used as a fallback when Ollama isn't reachable (e.g. no VM to run it on,
# a free-tier host) and Gemini is unavailable/quota-exceeded. Leave
# OPENROUTER_API_KEY unset to skip this provider entirely. Pick a current
# free model at https://openrouter.ai/models?max_price=0 - free model
# availability/names change over time, so this default may need updating.
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'nvidia/nemotron-3.5-lightning:free')

# AI Guru (ai-guru/backend) base URL, for the embedded-tutor RAG integration
# on a lesson page — a separate FastAPI service/process, not a shared DB.
AI_GURU_BASE_URL = os.getenv('AI_GURU_BASE_URL', 'http://localhost:8001')

# Cross-app SSO handoff from Astra Auth (Flask hub) - shared JWT secret and the
# hub's own base URL, used by the "Back to Astra Auth" sidebar link.
SSO_SHARED_SECRET = os.getenv('SSO_SHARED_SECRET', 'dev-sso-shared-secret-change-in-production')
ASTRA_AUTH_BASE_URL = os.getenv('ASTRA_AUTH_BASE_URL', 'http://localhost:5000')


# Authentication Settings
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Celery Configuration (Using Redis Broker and Django DB Results)
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Temporary logging configuration for development/debugging
if DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
                'style': '{',
            },
            'simple': {
                'format': '{levelname} {message}',
                'style': '{',
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': True,
            },
            'tutor': { # Assuming 'tutor' is the app with the /courses view
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': False,
            },
        },
        'root': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
    }
