from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], back_populates='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], back_populates='received_messages')

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200))
    google_id = db.Column(db.String(200), unique=True)
    name = db.Column(db.String(120))
    headline = db.Column(db.String(200))
    location = db.Column(db.String(120))
    university = db.Column(db.String(120))
    about = db.Column(db.Text)
    role = db.Column(db.String(20), nullable=False, default='seeker') # 'seeker' or 'provider'
    profile_pic_url = db.Column(db.String(200))
    banner_url = db.Column(db.String(200))
    
    education = db.relationship('Education', backref='user', lazy=True, cascade="all, delete-orphan")
    experience = db.relationship('Experience', backref='user', lazy=True, cascade="all, delete-orphan")
    skills = db.relationship('Skill', backref='user', lazy=True, cascade="all, delete-orphan")
    certifications = db.relationship('Certification', backref='user', lazy=True, cascade="all, delete-orphan")

    # New relationships for Posts and Articles
    posts = db.relationship('Post', back_populates='author', lazy='dynamic', cascade="all, delete-orphan")
    articles = db.relationship('Article', back_populates='author', lazy='dynamic', cascade="all, delete-orphan")

    internships = db.relationship('Internship', backref='provider', lazy=True)
    job_posts = db.relationship('JobPost', backref='provider', lazy=True)
    workshops = db.relationship('Workshop', backref='provider', lazy=True)
    events = db.relationship('Event', backref='provider', lazy=True)

    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', back_populates='sender')
    received_messages = db.relationship('Message', foreign_keys=[Message.recipient_id], back_populates='recipient')
    # Notifications relationship
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade="all, delete-orphan")

class Education(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    school = db.Column(db.String(120), nullable=False)
    degree = db.Column(db.String(120))
    dates = db.Column(db.String(120))
    grade = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Experience(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(120))
    dates = db.Column(db.String(120))
    location = db.Column(db.String(120))
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Certification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    issuing_organization = db.Column(db.String(120))
    issue_date = db.Column(db.String(120))
    credential_url = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    media_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship('User', back_populates='posts')

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    cover_image_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship('User', back_populates='articles')


class Internship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    company_name = db.Column(db.String(100))
    location = db.Column(db.String(100))
    description = db.Column(db.Text, nullable=False)
    apply_link = db.Column(db.String(255))
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    view_count = db.Column(db.Integer, default=0)

class JobPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    company_name = db.Column(db.String(100))
    location = db.Column(db.String(100))
    description = db.Column(db.Text, nullable=False)
    apply_link = db.Column(db.String(255))
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    view_count = db.Column(db.Integer, default=0)

class Workshop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    host_name = db.Column(db.String(100))
    location = db.Column(db.String(100))
    description = db.Column(db.Text, nullable=False)
    register_link = db.Column(db.String(255))
    workshop_date = db.Column(db.DateTime)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    host_name = db.Column(db.String(100))
    location = db.Column(db.String(100))
    description = db.Column(db.Text, nullable=False)
    register_link = db.Column(db.String(255))
    event_date = db.Column(db.DateTime)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class ProfileView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    viewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    viewed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    viewer = db.relationship('User', foreign_keys=[viewer_id])
    viewed = db.relationship('User', foreign_keys=[viewed_id])

class Connection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, accepted, rejected
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    requester = db.relationship('User', foreign_keys=[requester_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.Text)

    user = db.relationship('User', backref='activity_logs')

class JobApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_post.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='job_applications')
    job = db.relationship('JobPost', backref='applications')

class InternshipApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    internship_id = db.Column(db.Integer, db.ForeignKey('internship.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='internship_applications')
    internship = db.relationship('Internship', backref='applications')

class WorkshopRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    workshop_id = db.Column(db.Integer, db.ForeignKey('workshop.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='workshop_registrations')
    workshop = db.relationship('Workshop', backref='registrations')

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.String(300))  # Short summary for display
    category = db.Column(db.String(50), default='General')  # e.g., 'Education', 'Technology', 'Announcements'
    tags = db.Column(db.String(500))  # Comma-separated tags for better organization
    image_url = db.Column(db.String(200))
    link_url = db.Column(db.String(200))  # Optional external link
    source = db.Column(db.String(100), default='manual')  # 'manual' or 'api'
    source_url = db.Column(db.String(500))  # Original source URL from API
    is_published = db.Column(db.Boolean, default=True)
    date_posted = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    author = db.relationship('User', backref='news_posts', lazy=True)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'payload': self.payload,
            'created_at': self.created_at.isoformat(),
            'is_read': self.is_read
        }

class CareerGPS(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    interests = db.Column(db.Text)
    skills = db.Column(db.Text)
    goal = db.Column(db.String(100))
    motivation = db.Column(db.String(100))
    learning_style = db.Column(db.String(100))
    top_careers = db.Column(db.Text)
    selected_career = db.Column(db.String(100))
    progress = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = db.relationship('User', backref='career_gps', lazy=True)

class LearningPath(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    career_name = db.Column(db.String(150), nullable=False)
    career_summary = db.Column(db.Text)
    match_percentage = db.Column(db.Integer)
    learning_path_data = db.Column(db.Text)
    # Progress tracking
    progress = db.Column(db.Integer, default=0)  # Overall progress percentage
    completed_items = db.Column(db.Text)  # JSON array of completed item IDs
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True)  # Is this the current active path
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref='learning_paths', lazy=True)
>>>>>>> 27e5b26 (feat(learning-path): add AI-powered learning path generation, docs, templates, services (2025-11-08))
