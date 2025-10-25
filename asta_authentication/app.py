import os
from flask import Flask
from flask_socketio import SocketIO
from flask_login import LoginManager
from models import db, User, Post, Education, Experience, Skill, Certification
from blueprints import google_bp
from auth_routes import auth_bp
from main_routes import main_bp
from profile_routes import profile_bp
import logging

# --- App Initialization ---
app = Flask(__name__)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Configuration ---
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production-12345"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'asta_authentication/static/uploads'
DEBUG_MODE = os.environ.get("FLASK_DEBUG", "True").lower() in ["true", "1T"]

# Allow insecure transport for OAuth only in debug mode
if DEBUG_MODE:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# --- Database, CSRF, and Login Manager Initialization ---
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.signin'

# --- SocketIO Initialization ---
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Blueprints Registration ---
app.register_blueprint(google_bp, url_prefix="/login")
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(main_bp)
app.register_blueprint(profile_bp)

# Import chat events after socketio is initialized
import chat_events

# --- Database Creation ---
with app.app_context():
    db.create_all()
    app.logger.info(f"GOOGLE_CLIENT_ID: {os.environ.get('GOOGLE_CLIENT_ID')}")
    app.logger.info(f"GOOGLE_CLIENT_SECRET: {os.environ.get('GOOGLE_CLIENT_SECRET')}")

# --- Main Execution ---
if __name__ == '__main__':
    socketio.run(app, debug=DEBUG_MODE, host='127.0.0.1', port=5000)