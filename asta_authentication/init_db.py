import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import app, db

def init_db():
    """Initialize the database and create all tables."""
    with app.app_context():
        # Create upload directories if they don't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['POST_UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['ARTICLE_UPLOAD_FOLDER'], exist_ok=True)
        
        # Create all database tables
        db.create_all()
        print("✅ Database tables created successfully!")

if __name__ == '__main__':
    init_db()
