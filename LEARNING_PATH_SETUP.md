# Quick Setup Guide - Learning Path Feature

## Prerequisites

- AI Guru backend running on port 8001
- Asta Authentication app running
- Database configured

## Setup Steps

### 1. Run Database Migration

```bash
cd asta_authentication
python migrate_learning_path.py
```

This creates the `LearningPath` table in your database.

### 2. Ensure AI Guru is Running

```bash
cd ai-guru/backend
python main.py
```

Should see:

```
🚀 Starting AI Guru Multibot Backend...
📡 API Documentation: http://localhost:8001/docs
```

### 3. Test the Feature

#### Step 1: Take Career GPS Quiz

1. Navigate to your profile
2. Click "Discover My Career Path"
3. Complete the quiz
4. Submit answers

#### Step 2: Generate Learning Path

1. On results page, click "View Details" on any career
2. Click "Generate My Learning Path" button
3. Wait 10-30 seconds for AI generation
4. View your personalized learning path!

#### Step 3: View All Paths

- Navigate to "My Learning Paths" from your profile
- See all generated learning paths
- Click to view details anytime

## Verify Installation

### Check Database

```python
# In Python shell
from app import app, db
from models import LearningPath

with app.app_context():
    paths = LearningPath.query.all()
    print(f"Found {len(paths)} learning paths")
```

### Check API

```bash
# Test endpoint
curl http://localhost:8001/career-gps/learning-path -X POST \
  -H "Content-Type: application/json" \
  -d '{"career_name": "Test", "career_summary": "Test", "match_percentage": 75}'
```

## Troubleshooting

### "AI Guru service is unavailable"

- Check if AI Guru is running: `http://localhost:8001/docs`
- Check firewall/network settings
- Feature will use default template if service unavailable

### Database Error

- Run migration again: `python migrate_learning_path.py`
- Check database connection in config
- Verify SQLite file permissions

### No Learning Paths Showing

- Complete Career GPS quiz first
- Check if paths are saved: Query database
- Check browser console for errors

## Success Indicators

✅ Migration completes without errors
✅ AI Guru service responds at port 8001
✅ "Generate My Learning Path" button appears in modal
✅ Learning path displays with phases, courses, projects
✅ Path appears in "My Learning Paths" page

## Next Steps

After setup:

1. Test with different career choices
2. Verify paths are personalized
3. Check progress tracking
4. Explore all learning path features

## Support

Issues? Check:

- Console logs (backend and frontend)
- Database records
- API responses
- Network connectivity

Happy learning! 🎓
