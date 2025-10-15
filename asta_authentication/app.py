import os
from flask import Flask, session, g
from flask_wtf.csrf import CSRFProtect
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
DEBUG_MODE = os.environ.get("FLASK_DEBUG", "True").lower() in ["true", "1", "t"]

# Allow insecure transport for OAuth only in debug mode
if DEBUG_MODE:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# --- Database and CSRF Initialization ---
db.init_app(app)
csrf = CSRFProtect(app)

# --- Blueprints Registration ---
app.register_blueprint(google_bp, url_prefix="/login")
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(main_bp)
app.register_blueprint(profile_bp)

# --- Request Hooks ---
@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = User.query.get(user_id)

# --- Database Creation ---
with app.app_context():
    db.create_all()
    app.logger.info(f"GOOGLE_CLIENT_ID: {os.environ.get('GOOGLE_CLIENT_ID')}")
    app.logger.info(f"GOOGLE_CLIENT_SECRET: {os.environ.get('GOOGLE_CLIENT_SECRET')}")

# --- Main Execution ---
if __name__ == '__main__':
    app.run(debug=DEBUG_MODE, host='127.0.0.1', port=5000)
