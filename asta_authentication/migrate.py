import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from flask import Flask
from flask_migrate import Migrate
from flask.cli import FlaskGroup

# Import the Flask app and db from the package
from app import app, db

# Initialize Flask-Migrate
migrate = Migrate(app, db)
cli = FlaskGroup(app)

@cli.command()
def create_db():
    """Create the database and tables."""
    with app.app_context():
        # Create upload directories if they don't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['POST_UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['ARTICLE_UPLOAD_FOLDER'], exist_ok=True)
        
        # Create all database tables
        db.create_all()
        print("Database tables created successfully!")

@cli.command()
def drop_db():
    """Drop the database tables."""
    with app.app_context():
        db.drop_all()
        print("Database tables dropped!")

@cli.command()
def reset_db():
    """Drop and recreate database tables."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database reset complete!")

if __name__ == '__main__':
    cli()
