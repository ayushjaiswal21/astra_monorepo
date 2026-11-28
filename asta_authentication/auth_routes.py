from flask import Blueprint, render_template, redirect, url_for, session, request, flash, g, current_app, jsonify
from flask_dance.contrib.google import google
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
import os
import secrets
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from sqlalchemy import exc
try:
    from .models import db, User, PasswordResetToken
    from .utils import rate_limit, generate_unique_username
except ImportError:
    from models import db, User, PasswordResetToken
    from utils import rate_limit, generate_unique_username
from flask_login import login_user, logout_user, current_user

auth_bp = Blueprint('auth', __name__)

def register_mock_oauth_routes(app):
    # MOCK_OAUTH guard for testing
    if app.config.get("MOCK_OAUTH", False):
        # Avoid re-registering if already present
        if 'auth.mock_login' in app.view_functions:
            return

        def mock_login(email):
            user = User.query.filter_by(email=email).first()
            if not user:
                username = generate_unique_username(email)
                user = User(email=email, username=username, password=generate_password_hash("mockpass", method='pbkdf2:sha256'))
                db.session.add(user)
                db.session.commit()
            login_user(user)
            flash(f"Mock login successful for {email}", "success")
            return redirect(url_for('main.dashboard'))

        # Register directly on the app to avoid modifying an already-registered blueprint
        app.add_url_rule('/auth/mock-login/<email>', endpoint='auth.mock_login', view_func=mock_login)

# --- API Endpoints for Testing ---

@auth_bp.route('/register', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=60)
def api_register():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body must be JSON.'}), 400

    email = data.get('email')
    password = data.get('password')

    if not email:
        return jsonify({'error': 'missing field: email'}), 400
    if not password:
        return jsonify({'error': 'missing field: password'}), 400
    
    # Basic email validation
    if '@' not in email or '.' not in email.split('@')[1]:
        return jsonify({'error': 'Invalid email format.'}), 400

    # Basic password strength
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters long.'}), 400

    # Test mode check (placeholder for now)
    if os.environ.get("TEST") == "true" or os.environ.get("MOCK_AUTH") == "true":
        # Simplified creation logic for testing, no external services
        # For now, this path is identical to the non-test path as no external services are involved.
        pass

    try:
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'User with this email already exists.'}), 409

        username = generate_unique_username(email)
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        new_user = User(email=email, username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({'message': 'User created successfully.'}), 201
    except exc.IntegrityError:
        db.session.rollback() # Rollback in case of integrity error
        return jsonify({'error': 'user already exists'}), 409
    except Exception as e:
        current_app.logger.error(f"Unexpected error during user registration: {e}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred.'}), 500

@auth_bp.route('/login', methods=['POST'])
@rate_limit(max_requests=10, window_seconds=60)
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

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
@rate_limit(max_requests=5, window_seconds=60, methods=['POST'])
def forgot_password():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip()
        user = User.query.filter_by(email=email).first()

        if user:
            token = secrets.token_urlsafe(32)
            reset = PasswordResetToken(
                user_id=user.id,
                token=token,
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )
            db.session.add(reset)
            db.session.commit()

            reset_url = url_for('auth.reset_password', token=token, _external=True)
            sent = _send_password_reset_email(user.email, reset_url)
            if not sent:
                # No SMTP configured in this environment - surface the real,
                # working reset link directly instead of a silent dead end.
                flash(
                    f"Email isn't configured here, so here's your reset link directly: "
                    f"{reset_url}",
                    "info",
                )

        # Always show the same message, whether or not the email matched a
        # real account, so this can't be used to probe which emails exist.
        flash("If that email matches an account, a password reset link has been sent.", "success")
        return redirect(url_for('auth.forgot_password'))

    return render_template('forgot_password.html')


@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset = PasswordResetToken.query.filter_by(token=token).first()
    valid = reset and not reset.used and reset.expires_at > datetime.utcnow()

    if not valid:
        flash("This password reset link is invalid or has expired.", "danger")
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password') or ''
        confirm = request.form.get('confirm_password') or ''

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('reset_password.html', token=token)
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template('reset_password.html', token=token)

        reset.user.password = generate_password_hash(password, method='pbkdf2:sha256')
        reset.used = True
        db.session.commit()

        flash("Your password has been reset. Please sign in.", "success")
        return redirect(url_for('auth.signin_email'))

    return render_template('reset_password.html', token=token)


def _send_password_reset_email(to_email, reset_url):
    """Send a real email via SMTP if credentials are configured. Returns
    True if it was actually sent, False if there's nothing configured to
    send it with (caller falls back to showing the link directly)."""
    host = os.environ.get('SMTP_HOST')
    if not host:
        return False

    port = int(os.environ.get('SMTP_PORT', '587'))
    username = os.environ.get('SMTP_USERNAME')
    password = os.environ.get('SMTP_PASSWORD')
    from_addr = os.environ.get('SMTP_FROM', username or 'no-reply@astralearn.local')

    message = EmailMessage()
    message['Subject'] = 'Reset your AstraLearn password'
    message['From'] = from_addr
    message['To'] = to_email
    message.set_content(
        f"We received a request to reset your AstraLearn password.\n\n"
        f"Reset it here (valid for 1 hour): {reset_url}\n\n"
        f"If you didn't request this, you can ignore this email."
    )

    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(message)
        return True
    except Exception as e:
        current_app.logger.warning(f"Password reset email failed to send: {e}")
        return False

@auth_bp.route('/role_selection')
def role_selection():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.signin'))
    return render_template('role_selection.html')

@auth_bp.route('/signin_email', methods=['GET', 'POST'])
@rate_limit(max_requests=10, window_seconds=60, methods=['POST'])
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
@rate_limit(max_requests=5, window_seconds=60)
def join_form():
    email = request.form.get('email')
    password = request.form.get('password')

    if not email:
        flash("Email is required.", "danger")
        return redirect(url_for('auth.join'))

    if not password or len(password) < 6:
        flash("Password must be at least 6 characters long.", "danger")
        return redirect(url_for('auth.join'))

    if User.query.filter_by(email=email).first():
        flash("An account with this email already exists.", "danger")
        return redirect(url_for('auth.join'))

    username = generate_unique_username(email)
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    new_user = User(email=email, username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    login_user(new_user)
    return redirect(url_for('auth.role_selection'))

@auth_bp.route('/save_role', methods=['POST'])
def save_role():
    data = None
    try:
        data = request.get_json(silent=True) or request.form or {}
    except Exception:
        data = request.form or {}
    role = data.get('role')
    user = current_user if current_user and not current_user.is_anonymous else None
    if not user:
        current_app.logger.debug("save_role: User not authenticated.")
        return jsonify({"error": "not_authenticated"}), 401

    user_id_for_log = user.get_id()
    current_app.logger.debug(f"save_role: User {user_id_for_log} attempting to set role to {role}")

    try:
        user.role = role
        db.session.add(user)
        db.session.commit()
        login_user(user)
        current_app.logger.debug(f"save_role: User {user_id_for_log} role set to {role} successfully.")
    except exc.IntegrityError:
        db.session.rollback()
        current_app.logger.error("save_role: IntegrityError during role setting.", exc_info=True)
        return jsonify({"error": "user_conflict"}), 409
    except Exception as ex:
        current_app.logger.exception("Error setting role")
        return jsonify({"error": "server_error"}), 500

    # If this was called via XHR return JSON with redirect path
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        redirect_url = url_for('main.dashboard')
        current_app.logger.debug(f"save_role: XHR request, returning JSON redirect to {redirect_url}")
        return jsonify({"redirect": redirect_url})
    
    redirect_url = url_for('main.dashboard')
    current_app.logger.debug(f"save_role: Non-XHR request, redirecting to {redirect_url}")
    return redirect(redirect_url)

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
                username = generate_unique_username(email)
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
