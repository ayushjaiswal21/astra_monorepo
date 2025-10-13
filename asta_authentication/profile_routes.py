from flask import Blueprint, render_template, request, redirect, url_for
import os

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

# MOCK USER DATA (Replace with your database logic)
mock_user_data = {
    "username": "ayushjaiswal",
    "name": "Ayush Jaiswal",
    "headline": "Passionate Computer Science student | Aspiring Software Engineer",
    "location": "Hyderabad, India",
    "university": "Chaitanya Bharathi Institute Of Technology",
    "about": "I'm a passionate Computer Science engineering student with a dream to revolutionize the education sector through technology. My goal is to develop innovative learning platforms that make education accessible and engaging for everyone.",
    "profile_pic_url": None, 
    "banner_url": None,
    # --- ADD THIS NEW DATA ---
    "education": [
        { 
            "id": 1, 
            "logo": "https://upload.wikimedia.org/wikipedia/en/4/43/CBIT_Logo.png", # Example logo URL
            "school": "Chaitanya Bharathi Institute Of Technology", 
            "degree": "Bachelor of Technology - BTech, Electronics and Communication Engineering", 
            "dates": "Dec 2021 - Aug 2025", 
            "grade": "7.8",
            "skills": ["Microsoft Word", "User Interface Design", "Python"]
        },
        { 
            "id": 2, 
            "logo": None, # No logo available
            "school": "Pragathi Girls junior college", 
            "degree": "intermediate, MPC, Maths Physics Chemistry", 
            "dates": "Jun 2019 - May 2021", 
            "grade": "83.3",
            "skills": []
        }
    ],
    "skills": ["Wix studio", "Figma (Software)", "Python", "JavaScript", "HTML", "CSS", "Project Management"],
    "experience": [
        {
            "id": 1,
            "logo": "https://placehold.co/100x100/E2E8F0/4A5568?text=TS",
            "title": "Software Engineer Intern",
            "company": "Tech Solutions Inc.",
            "dates": "Jun 2024 - Aug 2024",
            "location": "San Francisco, CA",
            "description": "Worked on the core features of the company's flagship product."
        }
    ],
    "certifications": [
        {
            "id": 1,
            "name": "Foundational Python for Data Science",
            "issuing_organization": "IBM",
            "issue_date": "Issued Jun 2023",
            "credential_url": "#",
            "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/51/IBM_logo.svg/1200px-IBM_logo.svg.png"
        }
    ]
}

@profile_bp.route('/<username>')
def view_profile(username):
    # Fetch user from DB based on username. Using mock data for now.
    return render_template('profile/profile_view.html', user=mock_user_data)

@profile_bp.route('/upload-images', methods=['POST'])
def upload_images():
    username = "ayushjaiswal" # In real app, get current user
    if 'banner_image' in request.files and request.files['banner_image'].filename != '':
        print(f"Banner image received: {request.files['banner_image'].filename}")
        # Add logic to save the file and update user's banner_url in DB
    if 'profile_picture' in request.files and request.files['profile_picture'].filename != '':
        print(f"Profile picture received: {request.files['profile_picture'].filename}")
        # Add logic to save the file and update user's profile_pic_url in DB
    return redirect(url_for('profile.view_profile', username=username))

@profile_bp.route('/edit-about', methods=['POST'])
def edit_about():
    username = "ayushjaiswal"
    new_about_text = request.form.get('about_text')
    mock_user_data['about'] = new_about_text # Update mock data
    # Add logic to update the user's 'about' field in the database
    return redirect(url_for('profile.view_profile', username=username))

# --- Placeholder routes for modal forms ---

@profile_bp.route('/add-education', methods=['POST'])
def add_education():
    username = "ayushjaiswal"
    new_edu = {
        "id": len(mock_user_data['education']) + 1, # Simple ID generation
        "logo": None,
        "school": request.form.get('school'),
        "degree": request.form.get('degree'),
        "dates": request.form.get('dates'),
        "grade": "",
        "skills": []
    }
    mock_user_data['education'].append(new_edu)
    return redirect(url_for('profile.view_profile', username=username))

@profile_bp.route('/edit-education/<int:edu_id>', methods=['POST'])
def edit_education(edu_id):
    username = "ayushjaiswal"
    for edu in mock_user_data['education']:
        if edu['id'] == edu_id:
            edu['school'] = request.form.get('school', edu['school'])
            edu['degree'] = request.form.get('degree', edu['degree'])
            edu['dates'] = request.form.get('dates', edu['dates'])
            break
    return redirect(url_for('profile.view_profile', username=username))

@profile_bp.route('/add-experience', methods=['POST'])
def add_experience():
    username = "ayushjaiswal"
    new_exp = {
        "id": len(mock_user_data['experience']) + 1,
        "logo": None,
        "title": request.form.get('title'),
        "company": request.form.get('company'),
        "dates": f"{request.form.get('start_date')} - {request.form.get('end_date')}",
        "location": request.form.get('location'),
        "description": request.form.get('description')
    }
    mock_user_data['experience'].append(new_exp)
    return redirect(url_for('profile.view_profile', username=username))

@profile_bp.route('/edit-experience/<int:exp_id>', methods=['POST'])
def edit_experience(exp_id):
    username = "ayushjaiswal"
    for exp in mock_user_data['experience']:
        if exp['id'] == exp_id:
            exp['title'] = request.form.get('title', exp['title'])
            exp['company'] = request.form.get('company', exp['company'])
            exp['location'] = request.form.get('location', exp['location'])
            exp['dates'] = request.form.get('dates', exp['dates'])
            exp['description'] = request.form.get('description', exp['description'])
            break
    return redirect(url_for('profile.view_profile', username=username))

@profile_bp.route('/add-skill', methods=['POST'])
def add_skill():
    username = "ayushjaiswal"
    new_skill = request.form.get('skill_name')
    if new_skill and new_skill not in mock_user_data['skills']:
        mock_user_data['skills'].append(new_skill)
    return redirect(url_for('profile.view_profile', username=username))

@profile_bp.route('/edit-skill/<int:skill_index>', methods=['POST'])
def edit_skill(skill_index):
    username = "ayushjaiswal"
    # Note: Using index is fragile. A real app should use a unique ID.
    if 0 < skill_index <= len(mock_user_data['skills']):
        mock_user_data['skills'][skill_index - 1] = request.form.get('skill_name')
    return redirect(url_for('profile.view_profile', username=username))

@profile_bp.route('/add-certification', methods=['POST'])
def add_certification():
    username = "ayushjaiswal"
    new_cert = {
        "id": len(mock_user_data.get('certifications', [])) + 1,
        "name": request.form.get('name'),
        "issuing_organization": request.form.get('issuing_organization'),
        "issue_date": request.form.get('issue_date'),
        "credential_url": request.form.get('credential_url'),
        "logo": None # Placeholder for a logo if available
    }
    if 'certifications' not in mock_user_data:
        mock_user_data['certifications'] = []
    mock_user_data['certifications'].append(new_cert)
    return redirect(url_for('profile.view_profile', username=username))

@profile_bp.route('/edit-certification/<int:cert_id>', methods=['POST'])
def edit_certification(cert_id):
    username = "ayushjaiswal"
    for cert in mock_user_data.get('certifications', []):
        if cert['id'] == cert_id:
            cert['name'] = request.form.get('name', cert['name'])
            cert['issuing_organization'] = request.form.get('issuing_organization', cert['issuing_organization'])
            cert['issue_date'] = request.form.get('issue_date', cert['issue_date'])
            cert['credential_url'] = request.form.get('credential_url', cert['credential_url'])
            break
    return redirect(url_for('profile.view_profile', username=username))

@profile_bp.route('/network')
def network():
    # Mock data for the network page
    mock_network_data = {
        "stats": {
            "connections": 248,
            "contacts": 120,
            "groups": 15,
            "events": 3,
            "pages": 5
        },
        "invitations": [
            {
                "name": "Dr. Evelyn Reed",
                "headline": "Professor of Computer Science at Tech University",
                "mutual": 12
            },
            {
                "name": "John Carter",
                "headline": "Lead Developer at Innovate Corp",
                "mutual": 5
            }
        ],
        "suggestions": [
            {
                "id": 1,
                "name": "Jane Doe",
                "headline": "Data Scientist | AI Enthusiast",
                "profile_pic_url": "https://placehold.co/100x100/E2E8F0/4A5568?text=JD",
                "banner_url": "https://placehold.co/400x100/A0AEC0/FFFFFF?text=Banner",
                "mutual": 5
            },
            {
                "id": 2,
                "name": "Peter Jones",
                "headline": "UX/UI Designer at Creative Minds",
                "profile_pic_url": "https://placehold.co/100x100/E2E8F0/4A5568?text=PJ",
                "banner_url": "https://placehold.co/400x100/A0AEC0/FFFFFF?text=Banner",
                "mutual": 3
            },
            {
                "id": 3,
                "name": "Sam Wilson",
                "headline": "Backend Developer at Cloud Solutions",
                "profile_pic_url": "https://placehold.co/100x100/E2E8F0/4A5568?text=SW",
                "banner_url": "https://placehold.co/400x100/A0AEC0/FFFFFF?text=Banner",
                "mutual": 8
            },
            {
                "id": 4,
                "name": "Maria Garcia",
                "headline": "Product Manager at Enterprise Systems",
                "profile_pic_url": "https://placehold.co/100x100/E2E8F0/4A5568?text=MG",
                "banner_url": "https://placehold.co/400x100/A0AEC0/FFFFFF?text=Banner",
                "mutual": 2
            }
        ]
    }
    return render_template('network/network_hub.html', network=mock_network_data)