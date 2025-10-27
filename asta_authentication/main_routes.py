from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import current_user, login_required
try:
    from .models import db, User, Post, Internship, JobPost, Workshop, Event, Message, Education, Experience, Skill, Certification, ProfileView, Connection, ActivityLog, JobApplication, InternshipApplication, WorkshopRegistration
except ImportError:
    from models import db, User, Post, Internship, JobPost, Workshop, Event, Message, Education, Experience, Skill, Certification, ProfileView, Connection, ActivityLog, JobApplication, InternshipApplication, WorkshopRegistration
from werkzeug.utils import secure_filename
import os
from sqlalchemy import or_, func
from datetime import datetime, timedelta
import requests

main_bp = Blueprint('main', __name__)

def fetch_ai_guru_analytics(user_id):
    """Fetch analytics data from ai-guru backend"""
    try:
        response = requests.get(f'http://localhost:8001/analytics/{user_id}', timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Failed to fetch ai-guru data"}
    except requests.RequestException:
        return {"error": "ai-guru service unavailable"}

def fetch_astra_analytics(user_id):
    """Fetch analytics data from astra Django app"""
    try:
        response = requests.get(f'http://localhost:8000/api/analytics/{user_id}/', timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Failed to fetch astra data"}
    except requests.RequestException:
        return {"error": "astra service unavailable"}

def log_activity(user_id, activity_type, details=""):
    log = ActivityLog(user_id=user_id, activity_type=activity_type, details=details)
    db.session.add(log)
    db.session.commit()

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
    analytics_data = {}
    user = current_user

    # Common Core Data
    analytics_data['common'] = {
        'activity_feed': [{'activity_type': log.activity_type, 'timestamp': log.timestamp.isoformat(), 'details': log.details} for log in ActivityLog.query.filter_by(user_id=user.id).order_by(ActivityLog.timestamp.desc()).limit(10).all()],
        'login_frequency': ActivityLog.query.filter_by(user_id=user.id, activity_type='login').count(),
        'profile_views': ProfileView.query.filter_by(viewed_id=user.id).count(),
        'total_connections': Connection.query.filter(or_(Connection.requester_id == user.id, Connection.receiver_id == user.id), Connection.status == 'accepted').count(),
        'pending_connections': Connection.query.filter(Connection.receiver_id == user.id, Connection.status == 'pending').count()
    }

    current_app.logger.debug(f"Analytics - User ID: {user.id}, Role: {user.role}")
    current_app.logger.debug(f"Common analytics: {analytics_data['common']}")

    if user.role == 'seeker':
        astra_analytics_data = fetch_astra_analytics(user.id)
        current_app.logger.debug(f"Seeker - Astra analytics data: {astra_analytics_data}")
        analytics_data['seeker'] = {
            'courses_enrolled': astra_analytics_data.get('total_courses', 0),
            'overall_progress': astra_analytics_data.get('overall_progress', 0),
            'tests_completed': astra_analytics_data.get('total_quiz_attempts', 0),
            'internships_viewed': ActivityLog.query.filter_by(user_id=user.id, activity_type='viewed_internship').count(),
            'internships_applied': InternshipApplication.query.filter_by(user_id=user.id).count(),
            'jobs_viewed': ActivityLog.query.filter_by(user_id=user.id, activity_type='viewed_job').count(),
            'jobs_applied': JobApplication.query.filter_by(user_id=user.id).count(),
            'workshops_registered': WorkshopRegistration.query.filter_by(user_id=user.id).count()
        }
        current_app.logger.debug(f"Seeker - Full analytics: {analytics_data['seeker']}")

    if user.role == 'provider':
        ai_guru_data = fetch_ai_guru_analytics(user.id)
        astra_analytics_data = fetch_astra_analytics(user.id)
        current_app.logger.debug(f"Provider - AI Guru data: {ai_guru_data}")
        current_app.logger.debug(f"Provider - Astra analytics data: {astra_analytics_data}")

        # Get connected seekers
        connected_seeker_ids = set()
        # Seekers who connected to provider
        connections_as_receiver = db.session.query(Connection.requester_id).join(
            User, Connection.requester_id == User.id
        ).filter(
            Connection.receiver_id == user.id,
            Connection.status == 'accepted',
            User.role == 'seeker'
        ).all()
        connected_seeker_ids.update([c[0] for c in connections_as_receiver])
        
        # Seekers provider connected to
        connections_as_requester = db.session.query(Connection.receiver_id).join(
            User, Connection.receiver_id == User.id
        ).filter(
            Connection.requester_id == user.id,
            Connection.status == 'accepted',
            User.role == 'seeker'
        ).all()
        connected_seeker_ids.update([c[0] for c in connections_as_requester])

        # Fetch progress for each connected seeker
        seeker_progress_list = []
        for seeker_id in connected_seeker_ids:
            seeker = User.query.get(seeker_id)
            if seeker:
                seeker_astra_data = fetch_astra_analytics(seeker_id)
                seeker_progress_list.append({
                    'user_id': seeker_id,
                    'username': seeker.username,
                    'name': seeker.name or seeker.username,
                    'courses_enrolled': seeker_astra_data.get('total_courses', 0),
                    'overall_progress': seeker_astra_data.get('overall_progress', 0),
                    'tests_completed': seeker_astra_data.get('total_quiz_attempts', 0)
                })

        analytics_data['provider'] = {
            'announcement_performance': {
                'internships': {i.title: len(i.applications) for i in Internship.query.filter_by(user_id=user.id).all()},
                'jobs': {j.title: len(j.applications) for j in JobPost.query.filter_by(user_id=user.id).all()},
                'workshops': {w.title: len(w.registrations) for w in Workshop.query.filter_by(user_id=user.id).all()}
            },
            'seekers_connected': len(connected_seeker_ids),
            'seeker_progress': seeker_progress_list
        }
        current_app.logger.debug(f"Provider - Full analytics: {analytics_data['provider']}")

    if current_app.config['TESTING']:
        return jsonify(analytics_data)
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
        log_activity(current_user.id, 'created_post')
    
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
        log_activity(current_user.id, 'created_internship', f'{new_item.title}')
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
        log_activity(current_user.id, 'created_job', f'{new_item.title}')
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
        log_activity(current_user.id, 'created_workshop', f'{new_item.title}')
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
        log_activity(current_user.id, 'created_event', f'{new_item.title}')
        flash('Event posted successfully!', 'success')
        return redirect(url_for('main.events'))

    return render_template('create_event.html')

@main_bp.route('/api/internship/<int:internship_id>/view', methods=['POST'])
@login_required
def view_internship(internship_id):
    internship = Internship.query.get_or_404(internship_id)
    internship.view_count += 1
    db.session.commit()
    log_activity(current_user.id, 'viewed_internship', f'{internship.title}')
    return jsonify({'success': True})

@main_bp.route('/api/job/<int:job_id>/view', methods=['POST'])
@login_required
def view_job(job_id):
    job = JobPost.query.get_or_404(job_id)
    job.view_count += 1
    db.session.commit()
    log_activity(current_user.id, 'viewed_job', f'{job.title}')
    return jsonify({'success': True})

@main_bp.route('/api/internship/<int:internship_id>/apply', methods=['POST'])
@login_required
def apply_internship(internship_id):
    application = InternshipApplication(user_id=current_user.id, internship_id=internship_id)
    db.session.add(application)
    db.session.commit()
    log_activity(current_user.id, 'applied_internship', f'{Internship.query.get(internship_id).title}')
    return jsonify({'success': True})

@main_bp.route('/api/job/<int:job_id>/apply', methods=['POST'])
@login_required
def apply_job(job_id):
    application = JobApplication(user_id=current_user.id, job_id=job_id)
    db.session.add(application)
    db.session.commit()
    log_activity(current_user.id, 'applied_job', f'{JobPost.query.get(job_id).title}')
    return jsonify({'success': True})

@main_bp.route('/api/workshop/<int:workshop_id>/register', methods=['POST'])
@login_required
def register_workshop(workshop_id):
    registration = WorkshopRegistration(user_id=current_user.id, workshop_id=workshop_id)
    db.session.add(registration)
    db.session.commit()
    log_activity(current_user.id, 'registered_workshop', f'{Workshop.query.get(workshop_id).title}')
    return jsonify({'success': True})

@main_bp.route('/api/user/<int:user_id>/connect', methods=['POST'])
@login_required
def connect_user(user_id):
    connection = Connection(requester_id=current_user.id, receiver_id=user_id)
    db.session.add(connection)
    db.session.commit()
    log_activity(current_user.id, 'sent_connection_request', f'to {User.query.get(user_id).username}')
    return jsonify({'success': True})

@main_bp.route('/api/connection/<int:connection_id>/accept', methods=['POST'])
@login_required
def accept_connection(connection_id):
    connection = Connection.query.get_or_404(connection_id)
    if connection.receiver_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    connection.status = 'accepted'
    db.session.commit()
    log_activity(current_user.id, 'accepted_connection_request', f'from {connection.requester.username}')
    return jsonify({'success': True})

@main_bp.route('/api/connection/<int:connection_id>/reject', methods=['POST'])
@login_required
def reject_connection(connection_id):
    connection = Connection.query.get_or_404(connection_id)
    if connection.receiver_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    db.session.delete(connection)
    db.session.commit()
    log_activity(current_user.id, 'rejected_connection_request', f'from {connection.requester.username}')
    return jsonify({'success': True})
