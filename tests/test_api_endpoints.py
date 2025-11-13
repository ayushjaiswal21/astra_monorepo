import pytest
import requests
import json
import time

BASE_URL = "http://localhost:5000" # Assuming Flask app runs on 5000

@pytest.fixture(scope="module")
def client():
    # This fixture can be expanded to set up a test client for the Flask app
    # For now, we'll use requests directly.
    pass

def test_register_and_login():
    # Test registration
    register_data = {
        "email": f"test_user_{int(time.time()*1000)}@example.com",
        "password": "testpassword"
    }
    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    assert response.status_code == 201
    assert "message" in response.json()
    assert response.json()["message"] == "User created successfully."

    # Test login
    login_data = {
        "email": register_data["email"],
        "password": register_data["password"]
    }
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_mock_oauth_login():
    # This test assumes MOCK_OAUTH=true is set in the environment
    # and the mock-login route is active.
    mock_email = f"mock_user_{int(time.time()*1000)}@example.com"
    response = requests.get(f"{BASE_URL}/auth/mock-login/{mock_email}", allow_redirects=False)
    # Expect a redirect after successful mock login
    assert response.status_code == 302
    assert "/dashboard" in response.headers['Location']

    # Optionally, follow redirect and check content if needed
    # response_dashboard = requests.get(f"{BASE_URL}{response.headers['Location']}")
    # assert response_dashboard.status_code == 200
    # assert "Dashboard" in response_dashboard.text

def test_protected_api_unauthenticated_access():
    # Attempt to access a protected API endpoint without authentication
    # Using a non-existent user for the path, as authentication is the primary concern
    protected_url = f"{BASE_URL}/api/messages/non_existent_user"
    response = requests.get(protected_url, allow_redirects=False)

    # The expectation is a 401 JSON response, not a 302 redirect to HTML login
    if response.status_code == 302:
        redirect_location = response.headers.get('Location')
        pytest.fail(f"Protected API endpoint {protected_url} redirected (302) to {redirect_location} instead of returning 401 JSON.")
    
    assert response.status_code == 401
    assert response.headers['Content-Type'] == 'application/json'
    assert "error" in response.json()
    assert response.json()["error"] == "unauthorized"

# Add more API endpoint tests here as needed
# For example, testing profile creation, service listing, etc.