# test_features.py

import pytest
import requests
import uuid
import os

# --- Test Configuration ---
BASE_URL = "http://127.0.0.1:5000"
API_URL = f"{BASE_URL}/api"

# --- Test Fixtures ---

@pytest.fixture(scope="module")
def test_user_and_token():
    """Creates a new user, logs them in, and returns the user data and JWT token."""
    unique_id = str(uuid.uuid4())
    user_data = {
        "email": f"feature_tester_{unique_id}@example.com",
        "password": f"TestPass123_{unique_id}"
    }

    # Register
    register_res = requests.post(f"{BASE_URL}/auth/register", json=user_data)
    assert register_res.status_code == 201

    # Login
    login_res = requests.post(f"{BASE_URL}/auth/login", json=user_data)
    assert login_res.status_code == 200
    token = login_res.json()['access_token']
    
    # Get user ID from profile
    headers = {"Authorization": f"Bearer {token}"}
    profile_res = requests.get(f"{BASE_URL}/profile/", headers=headers)
    assert profile_res.status_code == 200
    user_id = profile_res.json()['id']

    return {"id": user_id, "token": token, "headers": headers}

@pytest.fixture(scope="module")
def dummy_files():
    """Creates dummy files for upload tests and cleans them up afterward."""
    post_media_path = "dummy_post_image.png"
    article_media_path = "dummy_article_image.jpg"

    # Create simple dummy files
    with open(post_media_path, "w") as f:
        f.write("dummy image content")
    with open(article_media_path, "w") as f:
        f.write("dummy image content")

    yield {
        "post_media": post_media_path,
        "article_media": article_media_path
    }

    # Cleanup
    os.remove(post_media_path)
    os.remove(article_media_path)

# --- Test Suite ---

class TestFeatures:
    
    def test_create_post(self, test_user_and_token, dummy_files):
        """Tests creating a new post with media."""
        with open(dummy_files["post_media"], "rb") as f:
            files = {"media": (dummy_files["post_media"], f, "image/png")}
            data = {"content": "This is a test post with an image!"}
            
            response = requests.post(
                f"{API_URL}/posts",
                headers=test_user_and_token["headers"],
                files=files,
                data=data
            )
        
        assert response.status_code == 201
        post_data = response.json()
        assert post_data["content"] == "This is a test post with an image!"
        assert "media_url" in post_data
        assert post_data["media_url"] is not None
        assert post_data["author"]["id"] == test_user_and_token["id"]

    def test_get_post_feed(self, test_user_and_token):
        """Tests that the main feed contains the newly created post."""
        response = requests.get(f"{API_URL}/posts/feed", headers=test_user_and_token["headers"])
        assert response.status_code == 200
        feed_data = response.json()
        assert isinstance(feed_data, list)
        assert len(feed_data) > 0
        # Check if our post is in the feed (likely the first one)
        assert "This is a test post with an image!" in [p['content'] for p in feed_data]

    def test_create_article(self, test_user_and_token, dummy_files):
        """Tests creating a new article with a cover image."""
        with open(dummy_files["article_media"], "rb") as f:
            files = {"cover_image": (dummy_files["article_media"], f, "image/jpeg")}
            data = {
                "title": "My Test Article",
                "body": "<h1>Hello World</h1><p>This is the body of my article.</p>"
            }
            
            response = requests.post(
                f"{API_URL}/articles",
                headers=test_user_and_token["headers"],
                files=files,
                data=data
            )

        assert response.status_code == 201
        article_data = response.json()
        assert article_data["title"] == "My Test Article"
        assert article_data["body"] == "<h1>Hello World</h1><p>This is the body of my article.</p>"
        assert "cover_image_url" in article_data
        assert article_data["cover_image_url"] is not None
        # Store the created article ID for the next test
        pytest.article_id = article_data['id']

    def test_get_all_articles(self):
        """Tests the public endpoint to list all articles."""
        response = requests.get(f"{API_URL}/articles")
        assert response.status_code == 200
        articles_data = response.json()
        assert isinstance(articles_data, list)
        assert len(articles_data) > 0
        assert "My Test Article" in [a['title'] for a in articles_data]

    def test_get_single_article(self):
        """Tests the public endpoint to get a single article by ID."""
        assert hasattr(pytest, 'article_id'), "Article creation test must run first."
        article_id = pytest.article_id
        
        response = requests.get(f"{API_URL}/articles/{article_id}")
        assert response.status_code == 200
        article_data = response.json()
        assert article_data["id"] == article_id
        assert article_data["title"] == "My Test Article"
        assert "body" in article_data
