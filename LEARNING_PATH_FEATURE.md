# AI-Powered Learning Path Generation Feature

## Overview

This feature generates personalized, AI-powered learning paths for career seekers when they click "View Details" on a recommended career from the Career GPS results. Each learning path is unique to the user's profile and chosen career.

## How It Works

### User Flow

1. **Seeker takes Career GPS Quiz** → Gets 3-5 career recommendations
2. **Clicks "View Details"** on a career → Opens modal with career details
3. **Clicks "Generate My Learning Path"** → AI generates personalized roadmap
4. **Learning path is saved** → Recorded in database for future reference
5. **View anytime** → Access from "My Learning Paths" page

## Key Features

### ✅ Personalized Learning Paths

- **AI-Generated**: Uses Gemini AI to create custom learning roadmaps
- **Profile-Based**: Considers user's education, skills, experience
- **Multi-Phase**: Structured progression from beginner to job-ready
- **Actionable**: Specific courses, projects, certifications

### ✅ Path Recording

- **Database Storage**: Each generated path is saved to `LearningPath` table
- **Progress Tracking**: Monitor completion percentage
- **Multiple Paths**: Users can have learning paths for different careers
- **Active Path**: Mark one path as currently active

### ✅ Comprehensive Content

Each learning path includes:

- **Overview**: Personalized explanation
- **Phases**: 3-5 structured learning phases
- **Courses**: Specific course recommendations with platforms
- **Projects**: Hands-on practice projects
- **Certifications**: Industry-recognized credentials
- **Resources**: Books, communities, tools
- **Networking Tips**: Build professional connections
- **Success Metrics**: Track progress milestones

## Technical Architecture

### Backend Components

#### 1. Database Model (`models.py`)

```python
class LearningPath(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    career_name = db.Column(db.String(150))
    career_summary = db.Column(db.Text)
    match_percentage = db.Column(db.Integer)
    learning_path_data = db.Column(db.Text)  # JSON
    progress = db.Column(db.Integer, default=0)
    completed_items = db.Column(db.Text)  # JSON array
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
```

#### 2. AI Service (`career_gps_service.py`)

- `generate_personalized_learning_path()`: Main AI generation function
- `generate_default_learning_path()`: Fallback when AI unavailable
- Uses Gemini 2.5 Flash model for generation

#### 3. API Endpoint (`main.py` - AI Guru)

```python
POST /career-gps/learning-path
{
    "career_name": "Data Scientist",
    "career_summary": "...",
    "match_percentage": 85,
    "user_profile": {...}
}
```

#### 4. Routes (`profile_routes.py`)

- `/profile/generate-learning-path/<career_index>`: Generate path
- `/profile/learning-path/<path_id>`: View path
- `/profile/learning-paths`: List all user's paths

### Frontend Components

#### 1. Career Results Page (`career_gps_results.html`)

- Modified "View Details" button to link to learning path generation
- Modal shows career details + "Generate My Learning Path" button

#### 2. Learning Path Display (`learning_path.html`)

- Comprehensive view with sidebar navigation
- Expandable phases with courses, projects, milestones
- Progress tracking
- Resource links and networking tips

#### 3. My Learning Paths (`my_learning_paths.html`)

- Grid view of all user's learning paths
- Progress indicators
- Quick access to view each path

## Data Flow

```
1. User clicks "Generate My Learning Path"
   ↓
2. Frontend → Profile Routes → generate_learning_path(career_index)
   ↓
3. Check if path already exists in DB
   ↓
4. If not, call AI Guru API → /career-gps/learning-path
   ↓
5. AI Guru → career_gps_service.generate_personalized_learning_path()
   ↓
6. Gemini AI generates comprehensive roadmap
   ↓
7. Save to database as LearningPath record
   ↓
8. Redirect to learning_path.html display
   ↓
9. User can track progress and return anytime
```

## AI Prompt Engineering

The AI prompt includes:

- **Career details**: Name, summary, match percentage
- **User profile**: Education, experience, skills, learning style
- **Structure requirements**: Exact JSON format with phases, courses, projects
- **Personalization**: Tailored to user's current level
- **Actionability**: Real courses and resources

## Database Migration

Run this command to create the LearningPath table:

```bash
python migrate_learning_path.py
```

## Configuration

### AI Guru Service

- Must be running on `http://localhost:8001`
- Uses Gemini API key from config
- Timeout: 60 seconds for generation

### Fallback Strategy

- If AI service unavailable → Use default template
- If JSON parsing fails → Use structured fallback
- Always ensures user gets a learning path

## Benefits

### For Seekers

✅ **Personalized Guidance**: Custom roadmap based on their profile
✅ **Clear Structure**: Step-by-step progression
✅ **Actionable Steps**: Real courses, projects, certifications
✅ **Progress Tracking**: Monitor learning journey
✅ **Recorded History**: Access paths anytime

### For Platform

✅ **Engagement**: Users spend more time on platform
✅ **Retention**: Clear value proposition
✅ **Data Collection**: Track popular careers and learning paths
✅ **AI Showcase**: Demonstrates AI capabilities

## Future Enhancements

1. **Progress Marking**: Mark courses/projects as complete
2. **Path Updates**: Refresh paths with new content
3. **Social Features**: Share paths with mentors
4. **Integration**: Link to actual course providers
5. **Analytics**: Track completion rates and success
6. **Notifications**: Remind users about milestones
7. **Gamification**: Badges and achievements

## Testing

### Manual Testing Steps

1. Complete Career GPS quiz
2. Click "View Details" on any career
3. Click "Generate My Learning Path"
4. Verify path is generated and displayed
5. Check database for LearningPath record
6. Navigate to "My Learning Paths"
7. Verify path appears in list

### API Testing

```bash
# Test learning path generation
curl -X POST http://localhost:8001/career-gps/learning-path \
  -H "Content-Type: application/json" \
  -d '{
    "career_name": "Data Scientist",
    "career_summary": "Analyze data to drive decisions",
    "match_percentage": 85,
    "user_profile": {...}
  }'
```

## Troubleshooting

### Issue: AI Guru service not responding

**Solution**: Check if service is running, use default templates

### Issue: JSON parsing error

**Solution**: Improved error handling with fallback paths

### Issue: Duplicate paths

**Solution**: Check for existing paths before generating

### Issue: Slow generation

**Solution**: Async processing or background jobs (future)

## Files Modified/Created

### Modified

- `models.py` - Added LearningPath model
- `profile_routes.py` - Added learning path routes
- `career_gps_service.py` - Added AI generation function
- `main.py` (AI Guru) - Added API endpoint
- `career_gps_results.html` - Updated button link

### Created

- `learning_path.html` - Display template
- `my_learning_paths.html` - List template
- `migrate_learning_path.py` - Migration script
- `LEARNING_PATH_FEATURE.md` - This documentation

## Conclusion

This feature transforms Career GPS from a recommendation tool into a complete career development platform. Each learning path is:

- **AI-generated** for personalization
- **Recorded** for future reference
- **Structured** for clear progression
- **Actionable** with real resources

It provides immense value to seekers while showcasing the platform's AI capabilities.
