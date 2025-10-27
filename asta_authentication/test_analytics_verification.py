"""
DELIVERABLE A: COMPREHENSIVE ANALYTICS VERIFICATION TEST SUITE
================================================================
This test suite verifies the complete Analytics Dashboard functionality
for the Astra platform, including all Seeker and Provider requirements.
"""

import pytest
from unittest.mock import patch
from .app import app, db
from .models import (User, Internship, JobPost, Workshop, Connection, 
                     InternshipApplication, JobApplication, WorkshopRegistration, 
                     ProfileView, ActivityLog)
from datetime import datetime
from flask_login import login_user, logout_user


# ============================================================================
# FIXTURES: Mock Environment Setup
# ============================================================================

@pytest.fixture(scope='module')
def test_client():
    """
    Mock the Environment: Set up a test client with in-memory database
    """
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()


@pytest.fixture(scope='function')
def init_database(test_client):
    """
    Create Mock Users: TestSeeker and TestProvider with clean database
    """
    # Clean all tables
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

    # Create mock users as specified
    test_seeker = User(
        username='TestSeeker', 
        email='testseeker@example.com', 
        password='password', 
        role='seeker', 
        name='Test Seeker'
    )
    test_provider = User(
        username='TestProvider', 
        email='testprovider@example.com', 
        password='password', 
        role='provider', 
        name='Test Provider'
    )
    db.session.add_all([test_seeker, test_provider])
    db.session.commit()

    # Log initial login activity
    db.session.add(ActivityLog(user_id=test_seeker.id, activity_type='login'))
    db.session.add(ActivityLog(user_id=test_provider.id, activity_type='login'))
    db.session.commit()

    yield test_seeker, test_provider


@pytest.fixture(autouse=True)
def mock_external_analytics():
    """
    Mock external service calls (astra Django app and ai-guru FastAPI)
    """
    with patch('asta_authentication.main_routes.fetch_astra_analytics') as mock_astra, \
         patch('asta_authentication.main_routes.fetch_ai_guru_analytics') as mock_ai_guru:
        
        # Mock astra Django response (course data)
        mock_astra.return_value = {
            'total_courses': 1,
            'overall_progress': 75,
            'total_quiz_attempts': 5,
            'recent_activity': 10
        }
        
        # Mock ai-guru FastAPI response (chat data)
        mock_ai_guru.return_value = {
            'total_interactions': 100,
            'unique_sessions': 50,
            'total_feedback': 5,
            'recent_interactions': 20
        }
        yield


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def login_test_user(client, user):
    """Helper to simulate user login"""
    with client.session_transaction() as sess:
        with app.app_context():
            login_user(user)
            sess['_user_id'] = str(user.id)
    with app.app_context():
        db.session.add(ActivityLog(user_id=user.id, activity_type='login'))
        db.session.commit()


def logout_test_user(client):
    """Helper to simulate user logout"""
    with client.session_transaction() as sess:
        with app.app_context():
            logout_user()
            sess.pop('_user_id', None)


# ============================================================================
# TEST 1: SEEKER ANALYTICS - Complete User Journey
# ============================================================================

def test_seeker_complete_journey(test_client, init_database):
    """
    Simulate Actions: Complete seeker journey including:
    - Provider posts internship
    - Seeker views internship
    - Seeker applies for internship
    - Seeker enrolls in course (mocked via external API)
    
    Assert All Requirements: Verify all seeker metrics
    """
    test_client.get('/auth/logout')  # Clean session
    test_seeker, test_provider = init_database

    # ========================================================================
    # ACTION 1: TestProvider posts a new internship
    # ========================================================================
    login_test_user(test_client, test_provider)
    internship = Internship(
        title='DevOps Internship',
        company_name='Tech Corp',
        description='Learn DevOps and Cloud Technologies',
        user_id=test_provider.id
    )
    db.session.add(internship)
    db.session.commit()
    internship_id = internship.id
    logout_test_user(test_client)

    # ========================================================================
    # ACTION 2: TestSeeker views the internship
    # ========================================================================
    login_test_user(test_client, test_seeker)
    response = test_client.post(f'/api/internship/{internship_id}/view')
    assert response.status_code == 200

    # ========================================================================
    # ACTION 3: TestSeeker applies for the internship
    # ========================================================================
    response = test_client.post(f'/api/internship/{internship_id}/apply')
    assert response.status_code == 200

    # ========================================================================
    # ACTION 4: TestSeeker views TestProvider's profile
    # ========================================================================
    test_client.get(f'/profile/{test_provider.username}')

    # ========================================================================
    # TEST ENDPOINTS & ASSERT: Call analytics endpoint and verify data
    # ========================================================================
    response_seeker = test_client.get('/analytics')
    assert response_seeker.status_code == 200
    
    data = response_seeker.json
    assert 'seeker' in data
    assert 'common' in data
    
    seeker_analytics = data['seeker']
    common_analytics = data['common']

    # ========================================================================
    # ASSERT ALL REQUIREMENTS: Verify each metric
    # ========================================================================
    
    # Common Core Metrics
    assert common_analytics['login_frequency'] >= 1, "Login frequency should be tracked"
    assert common_analytics['total_connections'] >= 0, "Connections should be counted"
    assert common_analytics['profile_views'] == 0, "Seeker hasn't been viewed"
    
    # Seeker-Specific Metrics
    assert seeker_analytics['internships_viewed'] == 1, \
        "TestSeeker viewed 1 internship"
    
    assert seeker_analytics['internships_applied'] == 1, \
        "TestSeeker applied to 1 internship"
    
    assert seeker_analytics['courses_enrolled'] == 1, \
        "TestSeeker enrolled in 1 course (from mocked astra)"
    
    assert seeker_analytics['overall_progress'] == 75, \
        "TestSeeker has 75% overall progress (from mocked astra)"
    
    assert seeker_analytics['tests_completed'] == 5, \
        "TestSeeker completed 5 tests (from mocked astra)"
    
    assert seeker_analytics['workshops_registered'] == 0, \
        "TestSeeker hasn't registered for workshops yet"
    
    assert seeker_analytics['jobs_applied'] == 0, \
        "TestSeeker hasn't applied for jobs yet"

    # Verify database state
    assert InternshipApplication.query.filter_by(
        user_id=test_seeker.id, 
        internship_id=internship_id
    ).count() == 1, "Application should be in database"
    
    assert ActivityLog.query.filter_by(
        user_id=test_seeker.id, 
        activity_type='viewed_internship'
    ).count() == 1, "View should be logged"

    logout_test_user(test_client)
    print("✅ SEEKER TEST PASSED: All requirements verified")


# ============================================================================
# TEST 2: PROVIDER ANALYTICS - Impact Dashboard
# ============================================================================

def test_provider_impact_dashboard(test_client, init_database):
    """
    Simulate Actions: Complete provider journey including:
    - Provider posts internship
    - Seeker applies for internship
    - Seeker connects with provider
    - Provider accepts connection
    
    Assert All Requirements: Verify provider sees applicants and seeker progress
    """
    test_client.get('/auth/logout')  # Clean session
    test_seeker, test_provider = init_database

    # ========================================================================
    # ACTION 1: TestProvider posts an internship
    # ========================================================================
    login_test_user(test_client, test_provider)
    internship = Internship(
        title='DevOps Internship',
        company_name='Tech Corp',
        description='Learn DevOps',
        user_id=test_provider.id
    )
    db.session.add(internship)
    db.session.commit()
    internship_id = internship.id
    logout_test_user(test_client)

    # ========================================================================
    # ACTION 2: TestSeeker applies for the internship
    # ========================================================================
    login_test_user(test_client, test_seeker)
    test_client.post(f'/api/internship/{internship_id}/apply')
    logout_test_user(test_client)

    # ========================================================================
    # ACTION 3: TestSeeker sends connection request to TestProvider
    # ========================================================================
    login_test_user(test_client, test_seeker)
    test_client.post(f'/api/user/{test_provider.id}/connect')
    logout_test_user(test_client)

    # ========================================================================
    # ACTION 4: TestProvider accepts connection request
    # ========================================================================
    login_test_user(test_client, test_provider)
    connection = Connection.query.filter_by(
        requester_id=test_seeker.id, 
        receiver_id=test_provider.id
    ).first()
    assert connection is not None, "Connection request should exist"
    test_client.post(f'/api/connection/{connection.id}/accept')

    # ========================================================================
    # TEST ENDPOINTS & ASSERT: Call provider analytics endpoint
    # ========================================================================
    response_provider = test_client.get('/analytics')
    assert response_provider.status_code == 200
    
    data = response_provider.json
    assert 'provider' in data
    assert 'common' in data
    
    provider_analytics = data['provider']
    common_analytics = data['common']

    # ========================================================================
    # ASSERT ALL REQUIREMENTS: Verify provider metrics
    # ========================================================================
    
    # Common Core Metrics
    assert common_analytics['login_frequency'] >= 1, "Login frequency tracked"
    assert common_analytics['total_connections'] == 1, "Provider has 1 connection"
    
    # Provider-Specific Metrics
    assert provider_analytics['seekers_connected'] == 1, \
        "TestProvider connected with 1 seeker"
    
    # Announcement Performance
    assert 'announcement_performance' in provider_analytics
    assert 'internships' in provider_analytics['announcement_performance']
    assert provider_analytics['announcement_performance']['internships']['DevOps Internship'] == 1, \
        "DevOps Internship has 1 applicant"
    
    # ========================================================================
    # CRITICAL: Test Seeker Progress Tracking (NEW FEATURE)
    # ========================================================================
    assert 'seeker_progress' in provider_analytics, \
        "Provider should see seeker progress"
    
    assert len(provider_analytics['seeker_progress']) == 1, \
        "Provider should see 1 connected seeker's progress"
    
    seeker_progress = provider_analytics['seeker_progress'][0]
    
    assert seeker_progress['username'] == 'TestSeeker', \
        "Seeker username should match"
    
    assert seeker_progress['name'] == 'Test Seeker', \
        "Seeker name should match"
    
    assert seeker_progress['courses_enrolled'] == 1, \
        "Provider sees seeker enrolled in 1 course"
    
    assert seeker_progress['overall_progress'] == 75, \
        "Provider sees seeker at 75% progress"
    
    assert seeker_progress['tests_completed'] == 5, \
        "Provider sees seeker completed 5 tests"

    # Verify database state
    assert Connection.query.filter_by(
        requester_id=test_seeker.id,
        receiver_id=test_provider.id,
        status='accepted'
    ).count() == 1, "Connection should be accepted in database"

    logout_test_user(test_client)
    print("✅ PROVIDER TEST PASSED: All requirements verified including seeker progress")


# ============================================================================
# TEST 3: COMPREHENSIVE INTEGRATION TEST
# ============================================================================

def test_complete_platform_integration(test_client, init_database):
    """
    Full integration test covering multiple announcements and interactions
    """
    test_client.get('/auth/logout')
    test_seeker, test_provider = init_database

    # Provider posts multiple announcements
    login_test_user(test_client, test_provider)
    
    internship = Internship(
        title='Python Developer Internship',
        company_name='StartupCo',
        description='Build web apps',
        user_id=test_provider.id
    )
    job = JobPost(
        title='Senior Developer',
        company_name='BigTech',
        description='Lead projects',
        user_id=test_provider.id
    )
    workshop = Workshop(
        title='AI Workshop',
        host_name='Tech Academy',
        description='Learn AI',
        user_id=test_provider.id
    )
    
    db.session.add_all([internship, job, workshop])
    db.session.commit()
    logout_test_user(test_client)

    # Seeker interacts with all announcements
    login_test_user(test_client, test_seeker)
    test_client.post(f'/api/internship/{internship.id}/view')
    test_client.post(f'/api/internship/{internship.id}/apply')
    test_client.post(f'/api/job/{job.id}/view')
    test_client.post(f'/api/job/{job.id}/apply')
    test_client.post(f'/api/workshop/{workshop.id}/register')

    # Verify seeker analytics
    response = test_client.get('/analytics')
    seeker_data = response.json['seeker']
    
    assert seeker_data['internships_viewed'] == 1
    assert seeker_data['internships_applied'] == 1
    assert seeker_data['jobs_viewed'] == 1
    assert seeker_data['jobs_applied'] == 1
    assert seeker_data['workshops_registered'] == 1
    
    logout_test_user(test_client)

    # Verify provider sees all applications
    login_test_user(test_client, test_provider)
    response = test_client.get('/analytics')
    provider_data = response.json['provider']
    
    assert provider_data['announcement_performance']['internships']['Python Developer Internship'] == 1
    assert provider_data['announcement_performance']['jobs']['Senior Developer'] == 1
    assert provider_data['announcement_performance']['workshops']['AI Workshop'] == 1
    
    logout_test_user(test_client)
    print("✅ INTEGRATION TEST PASSED: Multi-announcement scenario verified")


# ============================================================================
# RUN INSTRUCTIONS
# ============================================================================
"""
To run this test suite:

1. Navigate to the asta_authentication directory:
   cd asta_authentication

2. Run all tests with verbose output:
   pytest test_analytics_verification.py -v

3. Run specific test:
   pytest test_analytics_verification.py::test_seeker_complete_journey -v

4. Run with coverage:
   pytest test_analytics_verification.py --cov=. --cov-report=html

Expected Output:
✅ test_seeker_complete_journey PASSED
✅ test_provider_impact_dashboard PASSED
✅ test_complete_platform_integration PASSED
"""
