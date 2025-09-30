import os
from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify, g
from flask_dance.contrib.google import make_google_blueprint, google
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

# --- App Initialization ---
app = Flask(__name__)

# --- Configuration ---
# Load configuration from environment variables for security and flexibility.
# In a production environment, these should be set to secure, random values.
app.secret_key = os.environ.get("SECRET_KEY", "a-very-long-and-random-secret-key-for-dev")
DEBUG_MODE = os.environ.get("FLASK_DEBUG", "True").lower() in ["true", "1", "t"]

# Allow insecure transport for OAuth only in debug mode (local development).
# In production, this MUST be False and the app MUST run over HTTPS.
if DEBUG_MODE:
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Enable CSRF protection globally
csrf = CSRFProtect(app)

# --- Database Setup ---
def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db' not in g:
        g.db = sqlite3.connect('users.db')
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    # init_db is called outside of an app context, so we can't use get_db()
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT,
            google_id TEXT UNIQUE,
            role TEXT
        )
    ''')
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'role' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT")
    conn.commit()
    conn.close()

init_db()

# --- Google OAuth Configuration ---
app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

google_bp = make_google_blueprint(
    scope=["openid", "https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email"],
    redirect_to="google_login_callback"
)
app.register_blueprint(google_bp, url_prefix="/login")

# --- Routes ---
@app.route('/')
def index():
    """Renders the public home page."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Renders the user's main dashboard after login."""
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    # Fetch user data for dashboard
    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT email, role FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        return redirect(url_for('logout'))

    user = {
        'name': user_data['email'].split('@')[0].capitalize(),
        'email': user_data['email'],
        'role': user_data['role']
    }
    
    # Check if we should show AI Guru section
    show_ai_guru = request.args.get('show_ai_guru') == 'true'
    
    return render_template('dashboard.html', user=user, show_ai_guru=show_ai_guru)

@app.route("/google-login-callback")
def google_login_callback():
    if not google.authorized:
        flash("Login with Google failed.", "danger")
        return redirect(url_for("index"))

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
            return redirect(url_for('role_selection'))
        else:
            session['user_id'] = user['id']
            if not user['role']: # Role check
                return redirect(url_for('role_selection'))
            return redirect(url_for('dashboard'))

    except (AssertionError, Exception) as e:
        app.logger.error(f"An error occurred during Google login: {e}")
        flash("An error occurred during the login process. Please try again.", "danger")
        return redirect(url_for('index'))

@app.route('/ai-guru')
def ai_guru():
    if 'user_id' not in session:
        return redirect(url_for('signin'))
    
    # Check if this is an AJAX request (e.g., for dynamic content)
    if request.headers.get('Content-Type') == 'application/json' or request.args.get('ajax') == '1':
        return jsonify({
            'message': 'Welcome to AI Guru!',
            'suggestions': [
                'Focus on Python for data science.',
                'Practice coding challenges daily.',
                'Explore machine learning basics.'
            ]
        })
    
    # For direct visits, redirect back to dashboard with a flag to show AI Guru section
    return redirect(url_for('dashboard', show_ai_guru='true'))

@app.route('/save_role', methods=['POST'])
def save_role():
    if 'user_id' not in session:
        return redirect(url_for('signin'))
    user_id = session['user_id']
    role = request.form.get('role')
    if role in ['Seeker', 'Provider']:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        db.commit()
        return redirect(url_for('dashboard'))
    else:
        flash("Invalid role selected.", "warning")
        return redirect(url_for('role_selection'))

@app.route('/signin_email', methods=['GET', 'POST'])
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
                return redirect(url_for('role_selection'))
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password.", "danger")
            return redirect(url_for('signin_email'))
    return render_template('signin_email.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been successfully logged out.", "success")
    return redirect(url_for('index'))

# --- Unchanged Routes ---
@app.route('/signin')
def signin():
    return render_template('signin.html')

@app.route('/join')
def join():
    return render_template('join.html')

@app.route('/forgot_password')
def forgot_password():
    return render_template('forgot_password.html')

@app.route('/role_selection')
def role_selection():
    if 'user_id' not in session:
        return redirect(url_for('signin'))
    return render_template('role_selection.html')

@app.route('/join_form', methods=['POST'])
def join_form():
    email = request.form.get('email')
    password = request.form.get('password')

    if not password or len(password) < 6:
        flash("Password must be at least 6 characters long.", "danger")
        return redirect(url_for('join'))

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed_password))
        db.commit()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user_id = cursor.fetchone()['id']
        session['user_id'] = user_id
        return redirect(url_for('role_selection'))
    except sqlite3.IntegrityError:
        flash("An account with this email already exists.", "danger")
        return redirect(url_for('join'))
    except Exception as e:
        app.logger.error(f"An unexpected error occurred during registration: {e}")
        flash("An unexpected error occurred. Please try again.", "danger")
        return redirect(url_for('join'))

if __name__ == '__main__':
    init_db()
    app.run(debug=DEBUG_MODE, host='127.0.0.1', port=5000)
