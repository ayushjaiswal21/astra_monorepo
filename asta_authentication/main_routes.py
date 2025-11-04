from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import current_user, login_required
try:
    from .models import db, User, Post, Internship, JobPost, Workshop, Event, Message, Education, Experience, Skill, Certification, ProfileView, Connection, ActivityLog, JobApplication, InternshipApplication, WorkshopRegistration, News, Notification
except ImportError:
    from models import db, User, Post, Internship, JobPost, Workshop, Event, Message, Education, Experience, Skill, Certification, ProfileView, Connection, ActivityLog, JobApplication, InternshipApplication, WorkshopRegistration, News, Notification
from werkzeug.utils import secure_filename
import os
from sqlalchemy import or_, func
from datetime import datetime, timedelta
import requests
import json

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

def fetch_news_from_api(category="general", limit=10):
    """Fetch news from GNews API based on category with focus on jobs, careers, and market news"""
    api_key = "c137fde903ff8adc20b448777fcd183d"
    base_url = "https://gnews.io/api/v4/search"  # Using search endpoint for better targeting
    
    # Define search queries for relevant job market and career news
    category_queries = {
        "general": "jobs OR careers OR employment OR hiring OR recruitment OR job market",
        "technology": "tech jobs OR software engineer hiring OR IT careers OR tech industry jobs",
        "education": "education jobs OR teaching careers OR academic positions OR student employment OR internships",
        "announcements": "job openings OR hiring announcement OR recruitment drive OR career opportunities",
        "events": "job fair OR career event OR recruitment event OR hiring event",
        "research": "research positions OR academic jobs OR scientist careers OR research opportunities"
    }
    
    # Get the search query for the category
    search_query = category_queries.get(category.lower(), category_queries["general"])
    
    # Try with search query and English language filter
    params = {
        "token": api_key,
        "q": search_query,
        "lang": "en",  # Force English language
        "country": "us",  # Focus on US/international market news
        "max": min(limit, 10),
        "sortby": "relevance"  # Sort by relevance to get most relevant results
    }
    
    try:
        # First attempt: Search with full parameters
        response = requests.get(base_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", [])
            if articles:
                print(f"Successfully fetched {len(articles)} job/market articles from GNews API")
                return articles
        
        # Second attempt: Try with simpler query if first fails
        if response.status_code == 403 or not articles:
            print("Trying simplified query...")
            params_simple = {
                "token": api_key,
                "q": "jobs careers",
                "lang": "en",
                "max": min(limit, 10)
            }
            response = requests.get(base_url, params=params_simple, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                if articles:
                    print(f"Successfully fetched {len(articles)} articles with simplified query")
                    return articles
        
        # Third attempt: Fall back to top headlines with category
        if not articles:
            print("Falling back to top headlines...")
            headline_url = "https://gnews.io/api/v4/top-headlines"
            category_mapping = {
                "general": "business",  # Business news often covers job market
                "technology": "technology",
                "education": "general",
                "announcements": "business",
                "events": "general",
                "research": "science"
            }
            
            params_headline = {
                "token": api_key,
                "category": category_mapping.get(category.lower(), "business"),
                "lang": "en",
                "country": "us",
                "max": min(limit, 10)
            }
            
            response = requests.get(headline_url, params=params_headline, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                if articles:
                    print(f"Successfully fetched {len(articles)} headline articles")
                    return articles
        
        print(f"GNews API error: {response.status_code} - {response.text if response else 'No response'}")
        return []
        
    except requests.RequestException as e:
        print(f"Error fetching news from API: {e}")
        return []

def get_source_name(article):
    """Safely get source name from article, handling both dict and string formats"""
    source = article.get('source', {})
    if isinstance(source, dict):
        return source.get('name', 'GNews')
    elif isinstance(source, str):
        return source
    else:
        return 'GNews'

def get_source_url(article):
    """Safely get source URL from article, handling both dict and string formats"""
    source = article.get('source', {})
    if isinstance(source, dict):
        return source.get('url', '')
    else:
        return ''

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

    # Get manual news from database
    manual_news = News.query.filter_by(is_published=True).order_by(News.date_posted.desc()).limit(3).all()

    # Get live news from API
    live_news = []
    try:
        api_articles = fetch_news_from_api("general", 2)  # Get 2 live news articles
        for article in api_articles:
            live_news.append({
                'id': f"api_{hash(article.get('url', ''))}",
                'title': article.get('title', ''),
                'content': article.get('description', '') or article.get('content', ''),
                'summary': article.get('description', '')[:100] if article.get('description') else '',
                'category': 'General',  # Changed from 'Live News' to 'General' for better categorization
                'tags': f"live, news, {get_source_name(article).lower()}",
                'image_url': article.get('image'),
                'link_url': article.get('url'),
                'source': 'api',
                'source_url': get_source_url(article),
                'date_posted': datetime.fromisoformat(article.get('publishedAt', '').replace('Z', '+00:00')).replace(tzinfo=None) if article.get('publishedAt') else datetime.utcnow(),
                'author': type('obj', (object,), {'name': get_source_name(article), 'username': 'gnews'})()
            })
    except Exception as e:
        print(f"Error fetching live news for dashboard: {e}")

    # If no live news, add fallback articles focused on jobs and careers
    if not live_news:
        print("No live news available, adding job-focused fallback articles for dashboard")
        fallback_articles = [
            {
                'id': 'fallback_dashboard_1',
                'title': 'Top Companies Hiring Now: 10,000+ Open Positions',
                'content': 'Leading employers across tech, finance, and healthcare sectors announce major hiring initiatives. Entry-level to senior positions available with competitive benefits and remote work options.',
                'summary': 'Major companies launch recruitment drives with thousands of job opportunities.',
                'category': 'General',
                'tags': 'jobs, hiring, careers, recruitment, opportunities',
                'image_url': 'https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=400',
                'link_url': 'https://www.linkedin.com/jobs',
                'source': 'api',
                'source_url': 'https://www.linkedin.com',
                'date_posted': datetime.utcnow(),
                'author': type('obj', (object,), {'name': 'Career News', 'username': 'careernews'})()
            },
            {
                'id': 'fallback_dashboard_2',
                'title': 'Skills in Demand: What Employers Are Looking For in 2025',
                'content': 'Latest market analysis reveals top skills employers seek: AI/ML expertise, cloud computing, data analysis, and soft skills like communication and adaptability lead the list.',
                'summary': 'Market report highlights most sought-after skills for career advancement.',
                'category': 'General',
                'tags': 'skills, careers, job market, professional development',
                'image_url': 'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=400',
                'link_url': 'https://www.indeed.com/career-advice',
                'source': 'api',
                'source_url': 'https://www.indeed.com',
                'date_posted': datetime.utcnow(),
                'author': type('obj', (object,), {'name': 'Job Market Insights', 'username': 'jobinsights'})()
            }
        ]
        live_news = fallback_articles

    # Combine manual and live news, sort by date
    all_news = manual_news + live_news
    all_news.sort(key=lambda x: x.date_posted if hasattr(x, 'date_posted') else x.get('date_posted'), reverse=True)

    # Take top 5 for dashboard
    recent_news = all_news[:5]

    return render_template('dashboard.html', user=current_user, all_users=all_users, recent_news=recent_news)

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


@main_bp.route('/api/messages/<username>', methods=['POST'])
@login_required
def post_message(username):
    """
    Send a message to 'username'. Accepts JSON or form: { 'content': '...' }.
    Persists message, emits 'new_message' and creates a Notification for recipient.
    """
    other_user = User.query.filter_by(username=username).first_or_404()
    data = request.get_json(silent=True) or request.form
    content = data.get('content')
    if not content:
        return jsonify({'error': 'content is required'}), 400

    msg = Message(sender_id=current_user.id, recipient_id=other_user.id, content=content)
    db.session.add(msg)
    db.session.commit()

    # Build payload and emit to recipient personal room
    payload = {
        'id': msg.id,
        'sender_id': current_user.id,
        'sender_username': current_user.username,
        'recipient_id': other_user.id,
        'content': content,
        'timestamp': msg.timestamp.isoformat() if hasattr(msg, 'timestamp') else None
    }

    # Emit via socketio namespace '/chat' to recipient's room
    try:
        from app import socketio
        socketio.emit('new_message', payload, room=f'user_{other_user.id}', namespace='/chat')
    except Exception as e:
        current_app.logger.debug("socketio emit failed: %s", e)

    # Persist a notification
    try:
        notif = Notification(user_id=other_user.id, payload={'type': 'message', 'from': current_user.id, 'message_id': msg.id, 'excerpt': content[:200]})
        db.session.add(notif)
        db.session.commit()
        # Emit notification
        try:
            socketio.emit('notification', {'id': notif.id, 'payload': notif.payload}, room=f'user_{other_user.id}', namespace='/chat')
        except Exception:
            pass
    except Exception as e:
        current_app.logger.debug("notification create failed: %s", e)

    return jsonify({'id': msg.id}), 201

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

# News routes
@main_bp.route('/news')
@login_required
def news():
    page = int(request.args.get('page', 1))
    per_page = 10
    category = request.args.get('category', 'all')
    source = request.args.get('source', 'all')  # 'all', 'manual', 'api'

    # Handle special "News from AstraLearn" category
    if category == 'News from AstraLearn':
        # This category shows all provider-posted news (source='manual')
        manual_news = News.query.filter_by(is_published=True, source='manual').order_by(News.date_posted.desc()).all()
        api_news = []  # No API news for this category
    else:
        # Build query with proper filters for other categories
        # Get manual news from database with proper filtering
        manual_news_query = News.query.filter_by(is_published=True, source='manual')

        if category != 'all':
            manual_news_query = manual_news_query.filter_by(category=category)

        manual_news = manual_news_query.order_by(News.date_posted.desc()).all()

    # Get API news if requested - Always fetch live news for all categories
    api_news = []
    if source in ['all', 'api']:
        # Always fetch live news from API for all categories, not just fallback
        api_categories = {
            'technology': ['technology'],
            'education': ['general'],  # GNews doesn't have education, use general
            'announcements': ['general'],
            'events': ['general'],
            'research': ['science'],
            'general': ['general', 'technology', 'science']  # Multiple categories for general
        }

        # Always fetch live news for the requested category
        if category.lower() in api_categories:
            categories_to_fetch = api_categories[category.lower()]
        else:
            categories_to_fetch = ['general']  # Default to general for unknown categories

        for cat in categories_to_fetch:
            # Always try to fetch from API first
            api_articles = fetch_news_from_api(cat, per_page // len(categories_to_fetch) if len(categories_to_fetch) > 1 else per_page)

            # If API fails or returns no articles, add diverse fallback articles
            if not api_articles:
                print(f"No live {cat} news found from API, adding diverse fallback articles")

                # Create diverse fallback articles based on category - focused on jobs and market
                fallback_data = {
                    'general': [
                        {
                            'title': 'Tech Industry Hiring Surge: 50,000+ New Positions Open',
                            'content': 'Major technology companies announce massive hiring initiatives across software engineering, data science, and AI roles. Remote and hybrid positions available globally with competitive compensation packages.',
                            'summary': 'Tech companies launch major recruitment drives with thousands of new job openings worldwide.',
                            'image_url': 'https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=400',
                            'tags': 'jobs, hiring, tech, careers, recruitment',
                            'external_url': 'https://www.linkedin.com/jobs'
                        },
                        {
                            'title': 'Job Market Shows Strong Growth in Q4 2025',
                            'content': 'Employment rates reach new highs with 250,000 jobs added last month. Healthcare, technology, and finance sectors lead hiring trends with increased demand for skilled professionals.',
                            'summary': 'Job market demonstrates robust growth with record employment gains across key sectors.',
                            'image_url': 'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=400',
                            'tags': 'employment, job market, careers, hiring trends',
                            'external_url': 'https://www.bls.gov/news.release/empsit.toc.htm'
                        },
                        {
                            'title': 'Remote Work Revolution: Companies Embrace Flexible Hiring',
                            'content': 'Organizations worldwide adopt permanent remote work policies, opening opportunities for global talent. Work-from-anywhere positions increase by 300% compared to pre-pandemic levels.',
                            'summary': 'Remote work becomes standard practice with companies hiring talent globally.',
                            'image_url': 'https://images.unsplash.com/photo-1588196749597-9ff075ee6b5b?w=400',
                            'tags': 'remote work, flexible jobs, work from home, careers',
                            'external_url': 'https://www.flexjobs.com'
                        }
                    ],
                    'technology': [
                        {
                            'title': 'AI Engineers in High Demand: Salaries Reach $200K+',
                            'content': 'Artificial intelligence and machine learning roles see unprecedented demand. Companies offer competitive packages with average salaries exceeding $200,000 for experienced AI engineers.',
                            'summary': 'AI engineering positions command premium salaries as demand outpaces supply.',
                            'image_url': 'https://images.unsplash.com/photo-1677442136019-21780ecad995?w=400',
                            'tags': 'ai jobs, tech careers, machine learning, high salary',
                            'external_url': 'https://www.indeed.com/jobs?q=ai+engineer'
                        },
                        {
                            'title': 'Software Developer Shortage Creates Opportunities',
                            'content': 'Tech industry faces talent shortage with 1.4 million unfilled developer positions. Companies invest in training programs and offer attractive relocation packages to attract talent.',
                            'summary': 'Developer shortage opens doors for career switchers and new graduates.',
                            'image_url': 'https://images.unsplash.com/photo-1571171637578-41bc2dd41cd2?w=400',
                            'tags': 'software jobs, developer careers, tech hiring, programming',
                            'external_url': 'https://stackoverflow.com/jobs'
                        },
                        {
                            'title': 'Cybersecurity Careers Boom Amid Digital Threats',
                            'content': 'Cybersecurity professionals in critical demand as organizations prioritize digital security. Entry-level positions start at $80K with rapid career advancement opportunities.',
                            'summary': 'Cybersecurity field offers lucrative careers with strong job security and growth.',
                            'image_url': 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=400',
                            'tags': 'cybersecurity jobs, infosec careers, security analyst, tech',
                            'external_url': 'https://www.cybersecurityjobs.net'
                        }
                    ],
                    'science': [
                        {
                            'title': 'Research Scientist Positions Open at Leading Labs',
                            'content': 'Top research institutions announce openings for PhD-level scientists in biotechnology, pharmaceutical research, and clinical trials. Competitive salaries and grant funding opportunities available.',
                            'summary': 'Leading research labs seek scientists for breakthrough medical and biotech projects.',
                            'image_url': 'https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=400',
                            'tags': 'research jobs, scientist careers, biotech, pharma',
                            'external_url': 'https://www.nature.com/naturecareers'
                        },
                        {
                            'title': 'Data Science Careers in Healthcare Boom',
                            'content': 'Healthcare organizations seek data scientists to analyze patient outcomes and improve treatment protocols. Positions offer $120K+ salaries with opportunities to impact millions of lives.',
                            'summary': 'Healthcare data science roles combine technology with meaningful medical impact.',
                            'image_url': 'https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=400',
                            'tags': 'data science, healthcare jobs, analytics, medical careers',
                            'external_url': 'https://www.healthcareitnews.com/jobs'
                        },
                        {
                            'title': 'Environmental Scientists Needed for Climate Projects',
                            'content': 'Growing demand for environmental scientists to lead sustainability initiatives. Government and private sector roles focus on renewable energy, conservation, and climate modeling.',
                            'summary': 'Climate change drives demand for environmental science professionals.',
                            'image_url': 'https://images.unsplash.com/photo-1569163139394-de4e4f43e4e3?w=400',
                            'tags': 'environmental jobs, climate careers, sustainability, science',
                            'external_url': 'https://www.environmentalscience.org/careers'
                        }
                    ]
                }

                # Get fallback articles for this category
                category_fallbacks = fallback_data.get(cat.lower(), fallback_data['general'])

                fallback_articles = []
                for i, article_data in enumerate(category_fallbacks):
                    fallback_articles.append({
                        'id': f"fallback_{cat}_{i+1}",
                        'title': article_data['title'],
                        'content': article_data['content'],
                        'summary': article_data['summary'],
                        'category': cat.title(),
                        'tags': article_data['tags'],
                        'image_url': article_data['image_url'],
                        'link_url': article_data.get('external_url', f'https://example.com/{cat.lower()}-news-{i+1}'),
                        'source': {'name': 'AstraLearn News'},  # Fix: Make it a dict like real API
                        'url': article_data.get('external_url', f'https://example.com/{cat.lower()}-news-{i+1}'),
                        'publishedAt': (datetime.utcnow() - timedelta(hours=i)).isoformat() + 'Z',
                        'author': type('obj', (object,), {'name': 'AstraLearn News', 'username': 'astralearn'})()
                    })

                api_articles = fallback_articles

            for article in api_articles:
                # Better category mapping for API articles
                article_category = category.title() if category != 'all' else cat.title()

                # Enhanced categorization logic for live news
                if cat == 'technology':
                    article_category = 'Technology'
                elif cat == 'science':
                    article_category = 'Research'
                elif cat == 'general':
                    # Try to infer category from title/content with expanded keywords
                    title_lower = article.get('title', '').lower()
                    content_lower = article.get('description', '').lower() if article.get('description') else ''

                    # Education keywords
                    education_keywords = ['education', 'learning', 'school', 'university', 'student', 'college', 'academic', 'teaching', 'curriculum', 'classroom']
                    if any(word in title_lower or word in content_lower for word in education_keywords):
                        article_category = 'Education'
                    # Technology keywords
                    elif any(word in title_lower for word in ['tech', 'software', 'ai', 'digital', 'internet', 'app', 'platform', 'startup']):
                        article_category = 'Technology'
                    # Research keywords
                    elif any(word in title_lower for word in ['research', 'study', 'science', 'discovery', 'study', 'analysis']):
                        article_category = 'Research'
                    else:
                        article_category = 'General'

                api_news.append({
                    'id': f"api_{hash(article.get('url', ''))}",
                    'title': article.get('title', ''),
                    'content': article.get('description', '') or article.get('content', ''),
                    'summary': article.get('description', '')[:200] if article.get('description') else '',
                    'category': article_category,
                    'tags': f"{article_category.lower()}, news, {get_source_name(article).lower()}",
                    'image_url': article.get('image'),
                    'link_url': article.get('url'),
                    'source': 'api',
                    'source_url': get_source_url(article),
                    'date_posted': datetime.fromisoformat(article.get('publishedAt', '').replace('Z', '+00:00')).replace(tzinfo=None) if article.get('publishedAt') else datetime.utcnow(),
                    'author': type('obj', (object,), {'name': get_source_name(article), 'username': 'gnews'})()
                })

    # Filter API news by category if specified
    if category != 'all':
        filtered_api_news = [item for item in api_news if item.get('category', '').lower() == category.lower()]
    else:
        filtered_api_news = api_news

    # Combine and sort all news
    all_news_items = manual_news + filtered_api_news
    all_news_items.sort(key=lambda x: x.date_posted if hasattr(x, 'date_posted') else x.get('date_posted'), reverse=True)

    # Paginate the combined results
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_items = all_news_items[start_idx:end_idx]

    # Create a mock pagination object
    class MockPagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total

        @property
        def pages(self):
            return (self.total + self.per_page - 1) // self.per_page

        @property
        def has_prev(self):
            return self.page > 1

        @property
        def has_next(self):
            return self.page < self.pages

        @property
        def prev_num(self):
            return self.page - 1

        @property
        def next_num(self):
            return self.page + 1

        def iter_pages(self):
            pages = []
            for p in range(max(1, self.page - 2), min(self.pages + 1, self.page + 3)):
                pages.append(p if p != self.page else None)
            return pages

    pagination = MockPagination(paginated_items, page, per_page, len(all_news_items))

    # Get all available categories from both manual and API news
    manual_categories = db.session.query(News.category).filter_by(is_published=True).distinct().all()
    manual_categories = [cat[0] for cat in manual_categories]

    # Add API categories and special categories
    api_categories = ['Education', 'Technology', 'Research', 'General']
    special_categories = ['News from AstraLearn']  # Special category for provider news

    # Combine and deduplicate categories
    all_categories = list(set(manual_categories + api_categories + special_categories))
    all_categories.sort()  # Sort alphabetically

    return render_template('news.html', news=pagination.items, categories=all_categories, selected_category=category, selected_source=source, pagination=pagination)

@main_bp.route('/provider/create_news', methods=['GET', 'POST'])
@login_required
def create_news():
    if current_user.role != 'provider':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        new_news = News(
            title=request.form.get('title'),
            content=request.form.get('content'),
            summary=request.form.get('summary'),
            category=request.form.get('category', 'General'),
            tags=request.form.get('tags'),
            image_url=request.form.get('image_url'),
            link_url=request.form.get('link_url'),
            user_id=current_user.id
        )
        db.session.add(new_news)
        db.session.commit()
        flash('News article posted successfully!', 'success')
        return redirect(url_for('main.news'))

    # Add some sample education news articles for testing
    sample_education_news = [
        {
            'title': 'New AI-Powered Learning Platform Revolutionizes Education',
            'content': 'AstraLearn introduces cutting-edge AI technology to personalize learning experiences for students worldwide. The platform adapts to individual learning styles and paces, providing customized educational content that enhances student engagement and learning outcomes.',
            'summary': 'AI-powered learning platform transforms education with personalized experiences.',
            'category': 'Education',
            'tags': 'education, ai, learning, technology'
        },
        {
            'title': 'Universities Adopt Virtual Reality for Medical Training',
            'content': 'Leading medical schools are implementing VR technology to provide hands-on training experiences for students. This innovative approach allows safe practice of complex medical procedures in immersive virtual environments.',
            'summary': 'VR technology enhances medical education with realistic training simulations.',
            'category': 'Education',
            'tags': 'education, medical, vr, training'
        },
        {
            'title': 'Online Learning Trends Show 300% Growth in 2025',
            'content': 'The education sector has seen unprecedented growth in online learning platforms. Students worldwide are embracing digital education tools for flexible learning opportunities and remote access to quality education.',
            'summary': 'Online education market experiences explosive growth with new learning technologies.',
            'category': 'Education',
            'tags': 'education, online, growth, technology'
        },
        {
            'title': 'STEM Education Initiative Launched in Schools',
            'content': 'A comprehensive STEM education program has been launched in schools across the country, focusing on science, technology, engineering, and mathematics. The initiative aims to prepare students for future careers in technical fields.',
            'summary': 'New STEM education program launched to prepare students for technical careers.',
            'category': 'Education',
            'tags': 'education, stem, science, technology'
        },
        {
            'title': 'Digital Literacy Becomes Core Curriculum Component',
            'content': 'Educational institutions are integrating digital literacy as a core component of their curriculum. Students are learning essential digital skills including coding, data analysis, and online safety measures.',
            'summary': 'Digital literacy integrated into core curriculum across educational institutions.',
            'category': 'Education',
            'tags': 'education, digital literacy, curriculum, technology'
        }
    ]

    return render_template('create_news.html', sample_news=sample_education_news)

@main_bp.route('/provider/edit_news/<int:news_id>', methods=['GET', 'POST'])
@login_required
def edit_news(news_id):
    news_item = News.query.get_or_404(news_id)

    if news_item.user_id != current_user.id and current_user.role != 'provider':
        flash('You do not have permission to edit this news article.', 'danger')
        return redirect(url_for('main.news'))

    if request.method == 'POST':
        news_item.title = request.form.get('title')
        news_item.content = request.form.get('content')
        news_item.summary = request.form.get('summary')
        news_item.category = request.form.get('category', 'General')
        news_item.tags = request.form.get('tags')
        news_item.image_url = request.form.get('image_url')
        news_item.link_url = request.form.get('link_url')
        news_item.is_published = 'is_published' in request.form

        db.session.commit()
        flash('News article updated successfully!', 'success')
        return redirect(url_for('main.news'))

    return render_template('edit_news.html', news=news_item)

@main_bp.route('/provider/delete_news/<int:news_id>', methods=['POST'])
@login_required
def delete_news(news_id):
    news_item = News.query.get_or_404(news_id)

    if news_item.user_id != current_user.id and current_user.role != 'provider':
        flash('You do not have permission to delete this news article.', 'danger')
        return redirect(url_for('main.news'))

    db.session.delete(news_item)
    db.session.commit()
    flash('News article deleted successfully!', 'success')
    return redirect(url_for('main.news'))
