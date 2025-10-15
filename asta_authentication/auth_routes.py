from flask import Blueprint, render_template, redirect, url_for, session, request, flash, g, current_app
from flask_dance.contrib.google import google
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

auth_bp = Blueprint('auth', __name__)

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
    if 'user_id' not in session:
        return redirect(url_for('auth.signin'))
    return render_template('role_selection.html')

@auth_bp.route('/signin_email', methods=['GET', 'POST'])
def signin_email():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.password and check_password_hash(user.password, password):
            session['user_id'] = user.id
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
    
    # Check if user already exists
    if User.query.filter_by(email=email).first():
        flash("An account with this email already exists.", "danger")
        return redirect(url_for('auth.join'))

    new_user = User(email=email, username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    
    session['user_id'] = new_user.id
    return redirect(url_for('auth.role_selection'))

@auth_bp.route('/save_role', methods=['POST'])
def save_role():
    if 'user_id' not in session:
        return redirect(url_for('auth.signin'))
    user_id = session['user_id']
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
    session.clear()
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
            # Check if an account with that email already exists
            user = User.query.filter_by(email=email).first()
            if user:
                # Link Google ID to existing account
                user.google_id = google_id
            else:
                # Create new user
                username = email.split('@')[0]
                user = User(email=email, google_id=google_id, username=username)
                db.session.add(user)
            db.session.commit()

        session['user_id'] = user.id
        if not user.role:
            return redirect(url_for('auth.role_selection'))
        return redirect(url_for('main.dashboard'))

    except (AssertionError, Exception) as e:
        current_app.logger.error(f"An error occurred during Google login: {e}")
        flash("An error occurred during the login process. Please try again.", "danger")
        return redirect(url_for('main.index'))