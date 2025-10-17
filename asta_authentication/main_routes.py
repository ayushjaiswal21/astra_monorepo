from flask import Blueprint, render_template, redirect, url_for, g, request
from models import db, User, Post

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Renders the public home page."""
    if g.user:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
def dashboard():
    """Renders the user's main dashboard after login."""
    if not g.user:
        return redirect(url_for('auth.signin'))

    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template('dashboard_unified.html', current_user=g.user, posts=posts)

@main_bp.route('/network')
def network():
    """Renders the networking page which displays all users."""
    if not g.user:
        return redirect(url_for('auth.signin'))

    users = User.query.all()
    return render_template('network/network_hub.html', users=users, current_user=g.user)

@main_bp.route('/create-post', methods=['POST'])
def create_post():
    if not g.user:
        return redirect(url_for('auth.signin'))

    content = request.form.get('content')
    image_url = request.form.get('image_url')
    link_url = request.form.get('link_url')

    if content:
        new_post = Post(content=content, author=g.user, image_url=image_url, link_url=link_url)
        db.session.add(new_post)
        db.session.commit()
    
    return redirect(url_for('main.dashboard'))

@main_bp.route('/internships')
def internships():
    """Renders the internships page."""
    if not g.user:
        return redirect(url_for('auth.signin'))
    return render_template('internships.html', current_user=g.user)

@main_bp.route('/events')
def events():
    """Renders the events page."""
    if not g.user:
        return redirect(url_for('auth.signin'))
    return render_template('events.html', current_user=g.user)

@main_bp.route('/messages')
def messages():
    """Renders the messages page."""
    if not g.user:
        return redirect(url_for('auth.signin'))
    return render_template('messages.html', current_user=g.user)

@main_bp.route('/enrollments')
def enrollments():
    """Renders the enrollments page."""
    if not g.user:
        return redirect(url_for('auth.signin'))
    return render_template('enrollments.html', current_user=g.user)

@main_bp.route('/groups')
def groups():
    """Renders the groups page."""
    if not g.user:
        return redirect(url_for('auth.signin'))
    return render_template('groups.html', current_user=g.user)

@main_bp.route('/workshops')
def workshops():
    """Renders the workshops page."""
    if not g.user:
        return redirect(url_for('auth.signin'))
    return render_template('workshops.html', current_user=g.user)
