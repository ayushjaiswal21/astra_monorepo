import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect
import sqlite3
from blueprints import init_db, google_bp
from auth_routes import auth_bp
from main_routes import main_bp

# --- App Initialization ---
app = Flask(__name__)

# --- Configuration ---
app.secret_key = os.environ.get("SECRET_KEY", "a-very-long-and-random-secret-key-for-dev")
DEBUG_MODE = os.environ.get("FLASK_DEBUG", "True").lower() in ["true", "1", "t"]

# Allow insecure transport for OAuth only in debug mode
if DEBUG_MODE:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Enable CSRF protection globally
csrf = CSRFProtect(app)

# Initialize database
init_db()

# Register blueprints
app.register_blueprint(google_bp, url_prefix="/login")
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(main_bp)

if __name__ == '__main__':
    init_db()
    app.run(debug=DEBUG_MODE, host='127.0.0.1', port=5000)
