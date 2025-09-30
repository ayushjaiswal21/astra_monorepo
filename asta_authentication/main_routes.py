from flask import Blueprint, render_template, redirect, url_for, session, request, g
import sqlite3

main_bp = Blueprint('main', __name__)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('users.db')
        g.db.row_factory = sqlite3.Row
    return g.db

@main_bp.route('/')
def index():
    """Renders the public home page."""
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
def dashboard():
    """Renders the user's main dashboard after login."""
    if 'user_id' not in session:
        return redirect(url_for('auth.signin'))

    # Fetch user data for dashboard
    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT email, role FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        return redirect(url_for('auth.logout'))

    user = {
        'name': user_data['email'].split('@')[0].capitalize(),
        'email': user_data['email'],
        'role': user_data['role']
    }

    # Check if we should show AI Guru section
    show_ai_guru = request.args.get('show_ai_guru') == 'true'

    return render_template('dashboard.html', user=user, show_ai_guru=show_ai_guru)

@main_bp.route('/ai-guru')
def ai_guru():
    # This will redirect the user to the AI Guru frontend
    return redirect('http://127.0.0.1:3000/')
