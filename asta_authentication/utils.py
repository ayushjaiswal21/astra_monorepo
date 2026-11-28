import os
import time
from collections import defaultdict, deque
from functools import wraps
from flask import request, jsonify, current_app
from flask_login import current_user, login_required as flask_login_required


def generate_unique_username(email):
    """Derive a username from an email's local part, falling back to
    name1, name2, ... since `username` has a unique DB constraint but two
    different emails (e.g. john@gmail.com, john@yahoo.com) can share a
    local part."""
    try:
        from .models import User
    except ImportError:
        from models import User
    base_username = email.split('@')[0]
    username = base_username
    suffix = 1
    while User.query.filter_by(username=username).first():
        username = f"{base_username}{suffix}"
        suffix += 1
    return username

# shortcut: in-memory, per-process sliding-window limiter — fine for a
# single-worker prototype deployment, resets on restart, and won't share
# state across multiple processes/workers. Upgrade to Flask-Limiter + Redis
# if this app is ever run with more than one worker process.
_rate_limit_hits = defaultdict(deque)

def rate_limit(max_requests=10, window_seconds=60, methods=None):
    """Limit an endpoint to `max_requests` per `window_seconds` per client IP.
    `methods` restricts limiting to specific HTTP methods (e.g. only POST on
    a combined GET+POST view), defaulting to all methods."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if os.environ.get('TEST', 'false').lower() == 'true' or current_app.config.get('TESTING'):
                return f(*args, **kwargs)
            if methods and request.method not in methods:
                return f(*args, **kwargs)
            key = f"{f.__name__}:{request.remote_addr}"
            now = time.time()
            hits = _rate_limit_hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= max_requests:
                return jsonify({"error": "Too many requests, please try again later."}), 429
            hits.append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for test mode bypass
        if current_app.config.get('LOGIN_DISABLED') or \
           os.environ.get("TEST", "false").lower() == "true" or \
           os.environ.get("MOCK_AUTH", "false").lower() == "true":
            
            # If in test mode, and it's an API request, return 401 JSON if not authenticated
            if request.path.startswith('/api/'):
                if not current_user.is_authenticated:
                    return jsonify({"error": "unauthorized"}), 401
                return f(*args, **kwargs) # If authenticated (e.g., mock login), proceed
            else:
                # For non-API routes in test mode, just bypass login_required
                return f(*args, **kwargs)

        # If not in test mode, use the standard flask_login_required
        return flask_login_required(f)(*args, **kwargs)
    return decorated_function
