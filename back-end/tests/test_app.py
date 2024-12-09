import pytest
from app import create_app
from unittest.mock import patch

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client


def test_index_redirect(client):
    response = client.get("/")
    assert response.status_code == 302  # Redirect to login
    assert response.location.endswith("/login")


def test_home_page(client):
    response = client.get("/home")
    assert response.status_code == 302


def test_recommendation_page(client):
    response = client.get("/recommendation")
    assert response.status_code == 200
    assert b"Recommendation" in response.data


def test_entry_page(client):
    response = client.get("/entry")
    assert response.status_code == 200
    assert b"Entry" in response.data


def test_entry_submission_page(client):
    response = client.get("/entry-submission")
    assert response.status_code == 302


def test_signup(client):
    response = client.post(
        "/signup", data={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 302  # Redirect after signup

    response = client.post("/signup", data={"username": "testuser"})
    assert response.status_code == 302

    response = client.post(
        "/signup", data={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 302


def test_logout(client):
    client.post("/signup", data={"username": "testuser", "password": "testpass"})
    client.post("/login", data={"username": "testuser", "password": "testpass"})

    response = client.get("/logout")
    assert response.status_code == 302  # Redirect to login page


def test_login_invalid_user(client):
    response = client.post(
        "/login", data={"username": "fakeuser", "password": "fakepass"}
    )
    assert response.status_code == 200
    assert b"Invalid username or password." in response.data


def test_search_songs_no_input(client):
    """Test search functionality with no input."""
    response = client.get("/search-songs?songname=")
    assert response.status_code == 200
    assert b"No songs found" in response.data


def test_signup_missing_fields(client):
    """测试注册时缺少必填字段的情况。"""
    response = client.post("/signup", data={"username": ""}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Missing required fields" in response.data


def test_login_missing_fields(client):
    """Test login with missing fields."""
    response = client.post("/login", data={"username": ""})
    assert response.status_code == 200
    assert b"Invalid username or password." in response.data

def test_playlist_page(client):
    """Test viewing the playlists page."""
    response = client.get("/playlists")
    assert response.status_code == 302
