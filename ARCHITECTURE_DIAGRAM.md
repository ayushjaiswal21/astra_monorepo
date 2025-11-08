# Learning Path Feature - Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LEARNING PATH GENERATION FLOW                    │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│   SEEKER     │
│  (Frontend)  │
└──────┬───────┘
       │
       │ 1. Takes Career GPS Quiz
       ↓
┌─────────────────────────┐
│  Career GPS Results     │
│  - Top 3-5 careers      │
│  - Match percentages    │
│  - Summaries           │
└──────┬──────────────────┘
       │
       │ 2. Clicks "View Details"
       ↓
┌─────────────────────────┐
│   Career Details Modal  │
│  - Name & Summary       │
│  - Skills needed        │
│  - Mentors             │
│  - [Generate Path] BTN  │
└──────┬──────────────────┘
       │
       │ 3. Clicks "Generate My Learning Path"
       ↓
┌──────────────────────────────────────────────────────────────┐
│              BACKEND: profile_routes.py                       │
│                                                               │
│  /profile/generate-learning-path/<career_index>               │
│                                                               │
│  Step 1: Get Career GPS data from DB                          │
│  Step 2: Extract selected career info                         │
│  Step 3: Check if learning path already exists                │
│          ├─ YES → Redirect to existing path                   │
│          └─ NO → Continue to generation                       │
│  Step 4: Get comprehensive user profile                       │
│  Step 5: Call AI Guru API ──────────────────────┐            │
└──────────────────────────────────────────────────┼────────────┘
                                                   │
                                                   ↓
       ┌───────────────────────────────────────────────────────┐
       │            AI GURU BACKEND (Port 8001)                │
       │                                                        │
       │  POST /career-gps/learning-path                        │
       │                                                        │
       │  Receives:                                             │
       │  - career_name: "Data Scientist"                       │
       │  - career_summary: "..."                               │
       │  - match_percentage: 85                                │
       │  - user_profile: {education, skills, experience...}    │
       │                                                        │
       │  Calls: career_gps_service.py                          │
       │         ↓                                              │
       │  generate_personalized_learning_path()                 │
       │         ↓                                              │
       │  ┌──────────────────────────────┐                     │
       │  │   GEMINI AI (Google)         │                     │
       │  │   Model: gemini-2.5-flash    │                     │
       │  │                              │                     │
       │  │   Prompt includes:           │                     │
       │  │   - Career details           │                     │
       │  │   - User profile             │
       │  │   - Current skills           │                     │
       │  │   - Education background     │                     │
       │  │   - Learning style           │                     │
       │  │                              │                     │
       │  │   Generates:                 │                     │
       │  │   - 3-5 learning phases      │                     │
       │  │   - Specific courses         │                     │
       │  │   - Practice projects        │                     │
       │  │   - Certifications           │                     │
       │  │   - Resources & tips         │                     │
       │  │                              │                     │
       │  │   Returns: Structured JSON   │                     │
       │  └──────────────┬───────────────┘                     │
       │                 │                                      │
       │                 ↓                                      │
       │  Parses & validates JSON                               │
       │  Adds fallback if needed                               │
       │  Returns learning path data                            │
       └─────────────────┬──────────────────────────────────────┘
                         │
                         │ Response with learning_path JSON
                         ↓
┌────────────────────────────────────────────────────────────────┐
│              BACKEND: profile_routes.py (continued)             │
│                                                                 │
│  Step 6: Receive learning path from AI Guru                     │
│  Step 7: Create new LearningPath record:                        │
│          ┌─────────────────────────────────────┐               │
│          │  LearningPath                       │               │
│          │  - user_id: current_user.id         │               │
│          │  - career_name: "Data Scientist"    │               │
│          │  - career_summary: "..."            │               │
│          │  - match_percentage: 85             │               │
│          │  - learning_path_data: JSON string  │               │
│          │  - progress: 0                      │               │
│          │  - completed_items: []              │               │
│          │  - is_active: True                  │               │
│          │  - created_at: NOW                  │               │
│          └─────────────────────────────────────┘               │
│  Step 8: Deactivate other user's active paths                   │
│  Step 9: Save to database (db.session.commit)                   │
│  Step 10: Redirect to view_learning_path                        │
└────────────────────────┬───────────────────────────────────────┘
                         │
                         ↓
┌────────────────────────────────────────────────────────────────┐
│                   LEARNING PATH DISPLAY                         │
│               (learning_path.html template)                     │
│                                                                 │
│  ┌──────────────┐  ┌────────────────────────────────┐         │
│  │  SIDEBAR     │  │   MAIN CONTENT                 │         │
│  │             │  │                                │         │
│  │ Navigation  │  │  ┌──────────────────────────┐ │         │
│  │ - Overview  │  │  │  Career Header           │ │         │
│  │ - Phases    │  │  │  - Name                  │ │         │
│  │ - Certs     │  │  │  - Match: 85%            │ │         │
│  │ - Resources │  │  │  - Duration: 6-12 months │ │         │
│  │ - Network   │  │  └──────────────────────────┘ │         │
│  │             │  │                                │         │
│  │ Progress    │  │  ┌──────────────────────────┐ │         │
│  │ [====  ] 0% │  │  │  Phase 1: Foundation     │ │         │
│  │             │  │  │  - Duration: 2-3 months  │ │         │
│  │ Quick Links │  │  │  - Skills to learn       │ │         │
│  │ [Career GPS]│  │  │  - Courses (expandable)  │ │         │
│  │ [My Paths]  │  │  │  - Projects (expandable) │ │         │
│  └──────────────┘  │  │  - Milestones           │ │         │
│                    │  └──────────────────────────┘ │         │
│                    │                                │         │
│                    │  ┌──────────────────────────┐ │         │
│                    │  │  Phase 2: Development    │ │         │
│                    │  │  ...                     │ │         │
│                    │  └──────────────────────────┘ │         │
│                    │                                │         │
│                    │  ┌──────────────────────────┐ │         │
│                    │  │  Certifications          │ │         │
│                    │  │  - Cert 1                │ │         │
│                    │  │  - Cert 2                │ │         │
│                    │  └──────────────────────────┘ │         │
│                    │                                │         │
│                    │  ┌──────────────────────────┐ │         │
│                    │  │  Resources & Tips        │ │         │
│                    │  └──────────────────────────┘ │         │
│                    └────────────────────────────────┘         │
└────────────────────────────────────────────────────────────────┘
                         │
                         │ User can now:
                         ↓
            ┌────────────────────────────┐
            │  - Read complete path      │
            │  - Navigate between phases │
            │  - Track progress          │
            │  - Return anytime          │
            │  - Generate more paths     │
            └────────────────────────────┘


═══════════════════════════════════════════════════════════════════

                     DATABASE SCHEMA

┌────────────────────────────────────────────────────────────────┐
│                        LearningPath Table                       │
├────────────────────────────────────────────────────────────────┤
│  id                  INTEGER PRIMARY KEY                        │
│  user_id             INTEGER FOREIGN KEY → User.id              │
│  career_name         VARCHAR(150) NOT NULL                      │
│  career_summary      TEXT                                       │
│  match_percentage    INTEGER                                    │
│  learning_path_data  TEXT (JSON)                                │
│                      {                                          │
│                        "phases": [...],                         │
│                        "certifications": [...],                 │
│                        "resources": [...],                      │
│                        ...                                      │
│                      }                                          │
│  progress            INTEGER DEFAULT 0                          │
│  completed_items     TEXT (JSON array)                          │
│  is_active           BOOLEAN DEFAULT True                       │
│  created_at          DATETIME                                   │
│  updated_at          DATETIME                                   │
└────────────────────────────────────────────────────────────────┘
          │
          │ One-to-Many Relationship
          ↓
┌────────────────────────────────────────────────────────────────┐
│                          User Table                             │
├────────────────────────────────────────────────────────────────┤
│  id                  INTEGER PRIMARY KEY                        │
│  username            VARCHAR(80)                                │
│  email               VARCHAR(120)                               │
│  ...                                                            │
│                                                                 │
│  learning_paths      Relationship → LearningPath               │
└────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════

                   KEY INTEGRATION POINTS

1. Career GPS → Learning Path Generation
   - Passes career index and user data
   - Seamless user experience

2. AI Guru Service
   - Standalone service on port 8001
   - Can be deployed independently
   - Fallback to default if unavailable

3. Database Recording
   - Every path automatically saved
   - Timestamped for tracking
   - Linked to user account

4. User Profile Integration
   - Uses existing profile system
   - No duplicate data entry
   - Personalization based on profile

5. Progress Tracking (Future)
   - Update progress field
   - Mark completed_items
   - Track over time


═══════════════════════════════════════════════════════════════════

                    ERROR HANDLING FLOW

    Generate Request
          ↓
    Check DB for existing path
          ├─ Found → Return existing
          └─ Not found → Continue
                 ↓
          Call AI Guru API
          ├─ Success (200) → Parse JSON
          │       ├─ Valid → Save to DB
          │       └─ Invalid → Use default template
          │
          ├─ Connection Error → Use default template
          ├─ Timeout → Use default template
          └─ Other Error → Use default template
                 ↓
          Always returns a learning path
          Never fails completely


═══════════════════════════════════════════════════════════════════

This architecture ensures:
✅ Automatic recording of all career choices
✅ Personalized AI-generated content
✅ Robust error handling
✅ Seamless user experience
✅ Scalable design
✅ Future-proof for enhancements
```
