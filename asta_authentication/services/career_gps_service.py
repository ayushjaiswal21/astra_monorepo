import json
import re

def validate_and_preprocess_list(input_list, field_name):
    """Validate and preprocess list inputs"""
    if not input_list:
        return []

    if not isinstance(input_list, list):
        print(f"Warning: {field_name} should be a list, got {type(input_list)}")
        return []

    # Clean and validate each item
    cleaned_list = []
    for item in input_list:
        if isinstance(item, str) and item.strip():
            # Remove extra whitespace and limit length
            cleaned_item = item.strip()[:100]  # Max 100 chars per item
            if cleaned_item:
                cleaned_list.append(cleaned_item)

    # Remove duplicates while preserving order
    seen = set()
    unique_list = []
    for item in cleaned_list:
        item_lower = item.lower()
        if item_lower not in seen:
            seen.add(item_lower)
            unique_list.append(item)

    return unique_list[:20]  # Max 20 items

def validate_and_preprocess_text(input_text, field_name):
    """Validate and preprocess text inputs"""
    if not input_text:
        return ""

    if not isinstance(input_text, str):
        print(f"Warning: {field_name} should be a string, got {type(input_text)}")
        return ""

    # Clean the text
    cleaned_text = input_text.strip()

    # Remove potentially harmful content (basic sanitization)
    cleaned_text = re.sub(r'[<>]', '', cleaned_text)

    # Limit length
    return cleaned_text[:500]  # Max 500 characters

def categorize_industry(career_name, summary):
    """Categorize career into industry for diversity checking"""
    text = (career_name + " " + summary).lower()

    industry_keywords = {
        'technology': ['software', 'developer', 'engineer', 'tech', 'programming', 'data', 'ai', 'cybersecurity', 'it'],
        'design': ['designer', 'design', 'creative', 'ux', 'ui', 'graphic', 'artist', 'visual'],
        'business': ['manager', 'analyst', 'consultant', 'business', 'marketing', 'sales', 'finance', 'operations'],
        'healthcare': ['health', 'medical', 'nurse', 'doctor', 'therapist', 'patient', 'clinical', 'pharma'],
        'education': ['teacher', 'educator', 'trainer', 'professor', 'instructor', 'learning', 'academic'],
        'creative': ['writer', 'content', 'media', 'journalist', 'editor', 'artist', 'creative'],
        'science': ['scientist', 'research', 'lab', 'chemistry', 'biology', 'physics', 'researcher'],
        'engineering': ['engineer', 'engineering', 'architect', 'construction', 'manufacturing']
    }

    for industry, keywords in industry_keywords.items():
        if any(keyword in text for keyword in keywords):
            return industry

    return 'general'

def build_profile_context(user_profile):
    """Build comprehensive profile context for analysis"""
    if not user_profile:
        return ""

    context_parts = ["\nCOMPREHENSIVE USER PROFILE DATA:"]

    # Basic info
    basic = user_profile.get('basic_info', {})
    if basic:
        context_parts.append(f"""
Basic Information:
- Name: {basic.get('name', 'Not specified')}
- Headline: {basic.get('headline', 'Not specified')}
- Location: {basic.get('location', 'Not specified')}
- University: {basic.get('university', 'Not specified')}
- About: {basic.get('about', 'Not specified')[:200]}...
- Role: {basic.get('role', 'Not specified')}""")

    # Education
    education = user_profile.get('education', [])
    if education:
        context_parts.append(f"""
Education History ({len(education)} entries):
{chr(10).join([f"- {edu.get('degree', 'Unknown')} from {edu.get('school', 'Unknown')} ({edu.get('dates', 'Unknown dates')})" for edu in education[:3]])}""")

    # Experience
    experience = user_profile.get('experience', [])
    if experience:
        context_parts.append(f"""
Work Experience ({len(experience)} entries):
{chr(10).join([f"- {exp.get('title', 'Unknown')} at {exp.get('company', 'Unknown')} ({exp.get('dates', 'Unknown dates')})" for exp in experience[:3]])}""")

    # Skills
    skills = user_profile.get('skills', [])
    if skills:
        context_parts.append(f"""
Existing Skills ({len(skills)} skills):
{', '.join(skills[:10])}{'...' if len(skills) > 10 else ''}""")

    # Certifications
    certifications = user_profile.get('certifications', [])
    if certifications:
        context_parts.append(f"""
Certifications ({len(certifications)} entries):
{chr(10).join([f"- {cert.get('name', 'Unknown')} from {cert.get('issuing_organization', 'Unknown')}" for cert in certifications[:3]])}""")

    # Career history
    career_history = user_profile.get('career_history')
    if career_history:
        context_parts.append(f"""
Career History:
- Previously selected career: {career_history.get('selected_career', 'None')}
- Current progress: {career_history.get('progress', 0)}%
- Career GPS started: {career_history.get('created_at', 'Unknown')}""")

    return '\n'.join(context_parts)

def analyze_career_preferences(interests, skills, goal, motivation, learning_style, user_profile=None):
    """
    Analyze user's career preferences and generate personalized career recommendations.
    
    Args:
        interests (list): List of user interests
        skills (list): List of user skills
        goal (str): User's career goal
        motivation (str): User's life motivation
        learning_style (str): User's preferred learning style
        user_profile (dict): Comprehensive user profile data including education, experience, etc.
    
    Returns:
        list: Personalized career recommendations with details
    """
    
    # Input validation and preprocessing
    interests = validate_and_preprocess_list(interests, "interests")
    skills = validate_and_preprocess_list(skills, "skills")
    goal = validate_and_preprocess_text(goal, "goal")
    motivation = validate_and_preprocess_text(motivation, "motivation")
    learning_style = validate_and_preprocess_text(learning_style, "learning_style")
    
    # Generate personalized recommendations based on user profile
    return generate_personalized_recommendations(interests, skills, goal, motivation, learning_style, user_profile)

def generate_personalized_recommendations(interests, skills, goal, motivation, learning_style, user_profile=None):
    """Generate personalized recommendations based on user profile without AI"""
    
    # Start with default recommendations
    recommendations = [
        {
            "name": "UX Designer",
            "match": 85,
            "summary": "Create meaningful experiences for users by designing intuitive interfaces.",
            "skills": ["User Research", "Wireframing", "Prototyping", "Interaction Design"],
            "mentors": ["Design Experts", "Product Managers"],
            "learning_path": "design-fundamentals"
        },
        {
            "name": "Data Scientist",
            "match": 78,
            "summary": "Extract insights from data to drive business decisions and innovation.",
            "skills": ["Python", "Statistics", "Machine Learning", "Data Visualization"],
            "mentors": ["Senior Data Scientists", "Analytics Leaders"],
            "learning_path": "data-science-basics"
        },
        {
            "name": "Full Stack Developer",
            "match": 72,
            "summary": "Build complete web applications from frontend to backend systems.",
            "skills": ["JavaScript", "React", "Node.js", "Database Management"],
            "mentors": ["Lead Developers", "Engineering Managers"],
            "learning_path": "full-stack-development"
        }
    ]
    
    # Personalize based on user profile if available
    if user_profile:
        # Extract skills from profile
        profile_skills = user_profile.get('skills', [])
        if profile_skills:
            # Add user's existing skills to the recommendations
            for rec in recommendations:
                # Mix user's skills with recommended skills
                user_skill_count = min(2, len(profile_skills))
                rec['skills'] = profile_skills[:user_skill_count] + rec['skills']
        
        # Personalize summary based on user's about section
        about = user_profile.get('basic_info', {}).get('about', '').lower()
        if 'design' in about or 'creative' in about:
            recommendations[0]['match'] = 95  # Higher match for UX Designer
            recommendations[0]['summary'] = "Perfect match for your creative background. Create meaningful experiences for users by designing intuitive interfaces."
        elif 'data' in about or 'analysis' in about:
            recommendations[1]['match'] = 92  # Higher match for Data Scientist
            recommendations[1]['summary'] = "Ideal for your analytical mindset. Extract insights from data to drive business decisions and innovation."
        elif 'development' in about or 'programming' in about:
            recommendations[2]['match'] = 88  # Higher match for Full Stack Developer
            recommendations[2]['summary'] = "Aligns with your technical interests. Build complete web applications from frontend to backend systems."
    
    # Adjust based on interests
    if interests:
        interest_text = ' '.join(interests).lower()
        if any(word in interest_text for word in ['design', 'art', 'creative', 'visual', 'ui', 'ux']):
            recommendations[0]['match'] = max(recommendations[0]['match'], 90)
        if any(word in interest_text for word in ['data', 'analytics', 'statistics', 'math', 'research']):
            recommendations[1]['match'] = max(recommendations[1]['match'], 85)
        if any(word in interest_text for word in ['programming', 'coding', 'software', 'tech', 'computer']):
            recommendations[2]['match'] = max(recommendations[2]['match'], 80)
    
    # Sort by match percentage
    recommendations.sort(key=lambda x: x['match'], reverse=True)
    
    return recommendations

def get_career_roadmap(career_name, user_progress):
    """
    Generate a personalized roadmap for a selected career path.
    
    Args:
        career_name (str): The selected career path
        user_progress (int): Current progress percentage
    
    Returns:
        dict: Career roadmap with milestones and resources
    """
    
    # Return a default roadmap
    return {
        "career": career_name,
        "milestones": [
            {
                "title": "Foundation Building",
                "description": "Master the fundamental concepts and skills required for your chosen career path.",
                "timeframe": "3-6 months"
            },
            {
                "title": "Skill Application",
                "description": "Apply your knowledge through projects, internships, or volunteer work to gain practical experience.",
                "timeframe": "6-12 months"
            },
            {
                "title": "Networking & Mentorship",
                "description": "Connect with professionals in your field and find mentors to guide your career development.",
                "timeframe": "Ongoing"
            },
            {
                "title": "Specialization",
                "description": "Focus on specific areas within your career path to develop expertise and stand out.",
                "timeframe": "6-18 months"
            },
            {
                "title": "Career Launch",
                "description": "Secure your first position or major opportunity in your chosen career field.",
                "timeframe": "3-12 months"
            }
        ],
        "mentors": ["Industry Professionals", "Career Coaches"],
        "resources": ["Online Courses", "Professional Associations", "Industry Events"]
    }