from flask import Blueprint, render_template, redirect, url_for, session, request, flash, g, current_app, jsonify
from flask_dance.contrib.google import google
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
try:
    from .models import db, User
except ImportError:
    from models import db, User
from flask_login import login_user, logout_user, current_user

auth_bp = Blueprint('auth', __name__)

# --- API Endpoints for Testing ---

@auth_bp.route('/register', methods=['POST'])
def api_register():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required.'}), 400

    email = data.get('email')
    password = data.get('password')
    
    # Basic email validation
    if '@' not in email or '.' not in email.split('@')[1]:
        return jsonify({'error': 'Invalid email format.'}), 400

    # Basic password strength
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters long.'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'User with this email already exists.'}), 409

    username = email.split('@')[0]
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    
    new_user = User(email=email, username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User created successfully.'}), 201

@auth_bp.route('/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required.'}), 400

    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    # Create JWT token using Flask-JWT-Extended
    access_token = create_access_token(identity=user.id)
    return jsonify(access_token=access_token), 200

# --- Original Form-Based Routes ---


@auth_bp.route('/test')
def test():
    return "Auth blueprint is working!"

@auth_bp.route('/signin')
def signin():
    return render_template('signin.html')

@auth_bp.route('/join')
def join():
    return render_template('join.html')

@auth_bp.route('/forgot_password')
def forgot_password():
    return render_template('forgot_password.html')

@auth_bp.route('/role_selection')
def role_selection():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.signin'))
    return render_template('role_selection.html')

@auth_bp.route('/signin_email', methods=['GET', 'POST'])
def signin_email():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.password and check_password_hash(user.password, password):
            login_user(user)
            if not user.role:
                return redirect(url_for('auth.role_selection'))
            return redirect(url_for('main.dashboard'))
        else:
            flash("Invalid email or password.", "danger")
            return redirect(url_for('auth.signin_email'))
    return render_template('signin_email.html')

@auth_bp.route('/join_form', methods=['POST'])
def join_form():
    email = request.form.get('email')
    password = request.form.get('password')
    username = email.split('@')[0] # Simple username generation

    if not password or len(password) < 6:
        flash("Password must be at least 6 characters long.", "danger")
        return redirect(url_for('auth.join'))

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    
    if User.query.filter_by(email=email).first():
        flash("An account with this email already exists.", "danger")
        return redirect(url_for('auth.join'))

    new_user = User(email=email, username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    
    login_user(new_user)
    return redirect(url_for('auth.role_selection'))

@auth_bp.route('/save_role', methods=['POST'])
def save_role():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.signin'))
    user_id = current_user.id
    role = request.form.get('role')
    if role in ['Seeker', 'Provider']:
        user = User.query.get(user_id)
        user.role = role.lower()
        db.session.commit()
        return redirect(url_for('main.dashboard'))
    else:
        flash("Invalid role selected.", "warning")
        return redirect(url_for('auth.role_selection'))

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash("You have been successfully logged out.", "success")
    return redirect(url_for('main.index'))

@auth_bp.route("/google-login-callback")
def google_login_callback():
    current_app.logger.info(f"Request args: {request.args}")
    code = request.args.get('code')
    current_app.logger.info(f"Code: {code}")

    if not google.authorized:
        flash("Login with Google failed.", "danger")
        return redirect(url_for("main.index"))

    try:
        resp = google.get("/oauth2/v2/userinfo")
        assert resp.ok, resp.text
        user_info = resp.json()
        google_id = user_info['id']
        email = user_info['email']

        user = User.query.filter_by(google_id=google_id).first()

        if not user:
            user = User.query.filter_by(email=email).first()
            if user:
                user.google_id = google_id
            else:
                username = email.split('@')[0]
                user = User(email=email, google_id=google_id, username=username)
                db.session.add(user)
            db.session.commit()

        login_user(user)
        if not user.role:
            return redirect(url_for('auth.role_selection'))
        return redirect(url_for('main.dashboard'))

    except (AssertionError, Exception) as e:
        current_app.logger.error(f"An error occurred during Google login: {e}")
        flash("An error occurred during the login process. Please try again.", "danger")
        return redirect(url_for('main.index'))
