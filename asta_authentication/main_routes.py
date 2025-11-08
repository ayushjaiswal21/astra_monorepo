from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from models import db, User, Post, Internship, JobPost, Workshop, Event, Message, Education, Experience, Skill, Certification, News
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
        # AI Guru currently exposes a global analytics endpoint (no user scoping)
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

def fetch_news_from_api(category="general", limit=10):
    """Fetch news from GNews API based on category"""
    api_key = "c137fde903ff8adc20b448777fcd183d"
    base_url = "https://gnews.io/api/v4/top-headlines"

    # Map our categories to GNews categories
    category_mapping = {
        "general": "general",
        "technology": "technology",
        "education": "general",  # GNews doesn't have education category, use general
        "announcements": "general",
        "events": "general",
        "research": "science"
    }

    gnews_category = category_mapping.get(category.lower(), "general")

    # Try different parameter combinations to avoid 403 errors
    # Start with minimal parameters first
    params_minimal = {
        "token": api_key,
        "max": min(limit, 5)  # Start with smaller limit
    }

    try:
        response = requests.get(base_url, params=params_minimal, timeout=10)

        # If successful with minimal params, try adding more
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", [])
            if articles:
                print(f"Successfully fetched {len(articles)} articles from GNews API with minimal params")
                return articles

            # If empty, try with language
            params_lang = {
                "token": api_key,
                "lang": "en",
                "max": min(limit, 5)
            }
            response = requests.get(base_url, params=params_lang, timeout=10)
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                if articles:
                    print(f"Successfully fetched {len(articles)} articles from GNews API with language param")
                    return articles

        # If still failing, try without any optional parameters
        if response.status_code == 403:
            print(f"GNews API 403 error, trying with just token...")
            params_token_only = {
                "token": api_key
            }
            response = requests.get(base_url, params=params_token_only, timeout=10)

        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", [])
            if articles:
                print(f"Successfully fetched {len(articles)} articles from GNews API")
                return articles
            else:
                print("GNews API returned empty articles array")
                return []
        else:
            print(f"GNews API error: {response.status_code} - {response.text}")
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

    # If no live news, add fallback articles
    if not live_news:
        print("No live news available, adding fallback articles for dashboard")
        fallback_articles = [
            {
                'id': f"fallback_dashboard_{i+1}",
                'title': f'AstraLearn Update {i+1}: Latest Platform Developments',
                'content': f'Exciting updates from AstraLearn platform covering new features, user growth, and educational innovations.',
                'summary': f'AstraLearn platform update {i+1} with new features and improvements.',
                'category': 'General',
                'tags': 'astralearn, updates, platform, features',
                'image_url': 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=400',
                'link_url': f'https://astralearn.com/update-{i+1}',
                'source': 'api',
                'source_url': 'https://astralearn.com',
                'date_posted': datetime.utcnow(),
                'author': type('obj', (object,), {'name': 'AstraLearn', 'username': 'astralearn'})()
            } for i in range(2)
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
    if current_user.role == 'seeker':
        return redirect(url_for('main.seeker_analytics'))
    elif current_user.role == 'provider':
        return redirect(url_for('main.provider_analytics'))
    else:
        flash('Invalid role for analytics.', 'danger')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/analytics/seeker')
@login_required
def seeker_analytics():
    if current_user.role != 'seeker':
        flash('Access denied. This dashboard is for seekers only.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Flask data for seeker: focus on personal and general learning metrics
    total_users = User.query.count()
    total_posts = Post.query.count()
    total_messages = Message.query.count()

    # Personal profile completeness
    personal_completeness = calculate_profile_completeness(current_user)

    # Activity trends
    activity_trends = get_activity_trends()

    # Fetch from ai-guru
    ai_guru_data = fetch_ai_guru_analytics()

    # Fetch from astra
    astra_data = fetch_astra_analytics()

    # Aggregate data for seeker
    analytics_data = {
        "flask": {
            "total_users": total_users,
            "total_posts": total_posts,
            "total_messages": total_messages,
            "personal_completeness": personal_completeness,
            "recent_posts": activity_trends["recent_posts"],
            "recent_messages": activity_trends["recent_messages"]
        },
        "ai_guru": ai_guru_data,
        "astra": astra_data
    }

    return render_template('seeker_analytics.html', current_user=current_user, analytics_data=analytics_data)

@main_bp.route('/analytics/provider')
@login_required
def provider_analytics():
    if current_user.role != 'provider':
        flash('Access denied. This dashboard is for providers only.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Flask data for provider: focus on content creation metrics
    total_users = User.query.count()
    total_posts = Post.query.count()
    total_internships = Internship.query.filter_by(user_id=current_user.id).count()
    total_jobs = JobPost.query.filter_by(user_id=current_user.id).count()
    total_workshops = Workshop.query.filter_by(user_id=current_user.id).count()
    total_events = Event.query.filter_by(user_id=current_user.id).count()
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

    # Aggregate data for provider
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

    return render_template('provider_analytics.html', current_user=current_user, analytics_data=analytics_data)

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

                # Create diverse fallback articles based on category
                fallback_data = {
                    'general': [
                        {
                            'title': 'Global Economic Recovery Shows Promising Signs',
                            'content': 'World economies are demonstrating resilience with improved growth indicators across multiple sectors. Manufacturing output has increased by 3.2% in the last quarter, while service industries show steady recovery patterns.',
                            'summary': 'Global economic indicators show positive recovery trends with manufacturing and services leading the way.',
                            'image_url': 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=400',
                            'tags': 'economy, global, recovery, growth',
                            'external_url': 'https://www.bbc.com/news/business'
                        },
                        {
                            'title': 'Healthcare Innovation Reaches New Milestones',
                            'content': 'Breakthrough developments in telemedicine and personalized medicine are transforming healthcare delivery worldwide. New AI-driven diagnostic tools have improved accuracy rates by 94%.',
                            'summary': 'Healthcare sector sees revolutionary changes with AI diagnostics and telemedicine advancements.',
                            'image_url': 'https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=400',
                            'tags': 'healthcare, innovation, ai, medicine',
                            'external_url': 'https://www.who.int/news-room/feature-stories'
                        },
                        {
                            'title': 'Climate Action Initiatives Gain Momentum',
                            'content': 'International cooperation on climate change has intensified with new agreements and technological solutions. Renewable energy adoption has reached record levels globally.',
                            'summary': 'International climate initiatives show progress with increased renewable energy adoption.',
                            'image_url': 'https://images.unsplash.com/photo-1569163139394-de4e4f43e4e3?w=400',
                            'tags': 'climate, environment, renewable, energy',
                            'external_url': 'https://unfccc.int/news'
                        }
                    ],
                    'technology': [
                        {
                            'title': 'AI Revolutionizes Software Development Process',
                            'content': 'New AI-powered development tools are reducing coding time by 60% while improving code quality. Machine learning algorithms now assist in debugging and optimization automatically.',
                            'summary': 'AI tools transform software development with automated coding assistance and quality improvements.',
                            'image_url': 'https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=400',
                            'tags': 'ai, software, development, automation',
                            'external_url': 'https://techcrunch.com/ai'
                        },
                        {
                            'title': 'Quantum Computing Breakthroughs Accelerate',
                            'content': 'Recent advances in quantum computing have achieved error correction milestones. Commercial quantum computers are now available for research and enterprise applications.',
                            'summary': 'Quantum computing reaches new milestones with error correction and commercial availability.',
                            'image_url': 'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=400',
                            'tags': 'quantum, computing, breakthrough, research',
                            'external_url': 'https://www.ibm.com/quantum'
                        },
                        {
                            'title': '5G Networks Enable Smart City Innovations',
                            'content': 'Fifth-generation networks are powering smart city initiatives worldwide. IoT devices, autonomous vehicles, and real-time monitoring systems are becoming mainstream.',
                            'summary': '5G technology enables smart city innovations with IoT and autonomous systems integration.',
                            'image_url': 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=400',
                            'tags': '5g, iot, smart cities, connectivity',
                            'external_url': 'https://www.qualcomm.com/5g'
                        }
                    ],
                    'science': [
                        {
                            'title': 'CRISPR Technology Opens New Medical Frontiers',
                            'content': 'Gene-editing technology continues to advance with successful treatments for genetic disorders. Clinical trials show promising results for previously incurable conditions.',
                            'summary': 'CRISPR gene-editing technology shows success in treating genetic disorders.',
                            'image_url': 'https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=400',
                            'tags': 'crispr, genetics, medicine, research',
                            'external_url': 'https://www.nature.com/articles/d41586-023-00001-0'
                        },
                        {
                            'title': 'Space Exploration Missions Yield Rich Data',
                            'content': 'Recent space missions have returned unprecedented data about our solar system. Mars rovers and lunar missions provide insights into planetary science and potential colonization.',
                            'summary': 'Space missions deliver valuable data about Mars, Moon, and solar system exploration.',
                            'image_url': 'https://images.unsplash.com/photo-1446776653964-20c1d3a81b06?w=400',
                            'tags': 'space, mars, exploration, research',
                            'external_url': 'https://science.nasa.gov/missions'
                        },
                        {
                            'title': 'Climate Science Models Improve Accuracy',
                            'content': 'Advanced climate models now predict weather patterns with 85% accuracy up to 10 days in advance. This improvement aids disaster preparedness and resource management.',
                            'summary': 'Climate models achieve higher accuracy for weather prediction and disaster planning.',
                            'image_url': 'https://images.unsplash.com/photo-1569163139394-de4e4f43e4e3?w=400',
                            'tags': 'climate, weather, prediction, science',
                            'external_url': 'https://www.ipcc.ch/'
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
