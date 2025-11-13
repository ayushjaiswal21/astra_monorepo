import pytest
import requests

# Assuming Django app runs on port 8000
DJANGO_BASE_URL = "http://localhost:8000"

@pytest.fixture(scope="module")
def django_client():
    # In a real scenario, you might use Django's test client
    # For E2E-like testing, direct requests are fine.
    try:
        requests.get(f"{DJANGO_BASE_URL}/admin/", timeout=3)
    except requests.exceptions.RequestException:
        pytest.skip(f"Django server not reachable at {DJANGO_BASE_URL}; skipping Django tests")
    return None

def test_django_admin_access(django_client):
    # This is a very basic test to check if Django is running
    # and if the admin page is accessible (even if login is required)
    try:
        response = requests.get(f"{DJANGO_BASE_URL}/admin/", timeout=5)
        assert response.status_code in [200, 302] # 200 for admin login page, 302 for redirect
    except requests.exceptions.ConnectionError:
        pytest.skip(f"Django application not reachable at {DJANGO_BASE_URL}")

def test_django_course_listing(django_client):
    # Assuming there's a public course listing page
    # This test will need to be adapted based on actual Django routes
    try:
        response = requests.get(f"{DJANGO_BASE_URL}/courses/", timeout=5) # Placeholder route
        assert response.status_code == 200
        assert "Courses" in response.text # Placeholder content check
    except requests.exceptions.ConnectionError:
        pytest.skip(f"Django application not reachable at {DJANGO_BASE_URL}")

# Add more Django-specific tests here, e.g.,
# - Course creation (if API exists)
# - Course enrollment
# - Viewing course content