from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
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
    
    # Connection relationships (using back_populates to avoid naming conflicts)
    sent_connections = db.relationship('Connection',
                                     foreign_keys='Connection.requester_id',
                                     back_populates='requester',
                                     lazy='dynamic',
                                     cascade='all, delete-orphan')
    received_connections = db.relationship('Connection',
                                         foreign_keys='Connection.receiver_id',
                                         back_populates='receiver',
                                         lazy='dynamic',
                                         cascade='all, delete-orphan')
    
    def is_connected(self, user):
        """Check if this user is connected to another user"""
        return bool(Connection.query.filter(
            ((Connection.requester_id == self.id) & (Connection.receiver_id == user.id) |
             (Connection.requester_id == user.id) & (Connection.receiver_id == self.id)) &
            (Connection.status == 'accepted')
        ).first())
    
    def has_pending_request(self, user):
        """Check if there's a pending connection request between users"""
        return bool(Connection.query.filter(
            (Connection.requester_id == self.id) & 
            (Connection.receiver_id == user.id) &
            (Connection.status == 'pending')
        ).first())
        
    def get_connection_status(self, user):
        """Get the connection status between this user and another user"""
        if self.id == user.id:
            return 'self'
            
        connection = Connection.query.filter(
            ((Connection.requester_id == self.id) & (Connection.receiver_id == user.id)) |
            ((Connection.requester_id == user.id) & (Connection.receiver_id == self.id))
        ).first()
        
        if connection:
            if connection.status == 'accepted':
                return 'connected'
            elif connection.requester_id == self.id:
                return 'request_sent'
            else:
                return 'request_received'
        return 'not_connected'

class Education(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    school = db.Column(db.String(120), nullable=False)
    degree = db.Column(db.String(120))
    dates = db.Column(db.String(120))
    grade = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

class Experience(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(120))
    dates = db.Column(db.String(120))
    location = db.Column(db.String(120))
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

class Certification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    issuing_organization = db.Column(db.String(120))
    issue_date = db.Column(db.String(120))
    credential_url = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    media_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship('User', back_populates='posts')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'author_username': self.author.username if self.author else None,
            'content': self.content,
            'media_url': self.media_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

class PostLike(db.Model):
    __tablename__ = 'post_likes'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('post_id', 'user_id', name='uq_post_like'),)

class PostComment(db.Model):
    __tablename__ = 'post_comments'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User')

    def to_dict(self):
        return {
            'id': self.id,
            'post_id': self.post_id,
            'author_username': self.author.username if self.author else None,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
        }

class PostRepost(db.Model):
    __tablename__ = 'post_reposts'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('post_id', 'user_id', name='uq_post_repost'),)

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    cover_image_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship('User', back_populates='articles')

    def to_dict(self, with_body=False):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'author_username': self.author.username if self.author else None,
            'title': self.title,
            'cover_image_url': self.cover_image_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if with_body:
            data['body'] = self.body
        return data


class Internship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    company_name = db.Column(db.String(100))
    location = db.Column(db.String(100))
    description = db.Column(db.Text, nullable=False)
    apply_link = db.Column(db.String(255))
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    view_count = db.Column(db.Integer, default=0)

class JobPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    company_name = db.Column(db.String(100))
    location = db.Column(db.String(100))
    description = db.Column(db.Text, nullable=False)
    apply_link = db.Column(db.String(255))
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    host_name = db.Column(db.String(100))
    location = db.Column(db.String(100))
    description = db.Column(db.Text, nullable=False)
    register_link = db.Column(db.String(255))
    event_date = db.Column(db.DateTime)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

class ProfileView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    viewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    viewed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    viewer = db.relationship('User', foreign_keys=[viewer_id])
    viewed = db.relationship('User', foreign_keys=[viewed_id])

class Connection(db.Model):
    __tablename__ = 'connection'

    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)  # pending, accepted, rejected
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships with back_populates to match User model
    requester = db.relationship('User', 
                              foreign_keys=[requester_id],
                              back_populates='sent_connections')
    receiver = db.relationship('User', 
                             foreign_keys=[receiver_id],
                             back_populates='received_connections')

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    activity_type = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.Text)

    user = db.relationship('User', backref='activity_logs')

class JobApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_post.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='job_applications')
    job = db.relationship('JobPost', backref='applications')

class InternshipApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    internship_id = db.Column(db.Integer, db.ForeignKey('internship.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='internship_applications')
    internship = db.relationship('Internship', backref='applications')

class WorkshopRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    workshop_id = db.Column(db.Integer, db.ForeignKey('workshop.id'), nullable=False, index=True)
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)

    author = db.relationship('User', backref='news_posts', lazy=True)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
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

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship('User')

class SavedItem(db.Model):
    __tablename__ = 'saved_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    item_type = db.Column(db.String(20), nullable=False)  # 'job', 'internship', 'workshop', 'event'
    item_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'item_type', 'item_id', name='uq_saved_item'),)

class CareerGPS(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
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
