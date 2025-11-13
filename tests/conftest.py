import os
import pytest

# Set environment variables before any application code is imported
# This ensures that the Flask app uses an in-memory SQLite database for tests
os.environ["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
os.environ["TEST"] = "true" # Explicitly set TEST to true for test-mode behavior

# You can add other fixtures or hooks here if needed
# For example, a fixture to initialize the database for each test
@pytest.fixture(scope="session")
def app():
    # Import the Flask app here to ensure environment variables are set first
    from asta_authentication.app import app as flask_app, db as flask_db

    with flask_app.app_context():
        flask_db.create_all()
        yield flask_app
        flask_db.drop_all()

@pytest.fixture(scope="function")
def client(app):
    return app.test_client()

@pytest.fixture(scope="function")
def runner(app):
    return app.test_cli_runner()
