import pytest
from unittest.mock import patch
from .app import app, db
from .models import User, Internship, JobPost, Workshop, Connection, InternshipApplication, JobApplication, WorkshopRegistration, ProfileView, ActivityLog
from datetime import datetime, timedelta
from flask_login import login_user, current_user, logout_user

@pytest.fixture(scope='module')
def test_client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    app.config['SECRET_KEY'] = 'test-secret-key-for-sessions'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

@pytest.fixture(scope='function')
def init_database(test_client):
    # Use the app_context provided by test_client fixture
    db.session.query(User).delete()
    db.session.query(Internship).delete()
    db.session.query(JobPost).delete()
    db.session.query(Workshop).delete()
    db.session.query(Connection).delete()
    db.session.query(InternshipApplication).delete()
    db.session.query(JobApplication).delete()
    db.session.query(WorkshopRegistration).delete()
    db.session.query(ProfileView).delete()
    db.session.query(ActivityLog).delete()
    db.session.commit()

    # Create mock users
    seeker = User(username='Seeker_Sam', email='seeker@example.com', password='password', role='seeker', name='Seeker Sam')
    provider = User(username='Provider_Pat', email='provider@example.com', password='password', role='provider', name='Provider Pat')
    db.session.add_all([seeker, provider])
    db.session.commit()

    # Log initial login activity for both
    db.session.add(ActivityLog(user_id=seeker.id, activity_type='login'))
    db.session.add(ActivityLog(user_id=provider.id, activity_type='login'))
    db.session.commit()

    yield seeker, provider

@pytest.fixture(autouse=True)
def mock_external_analytics():
    with patch('asta_authentication.main_routes.fetch_astra_analytics') as mock_astra, \
         patch('asta_authentication.main_routes.fetch_ai_guru_analytics') as mock_ai_guru:
        mock_astra.return_value = {
            'total_courses': 1,
            'overall_progress': 75,
            'total_quiz_attempts': 5,
            'recent_activity': 10
        }
        mock_ai_guru.return_value = {
            'total_interactions': 100,
            'unique_sessions': 50,
            'total_feedback': 5,
            'recent_interactions': 20
        }
        yield

def login_test_user(client, user):
    """Properly log in a user for testing"""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True
    # Log the activity
    with app.app_context():
        db.session.add(ActivityLog(user_id=user.id, activity_type='login'))
        db.session.commit()

def logout_test_user(client):
    """Properly log out a user for testing"""
    with client.session_transaction() as sess:
        sess.pop('_user_id', None)
        sess.pop('_fresh', None)

def test_seeker_analytics_dashboard(test_client, init_database):
    test_client.get('/auth/logout') # Ensure clean session state
    seeker, provider = init_database

    # Simulate Provider_Pat posting an internship
    login_test_user(test_client, provider)
    internship = Internship(title='DevOps Internship', company_name='Tech Corp', description='Learn DevOps', user_id=provider.id)
    db.session.add(internship)
    db.session.commit()
    logout_test_user(test_client)

    # Simulate Seeker_Sam viewing the internship
    login_test_user(test_client, seeker)
    test_client.post(f'/api/internship/{internship.id}/view')
    # No logout here as next action is by same user

    # Simulate Seeker_Sam applying for the internship
    # Already logged in, no need to call login_test_user again
    test_client.post(f'/api/internship/{internship.id}/apply')
    # No logout here as next action is by same user

    # Simulate Seeker_Sam viewing Provider_Pat's profile
    # Already logged in, no need to call login_test_user again
    test_client.get(f'/profile/{provider.username}') # This should log a profile view
    logout_test_user(test_client)

    # Simulate Seeker_Sam logging in again to increase login frequency
    login_test_user(test_client, seeker)

    # Simulate Seeker_Sam accessing their analytics dashboard
    response_seeker = test_client.get('/analytics')
    assert response_seeker.status_code == 200
    seeker_analytics = response_seeker.json['seeker']
    common_analytics = response_seeker.json['common']

    assert common_analytics['login_frequency'] == 5 # Initial (1) + after internship post (1) + 3 more login_test_user calls for seeker
    assert ProfileView.query.filter_by(viewed_id=provider.id).count() == 1 # Assert Provider's profile was viewed once
    assert common_analytics['profile_views'] == 0 # Seeker views provider, not their own profile
    assert seeker_analytics['internships_viewed'] == 1
    assert seeker_analytics['internships_applied'] == 1
    assert seeker_analytics['courses_enrolled'] == 1

    logout_test_user(test_client)

def test_provider_analytics_dashboard(test_client, init_database):
    test_client.get('/auth/logout') # Ensure clean session state
    seeker, provider = init_database

    # Simulate Provider_Pat posting an internship
    login_test_user(test_client, provider)
    internship = Internship(title='DevOps Internship', company_name='Tech Corp', description='Learn DevOps', user_id=provider.id)
    db.session.add(internship)
    db.session.commit()
    logout_test_user(test_client)

    # Simulate Seeker_Sam applying for the internship
    login_test_user(test_client, seeker)
    response = test_client.post(f'/api/internship/{internship.id}/apply')
    print(f"Apply response: {response.status_code}, {response.data}")
    logout_test_user(test_client)

    # Simulate Seeker_Sam sending connection request to Provider_Pat
    login_test_user(test_client, seeker)
    response = test_client.post(f'/api/user/{provider.id}/connect')
    print(f"Connect response: {response.status_code}, {response.data}")
    logout_test_user(test_client)

    # Simulate Provider_Pat accepting connection request from Seeker_Sam
    login_test_user(test_client, provider)
    connection = Connection.query.filter_by(requester_id=seeker.id, receiver_id=provider.id).first()
    print(f"Connection found: {connection}")
    if connection:
        print(f"Connection ID: {connection.id}, Status: {connection.status}")
    assert connection is not None, f"Connection not found. Seeker ID: {seeker.id}, Provider ID: {provider.id}"
    test_client.post(f'/api/connection/{connection.id}/accept')

    # Simulate Provider_Pat accessing their analytics dashboard
    response_provider = test_client.get('/analytics')
    assert response_provider.status_code == 200
    provider_analytics = response_provider.json['provider']
    common_analytics = response_provider.json['common']

    assert common_analytics['login_frequency'] == 3 # Initial (1) + after internship post (1) + after connection accept (1)
    assert common_analytics['profile_views'] == 0 # Provider's profile is not viewed by provider
    assert provider_analytics['seekers_connected'] == 1
    assert provider_analytics['announcement_performance']['internships']['DevOps Internship'] == 1
    
    # Test seeker progress tracking
    assert 'seeker_progress' in provider_analytics
    assert len(provider_analytics['seeker_progress']) == 1
    seeker_progress = provider_analytics['seeker_progress'][0]
    assert seeker_progress['username'] == 'Seeker_Sam'
    assert seeker_progress['courses_enrolled'] == 1  # From mocked astra analytics
    assert seeker_progress['overall_progress'] == 75  # From mocked astra analytics
    assert seeker_progress['tests_completed'] == 5  # From mocked astra analytics

    logout_test_user(test_client)
