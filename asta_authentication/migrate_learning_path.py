"""
Migration script to add LearningPath table to the database
Run this script to update the database schema
"""

from app import app, db
from models import LearningPath

def migrate_database():
    """Add LearningPath table if it doesn't exist"""
    with app.app_context():
        print("🔄 Starting database migration...")
        try:
            # Create all tables (will only create new ones)
            db.create_all()
            print("✅ Database migration completed successfully!")
            print("✅ LearningPath table is now available")
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    migrate_database()
