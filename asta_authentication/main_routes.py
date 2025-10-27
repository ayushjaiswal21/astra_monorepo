from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from models import db, User, Post, Internship, JobPost, Workshop, Event, Message, Education, Experience, Skill, Certification
from werkzeug.utils import secure_filename
import os
from sqlalchemy import or_, func
from datetime import datetime, timedelta
import requests

main_bp = Blueprint('main', __name__)

def fetch_ai_guru_analytics():
    """Fetch analytics data from ai-guru backend"""
    try:
        response = requests.get('http://localhost:8001/analytics', timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Failed to fetch ai-guru data"}
    except requests.RequestException:
        return {"error": "ai-guru service unavailable"}

def fetch_astra_analytics():
    """Fetch analytics data from astra Django app"""
    try:
        response = requests.get('http://localhost:8000/api/analytics/', timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Failed to fetch astra data"}
    except requests.RequestException:
        return {"error": "astra service unavailable"}

def calculate_profile_completeness(user):
    """Calculate profile completeness percentage"""
    fields = [user.name, user.headline, user.location, user.university, user.about]
    filled_fields = sum(1 for field in fields if field)
    education_count = Education.query.filter_by(user_id=user.id).count()
    experience_count = Experience.query.filter_by(user_id=user.id).count()
    skills_count = Skill.query.filter_by(user_id=user.id).count()
    certifications_count = Certification.query.filter_by(user_id=user.id).count()
    total_items = len(fields) + 4  # 4 for counts
    filled_items = filled_fields + (1 if education_count > 0 else 0) + (1 if experience_count > 0 else 0) + (1 if skills_count > 0 else 0) + (1 if certifications_count > 0 else 0)
    return round((filled_items / total_items) * 100, 1) if total_items > 0 else 0

def get_activity_trends():
    """Get activity trends like recent posts"""
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_posts = Post.query.filter(Post.timestamp >= thirty_days_ago).count()
    recent_messages = Message.query.filter(Message.timestamp >= thirty_days_ago).count()
    return {"recent_posts": recent_posts, "recent_messages": recent_messages}

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    all_users = User.query.all()
    return render_template('dashboard.html', user=current_user, all_users=all_users)

@main_bp.route('/analytics')
@login_required
def analytics():
    # Flask data
    total_users = User.query.count()
    total_posts = Post.query.count()
    total_internships = Internship.query.count()
    total_jobs = JobPost.query.count()
    total_workshops = Workshop.query.count()
    total_events = Event.query.count()
    total_messages = Message.query.count()

    # Profile completeness
    avg_profile_completeness = 0
    if total_users > 0:
        completeness_scores = [calculate_profile_completeness(user) for user in User.query.all()]
        avg_profile_completeness = round(sum(completeness_scores) / total_users, 1)

    # Activity trends
    activity_trends = get_activity_trends()

    # Fetch from ai-guru
    ai_guru_data = fetch_ai_guru_analytics()

    # Fetch from astra
    astra_data = fetch_astra_analytics()

    # Aggregate data
    analytics_data = {
        "flask": {
            "total_users": total_users,
            "total_posts": total_posts,
            "total_internships": total_internships,
            "total_jobs": total_jobs,
            "total_workshops": total_workshops,
            "total_events": total_events,
            "total_messages": total_messages,
            "avg_profile_completeness": avg_profile_completeness,
            "recent_posts": activity_trends["recent_posts"],
            "recent_messages": activity_trends["recent_messages"]
        },
        "ai_guru": ai_guru_data,
        "astra": astra_data
    }

    return render_template('analytics.html', current_user=current_user, analytics_data=analytics_data)

@main_bp.route('/api/messages/<username>')
@login_required
def get_messages(username):
    other_user = User.query.filter_by(username=username).first_or_404()
    messages = Message.query.filter(
        or_(
            (Message.sender_id == current_user.id) & (Message.recipient_id == other_user.id),
            (Message.sender_id == other_user.id) & (Message.recipient_id == current_user.id)
        )
    ).order_by(Message.timestamp.asc()).all()

    return jsonify([{
        'sender': msg.sender.username,
        'content': msg.content,
        'timestamp': msg.timestamp.isoformat()
    } for msg in messages])

@main_bp.route('/network')
@login_required
def network():
    users = User.query.all()
    return render_template('network/network_hub.html', users=users, current_user=current_user)

@main_bp.route('/create-post', methods=['POST'])
@login_required
def create_post():
    content = request.form.get('content')
    image_url = request.form.get('image_url')
    link_url = request.form.get('link_url')

    if content:
        new_post = Post(content=content, author=current_user, image_url=image_url, link_url=link_url)
        db.session.add(new_post)
        db.session.commit()
    
    return redirect(url_for('main.dashboard'))

@main_bp.route('/internships')
@login_required
def internships():
    all_internships = Internship.query.order_by(Internship.date_posted.desc()).all()
    return render_template('internships.html', internships=all_internships)

@main_bp.route('/workshops')
@login_required
def workshops():
    all_workshops = Workshop.query.order_by(Workshop.date_posted.desc()).all()
    return render_template('workshops.html', workshops=all_workshops)

@main_bp.route('/events')
@login_required
def events():
    all_events = Event.query.order_by(Event.date_posted.desc()).all()
    return render_template('events.html', events=all_events)

@main_bp.route('/jobs')
@login_required
def jobs():
    all_jobs = JobPost.query.order_by(JobPost.date_posted.desc()).all()
    return render_template('jobs.html', jobs=all_jobs)

@main_bp.route('/announcements')
@login_required
def announcements():
    internships = Internship.query.all()
    jobs = JobPost.query.all()
    workshops = Workshop.query.all()
    events = Event.query.all()

    all_announcements = []
    for item in internships: item.type = 'Internship'; all_announcements.append(item)
    for item in jobs: item.type = 'Job'; all_announcements.append(item)
    for item in workshops: item.type = 'Workshop'; all_announcements.append(item)
    for item in events: item.type = 'Event'; all_announcements.append(item)

    all_announcements.sort(key=lambda x: x.date_posted, reverse=True)

    return render_template('announcements.html', announcements=all_announcements)

@main_bp.route('/messages')
@login_required
def messages():
    return render_template('messages.html', current_user=current_user)

@main_bp.route('/enrollments')
@login_required
def enrollments():
    return render_template('enrollments.html', current_user=current_user)

@main_bp.route('/groups')
@login_required
def groups():
    return render_template('groups.html', current_user=current_user)


@main_bp.route('/provider/create_internship', methods=['GET', 'POST'])
@login_required
def create_internship():
    if current_user.role != 'provider':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        new_item = Internship(
            title=request.form.get('title'),
            company_name=request.form.get('company_name'),
            location=request.form.get('location'),
            description=request.form.get('description'),
            apply_link=request.form.get('apply_link'),
            user_id=current_user.id
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Internship posted successfully!', 'success')
        return redirect(url_for('main.internships'))

    return render_template('create_internship.html')

@main_bp.route('/provider/create_job', methods=['GET', 'POST'])
@login_required
def create_job():
    if current_user.role != 'provider':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        new_item = JobPost(
            title=request.form.get('title'),
            company_name=request.form.get('company_name'),
            location=request.form.get('location'),
            description=request.form.get('description'),
            apply_link=request.form.get('apply_link'),
            user_id=current_user.id
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Job posted successfully!', 'success')
        return redirect(url_for('main.jobs'))

    return render_template('create_job.html')

@main_bp.route('/provider/create_workshop', methods=['GET', 'POST'])
@login_required
def create_workshop():
    if current_user.role != 'provider':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        new_item = Workshop(
            title=request.form.get('title'),
            host_name=request.form.get('host_name'),
            location=request.form.get('location'),
            description=request.form.get('description'),
            register_link=request.form.get('register_link'),
            workshop_date=datetime.fromisoformat(request.form.get('workshop_date')) if request.form.get('workshop_date') else None,
            user_id=current_user.id
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Workshop posted successfully!', 'success')
        return redirect(url_for('main.workshops'))

    return render_template('create_workshop.html')

@main_bp.route('/provider/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    if current_user.role != 'provider':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        new_item = Event(
            title=request.form.get('title'),
            host_name=request.form.get('host_name'),
            location=request.form.get('location'),
            description=request.form.get('description'),
            register_link=request.form.get('register_link'),
            event_date=datetime.fromisoformat(request.form.get('event_date')) if request.form.get('event_date') else None,
            user_id=current_user.id
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Event posted successfully!', 'success')
        return redirect(url_for('main.events'))

    return render_template('create_event.html')
