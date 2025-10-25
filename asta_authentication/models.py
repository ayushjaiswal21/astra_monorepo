from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()

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
    role = db.Column(db.String(20), nullable=False, default='student') # 'student' or 'provider'
    profile_pic_url = db.Column(db.String(200))
    banner_url = db.Column(db.String(200))
    
    education = db.relationship('Education', backref='user', lazy=True, cascade="all, delete-orphan")
    experience = db.relationship('Experience', backref='user', lazy=True, cascade="all, delete-orphan")
    skills = db.relationship('Skill', backref='user', lazy=True, cascade="all, delete-orphan")
    certifications = db.relationship('Certification', backref='user', lazy=True, cascade="all, delete-orphan")
    posts = db.relationship('Post', backref='author', lazy=True, cascade="all, delete-orphan")

    internships = db.relationship('Internship', backref='provider', lazy=True)
    job_posts = db.relationship('JobPost', backref='provider', lazy=True)
    workshops = db.relationship('Workshop', backref='provider', lazy=True)
    events = db.relationship('Event', backref='provider', lazy=True)

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
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_url = db.Column(db.String(200))
    link_url = db.Column(db.String(200))

class Internship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    company_name = db.Column(db.String(100))
    location = db.Column(db.String(100))
    description = db.Column(db.Text, nullable=False)
    apply_link = db.Column(db.String(255))
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class JobPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    company_name = db.Column(db.String(100))
    location = db.Column(db.String(100))
    description = db.Column(db.Text, nullable=False)
    apply_link = db.Column(db.String(255))
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

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

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')
