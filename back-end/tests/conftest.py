import pytest
from app import create_app
import os

@pytest.fixture
def client():
    # Set environment variables for the test database
    os.environ["MONGO_URI"] = "mongodb://localhost:27017/test_db"
    os.environ["MONGO_DBNAME"] = "test_db"
    app = create_app()
    app.config["TESTING"] = True

    # Test client for simulating HTTP requests
    with app.test_client() as client:
        yield client
