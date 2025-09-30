from flask import Blueprint, render_template, redirect, url_for, session, request, flash, g, current_app
from flask_dance.contrib.google import google
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

auth_bp = Blueprint('auth', __name__)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('users.db')
        g.db.row_factory = sqlite3.Row
    return g.db

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
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        if user and user['password'] and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            if not user['role']:
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

    if not password or len(password) < 6:
        flash("Password must be at least 6 characters long.", "danger")
        return redirect(url_for('auth.join'))

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed_password))
        db.commit()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user_id = cursor.fetchone()['id']
        session['user_id'] = user_id
        return redirect(url_for('auth.role_selection'))
    except sqlite3.IntegrityError:
        flash("An account with this email already exists.", "danger")
        return redirect(url_for('auth.join'))
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred during registration: {e}")
        flash("An unexpected error occurred. Please try again.", "danger")
        return redirect(url_for('auth.join'))

@auth_bp.route('/save_role', methods=['POST'])
def save_role():
    if 'user_id' not in session:
        return redirect(url_for('auth.signin'))
    user_id = session['user_id']
    role = request.form.get('role')
    if role in ['Seeker', 'Provider']:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        db.commit()
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
    if not google.authorized:
        flash("Login with Google failed.", "danger")
        return redirect(url_for("main.index"))

    try:
        resp = google.get("/oauth2/v2/userinfo")
        assert resp.ok, resp.text
        user_info = resp.json()
        google_id = user_info['id']
        email = user_info['email']

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE google_id = ?", (google_id,))
        user = cursor.fetchone()

        if not user:
            cursor.execute("INSERT INTO users (email, google_id) VALUES (?, ?)", (email, google_id))
            db.commit()
            cursor.execute("SELECT id FROM users WHERE google_id = ?", (google_id,))
            user_id = cursor.fetchone()['id']
            session['user_id'] = user_id
            return redirect(url_for('auth.role_selection'))
        else:
            session['user_id'] = user['id']
            if not user['role']:
                return redirect(url_for('auth.role_selection'))
            return redirect(url_for('main.dashboard'))

    except (AssertionError, Exception) as e:
        current_app.logger.error(f"An error occurred during Google login: {e}")
        flash("An error occurred during the login process. Please try again.", "danger")
        return redirect(url_for('main.index'))
