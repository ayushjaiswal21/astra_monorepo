import os
import sys
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_login import LoginManager, login_required, current_user
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from sqlalchemy import or_

from models import db, User, Post, Article, Education, Experience, Skill, Certification, Message, ProfileView, Connection, ActivityLog, JobApplication, InternshipApplication, WorkshopRegistration
from auth_routes import auth_bp
from main_routes import main_bp
from profile_routes import profile_bp
from routes import api_bp # Import the new API blueprint

import logging

# Load environment variables
load_dotenv()

# --- App Initialization ---
app = Flask(__name__)

# PROTOTYPE MODE: Enable CORS for all origins
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Configuration ---
# PROTOTYPE MODE: Relaxed security for development/testing
app.config['SECRET_KEY'] = "prototype-dev-key-not-for-production"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'asta_authentication/static/uploads'
app.config['POST_UPLOAD_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'posts')
app.config['ARTICLE_UPLOAD_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'articles')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
app.config['SESSION_COOKIE_SAMESITE'] = None  # Allow cross-origin cookies
app.config['SESSION_COOKIE_SECURE'] = False  # Allow HTTP (not just HTTPS)
app.config['SESSION_COOKIE_HTTPONLY'] = False  # Allow JavaScript access
DEBUG_MODE = os.environ.get("FLASK_DEBUG", "True").lower() in ["true", "1"]

# PROTOTYPE: Always allow insecure transport for OAuth
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# --- Database, CSRF, and Login Manager Initialization ---
db.init_app(app)
jwt = JWTManager(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.signin'

# --- SocketIO Initialization ---
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Message endpoint moved to main_routes.py for better organization

# --- Blueprints Registration ---

app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(main_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(api_bp) # Register the new API blueprint

# Import chat events after socketio is initialized
# Load chat socket handlers (this file registers the '/chat' namespace)
try:
    # relative import if project packaged; fallback to top-level
    from chat_socket import attach_chat_namespace
    attach_chat_namespace(socketio)
except Exception:
    # Try alternate import path
    try:
        from asta_authentication.chat_socket import attach_chat_namespace
        attach_chat_namespace(socketio)
    except Exception as e:
        app.logger.info("Chat socket handlers not loaded: %s", e)


# --- Database Creation ---
with app.app_context():
    # PROTOTYPE MODE: Don't drop tables automatically to preserve data
    db.create_all()
    app.logger.info("✅ Database initialized (prototype mode)")
    # Read both variants for compatibility
    client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID') or os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET') or os.environ.get('GOOGLE_CLIENT_SECRET')
    app.logger.info(f"Google OAuth configured: client_id={'set' if client_id else 'missing'}, secret={'set' if client_secret else 'missing'}")

# --- Main Execution ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, debug=DEBUG_MODE, host='127.0.0.1', port=port)