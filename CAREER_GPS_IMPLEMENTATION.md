# Career GPS Feature Implementation Guide

## Overview
This document provides a comprehensive guide for implementing the Career GPS feature across the Astra monorepo. The Career GPS helps users identify their ideal career direction through an AI-driven process and displays personalized career paths on their profile.

## Architecture

### Components
1. **Data Model** (`asta_authentication/models.py`)
   - `CareerGPS` model to store user career preferences and AI-generated recommendations

2. **Backend Routes** (`asta_authentication/profile_routes.py`)
   - Career GPS quiz and result processing
   - Integration with AI Guru service

3. **Frontend Templates** (`asta_authentication/templates/profile/`)
   - Career GPS quiz interface
   - Results display
   - Profile integration

4. **AI Service** (`ai-guru/backend/services/career_gps_service.py`)
   - Career recommendation engine
   - Personalized roadmap generation

5. **API Endpoints** (`ai-guru/backend/main.py`)
   - REST API for career recommendations
   - Roadmap generation service

## Implementation Steps

### 1. Database Model Setup
The `CareerGPS` model has been added to `asta_authentication/models.py` with the following fields:
- User relationship
- Career discovery quiz responses (interests, skills, goal, motivation, learning_style)
- AI generated results (top_careers, selected_career, progress)

### 2. Backend Routes
Routes have been added to `profile_routes.py`:
- `/career-gps` - Main dashboard
- `/career-gps/start` - Quiz interface
- `/career-gps/process/<gps_id>` - AI processing
- `/career-gps/select/<gps_id>/<career_index>` - Career selection

### 3. Frontend Implementation
Templates created:
- `career_gps_quiz.html` - Interactive career discovery quiz
- `career_gps_results.html` - AI-generated recommendations
- `career_gps.html` - Career dashboard
- Profile view updated to display Career GPS banner and roadmap

### 4. AI Integration
- Created `career_gps_service.py` in AI Guru backend
- Added API endpoints for recommendations and roadmaps
- Implemented fallback mechanisms for when AI service is unavailable

## Integration Points

### With AI Guru
- REST API calls from Flask to FastAPI service
- Fallback to default recommendations when AI is unavailable
- Context-aware prompts for career recommendations

### With Astra Learning Paths
- Learning path identifiers included in AI recommendations
- Future integration with Django-based learning modules

### With Mentorship Marketplace
- Mentor categories suggested by AI
- Future integration for connecting with actual mentors

## API Endpoints

### AI Guru Endpoints
1. `POST /career-gps/recommendations`
   - Generates career recommendations based on user input
   - Returns top 3 matches with details

2. `GET /career-gps/roadmap/{career_name}`
   - Generates personalized roadmap for selected career
   - Returns milestones and resources

### Authentication App Endpoints
1. `GET /profile/career-gps`
   - Career GPS dashboard

2. `GET /profile/career-gps/start`
   - Career discovery quiz

3. `POST /profile/career-gps/start`
   - Processes quiz responses

4. `GET /profile/career-gps/process/<gps_id>`
   - AI processing of career recommendations

5. `GET /profile/career-gps/select/<gps_id>/<career_index>`
   - Selects a career path

## Deployment Considerations

### Environment Variables
- Ensure AI Guru service is running on port 8001
- Configure Gemini API key in AI Guru `.env` file

### Dependencies
- All required dependencies are already present in the monorepo
- No additional packages needed for basic implementation

### Error Handling
- Fallback mechanisms for when AI service is unavailable
- Default career recommendations provided
- Graceful degradation of features

## Future Enhancements

### Progress Tracking
- Integration with learning path completion
- Mentor interaction tracking
- Skill assessment updates

### Advanced Features
- Career transition recommendations
- Salary and job market data integration
- Alumni network connections
- Certification pathway integration

### AI Improvements
- Personalized learning content generation
- Real-time progress feedback
- Adaptive roadmap adjustments

## Testing
- Unit tests for AI service functions
- Integration tests for API endpoints
- UI tests for quiz flow
- Fallback mechanism validation

## Maintenance
- Regular updates to career database
- AI model improvements
- User feedback incorporation