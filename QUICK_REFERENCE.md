# 🎓 Learning Path Feature - Quick Reference

## 📝 What It Does

When seekers click "View Details" on a career recommendation, they can generate an AI-powered, personalized learning path that is **automatically recorded** in the database.

## 🔄 User Flow

```
Career GPS Results → View Details → Generate My Learning Path → AI Creates Path → Path Saved to Database → Display Path → Access Anytime
```

## 🚀 Quick Start

### 1. Setup (One-time)

```bash
cd asta_authentication
python migrate_learning_path.py
```

### 2. Start Services

```bash
# Terminal 1: AI Guru
cd ai-guru/backend
python main.py

# Terminal 2: Asta Auth
cd asta_authentication
python app.py
```

### 3. Test

1. Go to your profile
2. Click "Discover My Career Path"
3. Complete quiz
4. Click "View Details" on any career
5. Click "Generate My Learning Path"
6. Wait 10-30 seconds
7. View your personalized path!

## 📊 What Gets Recorded

Every generated learning path saves:

- ✅ User ID (who)
- ✅ Career Name (what)
- ✅ Career Summary
- ✅ Match Percentage
- ✅ Complete Learning Content (JSON)
- ✅ Creation Timestamp (when)
- ✅ Progress (0-100%)
- ✅ Active Status

## 🎨 What Seeker Sees

### Learning Path Contains:

- **Overview**: Personalized explanation
- **Duration**: Estimated time (e.g., "6-12 months")
- **3-5 Phases**: Structured progression
  - Skills to learn
  - Specific courses (Coursera, Udemy, etc.)
  - Practice projects
  - Milestones
- **Certifications**: Industry credentials
- **Resources**: Books, communities, tools
- **Networking Tips**: Build connections
- **Success Metrics**: Track progress

## 🔗 New Routes

### Backend Routes

- `/profile/generate-learning-path/<index>` - Generate & save path
- `/profile/learning-path/<id>` - View specific path
- `/profile/learning-paths` - List all user's paths

### API Endpoint

- `POST /career-gps/learning-path` - AI generation (port 8001)

## 💾 Database

### New Table: `LearningPath`

```sql
- id (Primary Key)
- user_id (Foreign Key → User)
- career_name (VARCHAR 150)
- career_summary (TEXT)
- match_percentage (INTEGER)
- learning_path_data (TEXT/JSON)
- progress (INTEGER, default 0)
- completed_items (TEXT/JSON array)
- is_active (BOOLEAN)
- created_at (DATETIME)
- updated_at (DATETIME)
```

## 🤖 AI Magic

Uses Gemini 2.5 Flash to generate:

- Personalized based on user's education, skills, experience
- Structured JSON with phases, courses, projects
- Fallback to default template if AI unavailable
- 20-30 second generation time

## 🎯 Key Features

### For Seekers

- ✅ Personalized roadmap
- ✅ Clear progression path
- ✅ Actionable steps
- ✅ Save multiple paths
- ✅ Track progress
- ✅ Access anytime

### For Platform

- ✅ Records all career choices
- ✅ Tracks user interests
- ✅ Increases engagement
- ✅ Shows AI power
- ✅ Competitive advantage

## 📱 Access Points

Seekers can access learning paths from:

1. **Direct Generation**: Career GPS results → View Details → Generate
2. **My Learning Paths**: New page listing all paths
3. **Profile**: Link to learning paths
4. **Career GPS Page**: View existing paths

## ⚙️ Configuration

### Required

- AI Guru running on `http://localhost:8001`
- Database with `LearningPath` table
- Gemini API key configured

### Optional Settings

- Generation timeout: 60 seconds
- Max output tokens: 4096
- Temperature: 0.5 (balance creativity/consistency)

## 🔍 Verify Installation

```python
# Check database
from app import app, db
from models import LearningPath

with app.app_context():
    count = LearningPath.query.count()
    print(f"Learning paths in DB: {count}")
```

## 🐛 Troubleshooting

| Issue                  | Solution                        |
| ---------------------- | ------------------------------- |
| AI service unavailable | Will use default template       |
| Slow generation        | Increase timeout (60s default)  |
| Duplicate paths        | System checks & reuses existing |
| No paths showing       | Complete Career GPS quiz first  |
| Database error         | Run migration again             |

## 📈 Success Metrics

Track:

- Number of paths generated
- Most popular careers
- Average progress
- Completion rates
- User engagement time

## 🎉 Benefits

### Immediate Value

- Complete career guidance system
- Records user career decisions
- Provides actionable learning plans
- Increases platform stickiness

### Long-term Value

- Career preference data
- Learning path analytics
- User success tracking
- Recommendation improvements

## 📚 Documentation

Full docs available:

- `LEARNING_PATH_FEATURE.md` - Complete technical docs
- `LEARNING_PATH_SETUP.md` - Setup instructions
- `LEARNING_PATH_SUMMARY.md` - Implementation details
- `IMPLEMENTATION_CHECKLIST.md` - Verification checklist

## 🎬 Demo Flow

1. **Login** as seeker
2. **Navigate** to Career GPS
3. **Complete** quiz (2 minutes)
4. **View** 3-5 career recommendations
5. **Click** "View Details" on top match
6. **Generate** learning path (30 seconds)
7. **Explore** phases, courses, projects
8. **Save** and return anytime
9. **Track** progress over time

## ✅ Quick Checklist

Before going live:

- [ ] Database migration completed
- [ ] AI Guru service running
- [ ] Test path generation
- [ ] Verify path display
- [ ] Check "My Learning Paths" page
- [ ] Test multiple careers
- [ ] Confirm database records

## 🚀 Go Live!

Once checklist complete:

1. ✅ Feature is production-ready
2. ✅ All paths are recorded
3. ✅ Users get instant value
4. ✅ Platform gains competitive edge

---

**Need Help?** Check the full documentation or review backend logs for detailed error messages.

**Status**: 🟢 Production Ready
