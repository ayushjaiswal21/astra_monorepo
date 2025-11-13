import os
from functools import wraps
from flask import request, jsonify, current_app
from flask_login import current_user, login_required as flask_login_required

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
