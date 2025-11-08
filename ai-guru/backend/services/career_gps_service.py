import google.generativeai as genai
import config
import json
import re

# Configure Gemini API
genai.configure(api_key=config.GEMINI_API_KEY)

# Initialize the generative model (using the stable Gemini 2.5 Flash model)
model = genai.GenerativeModel('gemini-2.5-flash')  # Using stable Gemini 2.5 Flash

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
    """Build comprehensive profile context for AI analysis"""
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
        list: Top 3 career recommendations with details
    """

    # Input validation and preprocessing
    interests = validate_and_preprocess_list(interests, "interests")
    skills = validate_and_preprocess_list(skills, "skills")
    goal = validate_and_preprocess_text(goal, "goal")
    motivation = validate_and_preprocess_text(motivation, "motivation")
    learning_style = validate_and_preprocess_text(learning_style, "learning_style")

    # Process comprehensive user profile data
    profile_context = ""
    if user_profile:
        profile_context = build_profile_context(user_profile)
    
    # Create a comprehensive prompt for personalized career recommendations
    prompt = f"""
    You are an expert career counselor with extensive knowledge of diverse career fields. Analyze this user's comprehensive profile and provide 5 highly personalized career recommendations from different industries.

    USER PROFILE:
    Interests: {', '.join(interests) if interests else 'Not specified'}
    Skills: {', '.join(skills) if skills else 'Not specified'}
    Goal: {goal if goal else 'Not specified'}
    Motivation: {motivation if motivation else 'Not specified'}
    Learning Style: {learning_style if learning_style else 'Not specified'}

    {profile_context}

    REQUIREMENTS:
    - Provide exactly 5 diverse career recommendations from COMPLETELY DIFFERENT industries
    - Industries must include: Technology, Healthcare, Business, Creative Arts, Education, Science, Engineering, etc.
    - Each career must be realistic based on their education, experience, and skills
    - Include match percentage (60-95) based on profile compatibility
    - Skills should mix existing skills they have + new skills they need to develop
    - Ensure NO duplicate career types or similar roles
    - Return ONLY a valid JSON array with exactly 5 objects, no markdown or extra text

    JSON FORMAT:
    [
      {{
        "name": "Specific Career Title",
        "match": 85,
        "summary": "Detailed explanation of why this career fits their unique profile",
        "skills": ["Existing skill they have", "New skill to develop", "Another relevant skill"],
        "mentors": ["Specific mentor type 1", "Specific mentor type 2"],
        "learning_path": "specific-learning-path-identifier"
      }}
    ]

    IMPORTANT: Make each recommendation from a different industry sector and highly personalized to their profile.
    """
    
    try:
        # Generate response from AI with enhanced parameters
        print(f"🚀 Calling Gemini API with prompt length: {len(prompt)} characters")
        print(f"📝 User interests: {interests}")
        print(f"📝 User skills: {skills}")

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.4,  # lower for more consistent JSON
                top_p=0.9,
                max_output_tokens=2048,
                candidate_count=1
            )
        )

        # Handle blocked/empty responses
        if not getattr(response, 'candidates', None):
            print("⚠️ No candidates in response; likely blocked by safety filters.")
            return generate_relevant_defaults(interests, skills, goal)

        cand = response.candidates[0]
        parts = getattr(cand, 'content', None).parts if getattr(cand, 'content', None) else []
        if not parts:
            print("⚠️ Response had no content parts; safety or empty.")
            print(f"Safety ratings: {getattr(cand, 'safety_ratings', None)}")
            print(f"Finish reason: {getattr(cand, 'finish_reason', None)}")
            return generate_relevant_defaults(interests, skills, goal)

        # Extract text from parts safely
        text_chunks = []
        for p in parts:
            t = getattr(p, 'text', None)
            if isinstance(t, str):
                text_chunks.append(t)
        response_text = ("\n".join(text_chunks)).strip()
        print(f"🤖 AI Response received: {response_text[:200]}...")

        # Strip markdown fences if present
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # Parse JSON
        try:
            career_recommendations = json.loads(response_text)
            print(f"✅ JSON parsed successfully: {len(career_recommendations)} recommendations")
        except json.JSONDecodeError as json_error:
            print(f"❌ JSON parsing failed: {json_error}")
            print(f"Response text: {response_text}")
            return generate_relevant_defaults(interests, skills, goal)

        # Validate structure
        if not isinstance(career_recommendations, list):
            print("⚠️ Response is not a list; using defaults")
            return generate_relevant_defaults(interests, skills, goal)

        # Normalize and ensure fields
        validated = []
        seen_names = set()
        for rec in career_recommendations:
            if not isinstance(rec, dict):
                continue
            name = str(rec.get('name', '')).strip()
            if not name or name.lower() in seen_names:
                continue
            seen_names.add(name.lower())
            validated.append({
                'name': name,
                'match': int(rec.get('match', 75)),
                'summary': str(rec.get('summary', ''))[:400] or 'Personalized rationale unavailable.',
                'skills': rec.get('skills', []) or [],
                'mentors': rec.get('mentors', []) or [],
                'learning_path': rec.get('learning_path', 'general-path')
            })

        # Keep up to 5, ensure at least 3
        validated = validated[:5]
        if len(validated) < 3:
            defaults = generate_relevant_defaults(interests, skills, goal)
            for d in defaults:
                if len(validated) >= 3:
                    break
                if d['name'].lower() not in seen_names:
                    validated.append(d)
                    seen_names.add(d['name'].lower())

        return validated

    except Exception as e:
        print(f"❌ ERROR generating career recommendations: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return generate_relevant_defaults(interests, skills, goal)

def generate_relevant_defaults(interests, skills, goal):
    """Generate relevant default recommendations based on user profile"""
    defaults = []

    # Analyze interests and skills to provide relevant defaults
    interest_text = ' '.join(interests).lower() if interests else ''
    skills_text = ' '.join(skills).lower() if skills else ''
    goal_text = goal.lower() if goal else ''

    # Tech-focused defaults
    if any(word in interest_text + skills_text for word in ['programming', 'coding', 'software', 'tech', 'computer']):
        defaults.append({
            "name": "Software Developer",
            "match": 80,
            "summary": "Build innovative software solutions that solve real-world problems. This career leverages your technical interests and programming skills to create impactful applications.",
            "skills": ["Python", "JavaScript", "Problem Solving", "Version Control", "Database Design"],
            "mentors": ["Senior Developers", "Tech Leads", "Engineering Managers"],
            "learning_path": "software-development-fundamentals"
        })

    # Design-focused defaults
    if any(word in interest_text + skills_text for word in ['design', 'art', 'creative', 'visual', 'ui', 'ux']):
        defaults.append({
            "name": "UX/UI Designer",
            "match": 85,
            "summary": "Create beautiful and functional user experiences that delight users. This career combines your creative interests with user-centered design principles.",
            "skills": ["User Research", "Wireframing", "Prototyping", "Visual Design", "Usability Testing"],
            "mentors": ["Senior Designers", "Design Directors", "Product Managers"],
            "learning_path": "ux-ui-design-fundamentals"
        })

    # Data-focused defaults
    if any(word in interest_text + skills_text for word in ['data', 'analytics', 'statistics', 'math', 'research']):
        defaults.append({
            "name": "Data Analyst",
            "match": 78,
            "summary": "Transform raw data into actionable insights that drive business decisions. This analytical career path suits those who enjoy working with numbers and patterns.",
            "skills": ["SQL", "Excel", "Data Visualization", "Statistics", "Python"],
            "mentors": ["Senior Analysts", "Data Scientists", "Business Intelligence Managers"],
            "learning_path": "data-analysis-basics"
        })

    # Business/Management defaults
    if any(word in interest_text + skills_text + goal_text for word in ['business', 'management', 'leadership', 'team', 'strategy']):
        defaults.append({
            "name": "Project Manager",
            "match": 75,
            "summary": "Lead teams and projects to successful completion while managing resources and stakeholders. This career focuses on coordination, communication, and strategic planning.",
            "skills": ["Project Planning", "Team Leadership", "Communication", "Risk Management", "Stakeholder Management"],
            "mentors": ["Senior Project Managers", "Program Directors", "Business Leaders"],
            "learning_path": "project-management-fundamentals"
        })

    # Marketing defaults
    if any(word in interest_text + skills_text for word in ['marketing', 'social', 'content', 'brand', 'communication']):
        defaults.append({
            "name": "Digital Marketing Specialist",
            "match": 82,
            "summary": "Develop and execute marketing strategies that reach target audiences through digital channels. This creative career combines strategy with measurable results.",
            "skills": ["Social Media Marketing", "Content Creation", "SEO", "Analytics", "Campaign Management"],
            "mentors": ["Marketing Directors", "Brand Managers", "Digital Strategists"],
            "learning_path": "digital-marketing-fundamentals"
        })

    # Healthcare defaults
    if any(word in interest_text + skills_text + goal_text for word in ['health', 'medical', 'care', 'patient', 'wellness']):
        defaults.append({
            "name": "Healthcare Administrator",
            "match": 76,
            "summary": "Manage healthcare facilities and ensure quality patient care delivery. This career combines business acumen with a passion for healthcare improvement.",
            "skills": ["Healthcare Regulations", "Patient Care Coordination", "Budget Management", "Quality Assurance", "Team Leadership"],
            "mentors": ["Healthcare Executives", "Clinical Directors", "Operations Managers"],
            "learning_path": "healthcare-administration-basics"
        })

    # Education defaults
    if any(word in interest_text + skills_text + goal_text for word in ['teaching', 'education', 'learning', 'training', 'mentoring']):
        defaults.append({
            "name": "Corporate Trainer",
            "match": 79,
            "summary": "Design and deliver training programs that develop employee skills and organizational capabilities. This career focuses on adult learning and professional development.",
            "skills": ["Training Design", "Public Speaking", "Learning Assessment", "Curriculum Development", "Adult Learning Theory"],
            "mentors": ["Learning and Development Directors", "Senior Trainers", "HR Managers"],
            "learning_path": "corporate-training-fundamentals"
        })

    # Fill remaining slots with general defaults if needed
    general_defaults = [
        {
            "name": "Business Analyst",
            "match": 73,
            "summary": "Bridge the gap between business needs and technical solutions by analyzing requirements and recommending improvements.",
            "skills": ["Requirements Analysis", "Process Mapping", "Communication", "Problem Solving", "Documentation"],
            "mentors": ["Senior Business Analysts", "Product Owners", "Solutions Architects"],
            "learning_path": "business-analysis-fundamentals"
        },
        {
            "name": "Operations Coordinator",
            "match": 70,
            "summary": "Ensure smooth daily operations and coordinate various business functions to achieve organizational goals.",
            "skills": ["Process Optimization", "Vendor Management", "Communication", "Organization", "Problem Solving"],
            "mentors": ["Operations Managers", "Process Improvement Specialists", "Department Heads"],
            "learning_path": "operations-management-basics"
        },
        {
            "name": "Customer Success Manager",
            "match": 77,
            "summary": "Build long-term relationships with customers and ensure they achieve their desired outcomes with your products or services.",
            "skills": ["Customer Relationship Management", "Communication", "Problem Solving", "Product Knowledge", "Retention Strategies"],
            "mentors": ["Customer Success Directors", "Account Managers", "Sales Leaders"],
            "learning_path": "customer-success-fundamentals"
        }
    ]

    # Fill up to 3 recommendations
    while len(defaults) < 3:
        for general in general_defaults:
            if general not in defaults:
                defaults.append(general)
                break

    return defaults[:3]

def get_career_roadmap(career_name, user_progress):
    """
    Generate a personalized roadmap for a selected career path.
    
    Args:
        career_name (str): The selected career path
        user_progress (int): Current progress percentage
    
    Returns:
        dict: Career roadmap with milestones and resources
    """
    
    prompt = f"""
    Create a detailed 5-stage roadmap for the career: {career_name}
    
    Current user progress: {user_progress}%
    
    Provide:
    1. 5 milestones with titles and descriptions
    2. Recommended mentors for each stage
    3. Learning resources for each stage
    4. Estimated timeframes for each stage
    
    Format the response as JSON:
    {{
        "career": "{career_name}",
        "milestones": [
            {{
                "title": "Milestone Title",
                "description": "Detailed description",
                "timeframe": "Estimated duration"
            }}
        ],
        "mentors": ["Mentor Type 1", "Mentor Type 2"],
        "resources": ["Resource 1", "Resource 2"]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        roadmap = json.loads(response.text)
        return roadmap
    except Exception as e:
        print(f"Error generating career roadmap: {e}")
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

def generate_personalized_learning_path(career_name, career_summary, user_profile, match_percentage):
    """
    Generate a comprehensive, personalized learning path for a specific career choice.
    This function creates a detailed roadmap when a seeker clicks "View Details" on a career.
    
    Args:
        career_name (str): The selected career path name
        career_summary (str): Summary of the career
        user_profile (dict): User's comprehensive profile data
        match_percentage (int): How well this career matches the user
    
    Returns:
        dict: Comprehensive learning path with phases, courses, projects, certifications
    """
    
    # Build profile context for personalization
    profile_context = build_profile_context(user_profile) if user_profile else ""
    
    # Extract key information for better personalization
    user_skills = user_profile.get('skills', []) if user_profile else []
    user_education = user_profile.get('education', []) if user_profile else []
    user_experience = user_profile.get('experience', []) if user_profile else []
    learning_style = user_profile.get('basic_info', {}).get('learning_style', 'mixed') if user_profile else 'mixed'
    
    prompt = f"""
You are an expert career development advisor creating a PERSONALIZED LEARNING PATH for a student who has chosen to pursue a career as a {career_name}.

CAREER DETAILS:
- Career: {career_name}
- Summary: {career_summary}
- Match with User: {match_percentage}%

USER PROFILE:
{profile_context}

Current Skills: {', '.join(user_skills[:10]) if user_skills else 'Beginner level'}
Learning Style: {learning_style}

TASK: Create a comprehensive, step-by-step learning path that will help this specific user transition into the {career_name} role. 

The learning path should be:
1. PERSONALIZED to their current skill level and background
2. STRUCTURED in clear phases from beginner to job-ready
3. ACTIONABLE with specific courses, projects, and certifications
4. REALISTIC with estimated timelines

Return ONLY a valid JSON object (no markdown, no extra text) with this EXACT structure:

{{
  "career_name": "{career_name}",
  "overview": "A 2-3 sentence personalized overview explaining why this path suits them",
  "total_duration": "Estimated total time (e.g., '6-12 months')",
  "phases": [
    {{
      "phase_number": 1,
      "title": "Phase name",
      "duration": "Time needed",
      "description": "What they'll achieve in this phase",
      "skills_to_learn": ["Skill 1", "Skill 2", "Skill 3"],
      "courses": [
        {{
          "name": "Specific course name",
          "provider": "Platform (e.g., Coursera, Udemy, YouTube)",
          "duration": "Course length",
          "difficulty": "Beginner/Intermediate/Advanced",
          "why_relevant": "How this helps their career goal"
        }}
      ],
      "projects": [
        {{
          "title": "Specific project name",
          "description": "What they'll build",
          "skills_practiced": ["Skill 1", "Skill 2"],
          "estimated_time": "Time to complete"
        }}
      ],
      "milestones": ["Concrete achievement 1", "Concrete achievement 2"]
    }}
  ],
  "certifications": [
    {{
      "name": "Certification name",
      "provider": "Issuing organization",
      "importance": "Why this matters for {career_name}",
      "estimated_cost": "Cost range or 'Free'",
      "preparation_time": "Time to prepare"
    }}
  ],
  "key_resources": [
    {{
      "type": "Book/Blog/Community/Tool",
      "name": "Resource name",
      "description": "What it offers",
      "url": "example.com (if known) or 'Search online'"
    }}
  ],
  "networking_tips": [
    "Specific actionable networking advice 1",
    "Specific actionable networking advice 2",
    "Specific actionable networking advice 3"
  ],
  "success_metrics": [
    "How to measure progress 1",
    "How to measure progress 2",
    "How to measure progress 3"
  ],
  "next_steps": "What to do after completing this learning path"
}}

IMPORTANT REQUIREMENTS:
- Include 3-5 phases progressing from fundamentals to job-ready
- Each phase should have 2-4 courses and 2-3 projects
- Recommend 2-4 relevant certifications
- All content must be realistic and available
- Personalize based on their current level
- Be specific with course names and providers
"""

    try:
        print(f"🎓 Generating personalized learning path for: {career_name}")
        print(f"📊 Match percentage: {match_percentage}%")
        print(f"👤 User has {len(user_skills)} skills in profile")
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.5,
                top_p=0.9,
                max_output_tokens=4096,  # Increased for comprehensive content
                candidate_count=1
            )
        )
        
        # Handle blocked/empty responses
        if not getattr(response, 'candidates', None):
            print("⚠️ No candidates in response; using default learning path")
            return generate_default_learning_path(career_name, career_summary)
        
        cand = response.candidates[0]
        parts = getattr(cand, 'content', None).parts if getattr(cand, 'content', None) else []
        if not parts:
            print("⚠️ Response had no content parts")
            return generate_default_learning_path(career_name, career_summary)
        
        # Extract text
        text_chunks = []
        for p in parts:
            t = getattr(p, 'text', None)
            if isinstance(t, str):
                text_chunks.append(t)
        response_text = ("\n".join(text_chunks)).strip()
        
        print(f"🤖 AI Response length: {len(response_text)} characters")
        
        # Strip markdown fences
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        elif response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        # Parse JSON
        try:
            learning_path = json.loads(response_text)
            print(f"✅ Learning path generated successfully with {len(learning_path.get('phases', []))} phases")
            return learning_path
        except json.JSONDecodeError as json_error:
            print(f"❌ JSON parsing failed: {json_error}")
            print(f"Response preview: {response_text[:300]}...")
            return generate_default_learning_path(career_name, career_summary)
            
    except Exception as e:
        print(f"❌ Error generating learning path: {e}")
        import traceback
        traceback.print_exc()
        return generate_default_learning_path(career_name, career_summary)

def generate_default_learning_path(career_name, career_summary):
    """Generate a default learning path structure when AI generation fails"""
    return {
        "career_name": career_name,
        "overview": f"This learning path will guide you step-by-step to become a successful {career_name}. {career_summary}",
        "total_duration": "6-12 months",
        "phases": [
            {
                "phase_number": 1,
                "title": "Foundation & Fundamentals",
                "duration": "2-3 months",
                "description": "Build a strong foundation in the core concepts and skills required for this career",
                "skills_to_learn": ["Core Concept 1", "Core Concept 2", "Core Concept 3"],
                "courses": [
                    {
                        "name": f"Introduction to {career_name}",
                        "provider": "Coursera / Udemy",
                        "duration": "4-6 weeks",
                        "difficulty": "Beginner",
                        "why_relevant": "Establishes foundational understanding"
                    },
                    {
                        "name": "Essential Skills Development",
                        "provider": "edX / LinkedIn Learning",
                        "duration": "3-4 weeks",
                        "difficulty": "Beginner",
                        "why_relevant": "Builds practical skills"
                    }
                ],
                "projects": [
                    {
                        "title": "Beginner Project",
                        "description": "Apply fundamental concepts in a real project",
                        "skills_practiced": ["Skill 1", "Skill 2"],
                        "estimated_time": "2-3 weeks"
                    }
                ],
                "milestones": [
                    "Complete foundational courses",
                    "Build first project",
                    "Understand core concepts"
                ]
            },
            {
                "phase_number": 2,
                "title": "Skill Development & Practice",
                "duration": "2-4 months",
                "description": "Develop intermediate skills through hands-on practice and real-world projects",
                "skills_to_learn": ["Intermediate Skill 1", "Intermediate Skill 2", "Tool Proficiency"],
                "courses": [
                    {
                        "name": f"Advanced {career_name} Techniques",
                        "provider": "Udacity / Pluralsight",
                        "duration": "6-8 weeks",
                        "difficulty": "Intermediate",
                        "why_relevant": "Deepens practical knowledge"
                    }
                ],
                "projects": [
                    {
                        "title": "Intermediate Portfolio Project",
                        "description": "Build a comprehensive project for your portfolio",
                        "skills_practiced": ["Multiple Skills", "Problem Solving"],
                        "estimated_time": "4-6 weeks"
                    },
                    {
                        "title": "Collaborative Project",
                        "description": "Work with others on a team project",
                        "skills_practiced": ["Teamwork", "Version Control"],
                        "estimated_time": "3-4 weeks"
                    }
                ],
                "milestones": [
                    "Complete intermediate courses",
                    "Build portfolio projects",
                    "Gain practical experience"
                ]
            },
            {
                "phase_number": 3,
                "title": "Specialization & Career Prep",
                "duration": "2-3 months",
                "description": "Specialize in key areas and prepare for job opportunities",
                "skills_to_learn": ["Specialized Skill 1", "Professional Skill 2", "Industry Tools"],
                "courses": [
                    {
                        "name": "Professional Development",
                        "provider": "Industry Leaders",
                        "duration": "4-6 weeks",
                        "difficulty": "Advanced",
                        "why_relevant": "Prepares you for real-world work"
                    }
                ],
                "projects": [
                    {
                        "title": "Capstone Project",
                        "description": "Build a professional-grade project showcasing all your skills",
                        "skills_practiced": ["All Learned Skills"],
                        "estimated_time": "6-8 weeks"
                    }
                ],
                "milestones": [
                    "Complete specialization",
                    "Build impressive portfolio",
                    "Prepare for interviews"
                ]
            }
        ],
        "certifications": [
            {
                "name": f"Professional {career_name} Certificate",
                "provider": "Industry Association",
                "importance": "Validates your skills to employers",
                "estimated_cost": "$100-$300",
                "preparation_time": "2-4 weeks"
            },
            {
                "name": "Foundational Skills Certificate",
                "provider": "Online Learning Platform",
                "importance": "Demonstrates core competency",
                "estimated_cost": "Free-$100",
                "preparation_time": "1-2 weeks"
            }
        ],
        "key_resources": [
            {
                "type": "Community",
                "name": f"{career_name} Community Forum",
                "description": "Connect with other learners and professionals",
                "url": "Search online for relevant communities"
            },
            {
                "type": "Book",
                "name": f"The Complete Guide to {career_name}",
                "description": "Comprehensive reference book",
                "url": "Available on Amazon/Bookstores"
            },
            {
                "type": "Blog",
                "name": "Industry Leaders' Blogs",
                "description": "Stay updated with latest trends",
                "url": "Search for top blogs in the field"
            }
        ],
        "networking_tips": [
            "Join professional associations and online communities",
            "Attend industry meetups and conferences",
            "Connect with professionals on LinkedIn",
            "Participate in online forums and discussions",
            "Seek mentorship from experienced professionals"
        ],
        "success_metrics": [
            "Complete all phase projects and add to portfolio",
            "Earn at least one relevant certification",
            "Build a network of 20+ industry professionals",
            "Contribute to open-source or community projects",
            "Successfully complete technical interviews"
        ],
        "next_steps": "Start applying for entry-level positions, continue building projects, and keep learning new skills in the field."
    }