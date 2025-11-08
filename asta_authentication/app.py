import os
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_login import LoginManager, login_required, current_user
from sqlalchemy import or_
from models import db, User, Post, Education, Experience, Skill, Certification, Message
from blueprints import google_bp
from auth_routes import auth_bp
from main_routes import main_bp
from profile_routes import profile_bp
import logging

# Load environment variables
load_dotenv()

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

@app.route('/api/messages/<username>')
@login_required
def get_messages(username):
    recipient = User.query.filter_by(username=username).first()
    if not recipient:
        return jsonify({"error": "User not found"}), 404

    messages = Message.query.filter(
        or_(
            (Message.sender_id == current_user.id) & (Message.recipient_id == recipient.id),
            (Message.sender_id == recipient.id) & (Message.recipient_id == current_user.id)
        )
    ).order_by(Message.timestamp.asc()).all()

    return jsonify([{
        'sender': msg.sender.username,
        'content': msg.content,
        'timestamp': msg.timestamp.isoformat()
    } for msg in messages])

# --- Blueprints Registration ---
app.register_blueprint(google_bp, url_prefix="/login")
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(main_bp)
app.register_blueprint(profile_bp)

# Import chat events after socketio is initialized
import chat_events

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