from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from werkzeug.utils import secure_filename
import os
import json
import requests
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_login import current_user
from .utils import api_login_required as login_required
from sqlalchemy import or_

try:
    from .models import db, User, Education, Experience, Skill, Certification, ProfileView, Post, CareerGPS, LearningPath
    from .main_routes import log_activity
except ImportError:
    from models import db, User, Education, Experience, Skill, Certification, ProfileView, Post, CareerGPS, LearningPath
    from main_routes import log_activity

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

# Connection Request API Endpoint
@profile_bp.route('/api/user/<int:user_id>/connect', methods=['POST'])
@login_required
def send_connection_request(user_id):
    try:
        from .models import User, Connection, db, Notification
        
        # Check if user exists
        target_user = User.query.get_or_404(user_id)
        
        # Prevent self-connection
        if current_user.id == user_id:
            return jsonify({'success': False, 'error': 'Cannot send connection request to yourself'}), 400
            
        # Check if already connected
        if current_user.is_connected(target_user):
            return jsonify({'success': False, 'error': 'You are already connected with this user'}), 400
            
        # Check if there's already a pending request
        existing_request = Connection.query.filter(
            ((Connection.requester_id == current_user.id) & (Connection.receiver_id == user_id)) |
            ((Connection.requester_id == user_id) & (Connection.receiver_id == current_user.id))
        ).first()
        
        if existing_request:
            if existing_request.status == 'pending':
                if existing_request.requester_id == current_user.id:
                    return jsonify({'success': False, 'error': 'Connection request already sent'}), 400
                else:
                    # Accept the pending request
                    existing_request.status = 'accepted'
                    db.session.commit()
                    
                    # Create notification for the requester
                    notification = Notification(
                        user_id=existing_request.requester_id,
                        payload={
                            'type': 'connection_accepted',
                            'message': f'{current_user.username} accepted your connection request',
                            'user_id': current_user.id,
                            'username': current_user.username
                        }
                    )
                    db.session.add(notification)
                    db.session.commit()
                    
                    return jsonify({
                        'success': True, 
                        'message': 'Connection request accepted',
                        'status': 'connected'
                    })
        
        # Create new connection request
        connection = Connection(
            requester_id=current_user.id,
            receiver_id=user_id,
            status='pending'
        )
        db.session.add(connection)
        
        # Create notification for the receiver
        notification = Notification(
            user_id=user_id,
            payload={
                'type': 'connection_request',
                'message': f'{current_user.username} sent you a connection request',
                'user_id': current_user.id,
                'username': current_user.username
            }
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Connection request sent',
            'status': 'request_sent'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error in send_connection_request: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

# --- API Endpoint for Profile --- 
@profile_bp.route('/', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role
    })

# --- Original Form-Based Routes ---

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@profile_bp.route('/upload-images', methods=['POST'])
@login_required
def upload_images():
    if 'banner_image' in request.files:
        file = request.files['banner_image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            current_user.banner_url = url_for('static', filename='uploads/' + filename)
            log_activity(current_user.id, 'updated_banner_image')

    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            current_user.profile_pic_url = url_for('static', filename='uploads/' + filename)
            log_activity(current_user.id, 'updated_profile_picture')
    
    db.session.commit()
    return redirect(url_for('profile.view_profile', username=current_user.username))


@profile_bp.route('/<username>')
@login_required
def view_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).all()
    if current_user.id != user.id:
        profile_view = ProfileView(viewer_id=current_user.id, viewed_id=user.id)
        db.session.add(profile_view)
        db.session.commit()
        log_activity(current_user.id, 'viewed_profile', f"viewed {user.username}'s profile")
    return render_template('profile/profile_view.html', user=user, posts=posts)

@profile_bp.route('/edit-about', methods=['POST'])
@login_required
def edit_about():
    new_about_text = request.form.get('about')
    current_user.about = new_about_text
    db.session.commit()
    log_activity(current_user.id, 'updated_about_section')
    return jsonify({'success': True, 'message': 'About section updated successfully.', 'about': new_about_text})

@profile_bp.route('/edit-basic', methods=['POST'])
@login_required
def edit_basic():
    """Update basic profile fields: name and headline"""
    name = request.form.get('name')
    headline = request.form.get('headline')
    if name is not None:
        current_user.name = name.strip() or None
    if headline is not None:
        current_user.headline = headline.strip() or None
    db.session.commit()
    log_activity(current_user.id, 'updated_basic_profile')
    return jsonify({'success': True, 'name': current_user.name, 'headline': current_user.headline})

@profile_bp.route('/add-education', methods=['POST'])
@login_required
def add_education():
    new_edu = Education(
        school=request.form.get('school'),
        degree=request.form.get('degree'),
        dates=request.form.get('dates'),
        user_id=current_user.id
    )
    db.session.add(new_edu)
    db.session.commit()
    log_activity(current_user.id, 'added_education', f'{new_edu.school}')
    return jsonify({'success': True, 'id': new_edu.id})

@profile_bp.route('/edit-education/<int:edu_id>', methods=['POST'])
@login_required
def edit_education(edu_id):
    edu = Education.query.get_or_404(edu_id)
    if edu.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'You are not authorized to edit this education.'}), 403

    edu.school = request.form.get('school', edu.school)
    edu.degree = request.form.get('degree', edu.degree)
    edu.dates = request.form.get('dates', edu.dates)
    db.session.commit()
    log_activity(current_user.id, 'edited_education', f'{edu.school}')
    return jsonify({'success': True})

@profile_bp.route('/add-experience', methods=['POST'])
@login_required
def add_experience():
    new_exp = Experience(
        title=request.form.get('title'),
        company=request.form.get('company'),
        dates=f"{request.form.get('start_date')} - {request.form.get('end_date')}",
        location=request.form.get('location'),
        description=request.form.get('description'),
        user_id=current_user.id
    )
    db.session.add(new_exp)
    db.session.commit()
    log_activity(current_user.id, 'added_experience', f'{new_exp.title} at {new_exp.company}')
    return jsonify({'success': True, 'id': new_exp.id})

@profile_bp.route('/edit-experience/<int:exp_id>', methods=['POST'])
@login_required
def edit_experience(exp_id):
    exp = Experience.query.get_or_404(exp_id)
    if exp.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'You are not authorized to edit this experience.'}), 403

    exp.title = request.form.get('title', exp.title)
    exp.company = request.form.get('company', exp.company)
    exp.location = request.form.get('location', exp.location)
    exp.dates = request.form.get('dates', exp.dates)
    exp.description = request.form.get('description', exp.description)
    db.session.commit()
    log_activity(current_user.id, 'edited_experience', f'{exp.title} at {exp.company}')
    return jsonify({'success': True})

@profile_bp.route('/delete-experience/<int:exp_id>', methods=['POST'])
@login_required
def delete_experience(exp_id):
    exp = Experience.query.get_or_404(exp_id)
    if exp.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'You are not authorized to delete this experience.'}), 403

    db.session.delete(exp)
    db.session.commit()
    log_activity(current_user.id, 'deleted_experience', f'{exp.title} at {exp.company}')
    return jsonify({'success': True})

@profile_bp.route('/add-skill', methods=['POST'])
@login_required
def add_skill():
    # Accept both 'skill_name' and 'name' from different forms
    skill_name = request.form.get('skill_name') or request.form.get('name')
    if skill_name:
        existing_skill = Skill.query.filter_by(name=skill_name, user_id=current_user.id).first()
        if not existing_skill:
            new_skill = Skill(name=skill_name, user_id=current_user.id)
            db.session.add(new_skill)
            db.session.commit()
            log_activity(current_user.id, 'added_skill', f'{new_skill.name}')
            return jsonify({'success': True, 'id': new_skill.id})
        else:
            return jsonify({'success': False, 'error': 'Skill already exists'}), 400
    return jsonify({'success': False, 'error': 'Skill name is required'}), 400

@profile_bp.route('/add-certification', methods=['POST'])
@login_required
def add_certification():
    new_cert = Certification(
        name=request.form.get('name'),
        issuing_organization=(request.form.get('issuing_organization') or request.form.get('issuer')),
        issue_date=request.form.get('issue_date'),
        credential_url=request.form.get('credential_url'),
        user_id=current_user.id
    )
    db.session.add(new_cert)
    db.session.commit()
    log_activity(current_user.id, 'added_certification', f'{new_cert.name}')
    return jsonify({'success': True, 'id': new_cert.id})

@profile_bp.route('/edit-certification/<int:cert_id>', methods=['POST'])
@login_required
def edit_certification(cert_id):
    cert = Certification.query.get_or_404(cert_id)
    if cert.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'You are not authorized to edit this certification.'}), 403
    
    def get_comprehensive_user_profile(user_id):
        """Get comprehensive user profile data for career recommendations"""
        user = User.query.get(user_id)
        if not user:
            return {}
    
        # Get all user data
        education = Education.query.filter_by(user_id=user_id).all()
        experience = Experience.query.filter_by(user_id=user_id).all()
        skills = Skill.query.filter_by(user_id=user_id).all()
        certifications = Certification.query.filter_by(user_id=user_id).all()
    
        # Format education data
        education_data = []
        for edu in education:
            education_data.append({
                "school": edu.school,
                "degree": edu.degree,
                "dates": edu.dates,
                "grade": getattr(edu, 'grade', None)
            })
    
        # Format experience data
        experience_data = []
        for exp in experience:
            experience_data.append({
                "title": exp.title,
                "company": exp.company,
                "dates": exp.dates,
                "location": exp.location,
                "description": exp.description
            })
    
        # Format skills data
        skills_data = [skill.name for skill in skills]
    
        # Format certifications data
        certifications_data = []
        for cert in certifications:
            certifications_data.append({
                "name": cert.name,
                "issuing_organization": cert.issuing_organization,
                "issue_date": cert.issue_date,
                "credential_url": cert.credential_url
            })
    
        # Get existing career GPS data if any
        career_gps = CareerGPS.query.filter_by(user_id=user_id).first()
        career_history = None
        if career_gps:
            career_history = {
                "selected_career": career_gps.selected_career,
                "progress": career_gps.progress,
                "created_at": career_gps.created_at.isoformat() if career_gps.created_at else None
            }
    
        return {
            "basic_info": {
                "name": user.name,
                "headline": user.headline,
                "location": user.location,
                "university": user.university,
                "about": user.about,
                "role": user.role
            },
            "education": education_data,
            "experience": experience_data,
            "skills": skills_data,
            "certifications": certifications_data,
            "career_history": career_history
        }

    cert.name = request.form.get('name', cert.name)
    cert.issuing_organization = (request.form.get('issuing_organization') or request.form.get('issuer') or cert.issuing_organization)
    cert.issue_date = request.form.get('issue_date', cert.issue_date)
    cert.credential_url = request.form.get('credential_url', cert.credential_url)
    db.session.commit()
    log_activity(current_user.id, 'edited_certification', f'{cert.name}')
    return jsonify({'success': True})

def get_comprehensive_user_profile(user_id):
    """Get comprehensive user profile data for career recommendations"""
    user = User.query.get(user_id)
    if not user:
        return {}

    # Get all user data
    education = Education.query.filter_by(user_id=user_id).all()
    experience = Experience.query.filter_by(user_id=user_id).all()
    skills = Skill.query.filter_by(user_id=user_id).all()
    certifications = Certification.query.filter_by(user_id=user_id).all()

    # Format education data
    education_data = []
    for edu in education:
        education_data.append({
            "school": edu.school,
            "degree": edu.degree,
            "dates": edu.dates,
            "grade": getattr(edu, 'grade', None)
        })

    # Format experience data
    experience_data = []
    for exp in experience:
        experience_data.append({
            "title": exp.title,
            "company": exp.company,
            "dates": exp.dates,
            "location": exp.location,
            "description": exp.description
        })

    # Format skills data
    skills_data = [skill.name for skill in skills]

    # Format certifications data
    certifications_data = []
    for cert in certifications:
        certifications_data.append({
            "name": cert.name,
            "issuing_organization": cert.issuing_organization,
            "issue_date": cert.issue_date,
            "credential_url": cert.credential_url
        })

    # Get existing career GPS data if any
    career_gps = CareerGPS.query.filter_by(user_id=user_id).first()
    career_history = None
    if career_gps:
        career_history = {
            "selected_career": career_gps.selected_career,
            "progress": career_gps.progress,
            "created_at": career_gps.created_at.isoformat() if career_gps.created_at else None
        }

    return {
        "basic_info": {
            "name": user.name,
            "headline": user.headline,
            "location": user.location,
            "university": user.university,
            "about": user.about,
            "role": user.role
        },
        "education": education_data,
        "experience": experience_data,
        "skills": skills_data,
        "certifications": certifications_data,
        "career_history": career_history
    }

# Career GPS Routes
@profile_bp.route('/career-gps')
@login_required
def career_gps():
    # Check if user already has a career GPS
    gps_data = CareerGPS.query.filter_by(user_id=current_user.id).first()
    return render_template('profile/career_gps.html', gps_data=gps_data)

@profile_bp.route('/career-gps/start', methods=['GET', 'POST'])
@login_required
def start_career_gps():
    if request.method == 'POST':
        # Save quiz responses
        gps_data = CareerGPS(
            user_id=current_user.id,
            interests=request.form.get('interests', '[]'),
            skills=request.form.get('skills', '[]'),
            goal=request.form.get('goal'),
            motivation=request.form.get('motivation'),
            learning_style=request.form.get('learning_style')
        )
        db.session.add(gps_data)
        db.session.commit()
        
        # Redirect to AI processing endpoint
        return redirect(url_for('profile.process_career_gps', gps_id=gps_data.id))
    
    return render_template('profile/career_gps_quiz.html')

@profile_bp.route('/career-gps/process/<int:gps_id>')
@login_required
def process_career_gps(gps_id):
    gps_data = CareerGPS.query.get_or_404(gps_id)
    if gps_data.user_id != current_user.id:
        flash("You are not authorized to access this career GPS data.", "danger")
        return redirect(url_for('profile.view_profile', username=current_user.username))
    
    # Parse user data
    try:
        interests = json.loads(gps_data.interests) if gps_data.interests else []
    except json.JSONDecodeError:
        interests = []
    try:
        skills = json.loads(gps_data.skills) if gps_data.skills else []
    except json.JSONDecodeError:
        skills = []
    
    # Get comprehensive user profile data for better recommendations
    user_profile_data = get_comprehensive_user_profile(current_user.id)
    
    # Generate career recommendations by calling the AI Guru service
    try:
        import requests
        
        # Debug: Print the data being passed to the service
        print(f"DEBUG: interests={interests}")
        print(f"DEBUG: skills={skills}")
        print(f"DEBUG: goal={gps_data.goal}")
        print(f"DEBUG: motivation={gps_data.motivation}")
        print(f"DEBUG: learning_style={gps_data.learning_style}")
        print(f"DEBUG: user_profile_data keys={user_profile_data.keys() if user_profile_data else None}")

        # Call the AI Guru API for career recommendations
        ai_guru_url = "http://localhost:8001/career-gps/recommendations"
        print(f"🚀 Calling AI Guru service at {ai_guru_url}")
        
        payload = {
            "interests": interests,
            "skills": skills,
            "goal": gps_data.goal or "",
            "motivation": gps_data.motivation or "",
            "learning_style": gps_data.learning_style or "",
            "user_profile": user_profile_data
        }
        
        response = requests.post(ai_guru_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            top_careers = result.get('recommendations', [])
            print(f"✅ Received {len(top_careers)} recommendations from AI Guru")
            print(f"DEBUG: top_careers={top_careers}")
        else:
            print(f"❌ AI Guru service returned status {response.status_code}: {response.text}")
            raise Exception(f"AI Guru service error: {response.status_code}")
        
        # Ensure we have at least 3 recommendations
        if len(top_careers) < 3:
            print(f"⚠️ Only received {len(top_careers)} recommendations, filling with defaults")
            top_careers = get_default_career_recommendations()[:3]
        
        gps_data.top_careers = json.dumps(top_careers)
        db.session.commit()
    except requests.exceptions.ConnectionError as e:
        # AI Guru service is not running
        print(f"❌ Cannot connect to AI Guru service: {e}")
        print("⚠️ Make sure the AI Guru service is running on http://localhost:8001")
        print("🔄 Using fallback recommendations")
        top_careers = get_default_career_recommendations()
        gps_data.top_careers = json.dumps(top_careers)
        db.session.commit()
    except requests.exceptions.Timeout as e:
        # AI Guru service timed out
        print(f"❌ AI Guru service timeout: {e}")
        print("🔄 Using fallback recommendations")
        top_careers = get_default_career_recommendations()
        gps_data.top_careers = json.dumps(top_careers)
        db.session.commit()
    except Exception as e:
        # Fallback to default recommendations if anything fails
        print(f"❌ Error generating career recommendations: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        print("🔄 Using fallback recommendations")
        top_careers = get_default_career_recommendations()
        gps_data.top_careers = json.dumps(top_careers)
        db.session.commit()
    
    return render_template('profile/career_gps_results.html', gps_data=gps_data, top_careers=top_careers)

def get_default_career_recommendations():
    """Fallback function to provide default career recommendations"""
    return [
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

@profile_bp.route('/career-gps/select/<int:gps_id>/<int:career_index>')
@login_required
def select_career(gps_id, career_index):
    gps_data = CareerGPS.query.get_or_404(gps_id)
    if gps_data.user_id != current_user.id:
        flash("You are not authorized to access this career GPS data.", "danger")
        return redirect(url_for('profile.view_profile', username=current_user.username))
    
    import json
    top_careers = json.loads(gps_data.top_careers)
    if 0 <= career_index < len(top_careers):
        selected_career = top_careers[career_index]
        gps_data.selected_career = selected_career['name']
        gps_data.progress = 10  # Initial progress
        db.session.commit()
    
    return redirect(url_for('profile.view_profile', username=current_user.username))

@profile_bp.route('/generate-learning-path/<int:career_index>')
@login_required
def generate_learning_path(career_index):
    """
    Generate and save a personalized learning path for a selected career
    This is called when seeker clicks "View Details" on a career recommendation
    """
    # Get the user's career GPS data
    gps_data = CareerGPS.query.filter_by(user_id=current_user.id).order_by(CareerGPS.created_at.desc()).first()
    
    if not gps_data or not gps_data.top_careers:
        flash("Please complete the Career GPS quiz first.", "warning")
        return redirect(url_for('profile.career_gps'))
    
    import json
    try:
        top_careers = json.loads(gps_data.top_careers)
        if career_index < 0 or career_index >= len(top_careers):
            flash("Invalid career selection.", "danger")
            return redirect(url_for('profile.career_gps'))
        
        selected_career = top_careers[career_index]
        career_name = selected_career['name']
        career_summary = selected_career.get('summary', '')
        match_percentage = selected_career.get('match', 75)
        
        print(f"🎓 Generating learning path for {current_user.username}: {career_name}")
        
        # Check if learning path already exists for this career
        existing_path = LearningPath.query.filter_by(
            user_id=current_user.id,
            career_name=career_name
        ).first()
        
        if existing_path:
            print(f"✅ Found existing learning path (ID: {existing_path.id})")
            flash(f"Loading your learning path for {career_name}!", "success")
            return redirect(url_for('profile.view_learning_path', path_id=existing_path.id))
        
        # Get comprehensive user profile
        user_profile_data = get_comprehensive_user_profile(current_user.id)
        
        # Call AI Guru service to generate learning path
        try:
            import requests
            
            ai_guru_url = "http://localhost:8001/career-gps/learning-path"
            print(f"🚀 Calling AI Guru service at {ai_guru_url}")
            
            payload = {
                "career_name": career_name,
                "career_summary": career_summary,
                "match_percentage": match_percentage,
                "user_profile": user_profile_data
            }
            
            response = requests.post(ai_guru_url, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                learning_path_data = result.get('learning_path', {})
                print(f"✅ Received learning path with {len(learning_path_data.get('phases', []))} phases")
            else:
                print(f"❌ AI Guru service returned status {response.status_code}")
                raise Exception(f"AI Guru service error: {response.status_code}")
            
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to AI Guru service - using default path")
            flash("Using default learning path template. AI Guru service is unavailable.", "warning")
            learning_path_data = create_default_learning_path_structure(career_name, career_summary)
        except Exception as e:
            print(f"❌ Error calling AI Guru: {e}")
            flash("Using default learning path template.", "warning")
            learning_path_data = create_default_learning_path_structure(career_name, career_summary)
        
        # Save learning path to database
        new_learning_path = LearningPath(
            user_id=current_user.id,
            career_name=career_name,
            career_summary=career_summary,
            match_percentage=match_percentage,
            learning_path_data=json.dumps(learning_path_data),
            progress=0,
            completed_items=json.dumps([]),
            is_active=True
        )
        
        # Deactivate other learning paths for this user
        LearningPath.query.filter_by(user_id=current_user.id, is_active=True).update({'is_active': False})
        
        db.session.add(new_learning_path)
        db.session.commit()
        
        print(f"✅ Learning path saved to database (ID: {new_learning_path.id})")
        flash(f"Your personalized learning path for {career_name} has been generated!", "success")
        return redirect(url_for('profile.view_learning_path', path_id=new_learning_path.id))
        
    except Exception as e:
        print(f"❌ Error generating learning path: {e}")
        import traceback
        traceback.print_exc()
        flash("Failed to generate learning path. Please try again.", "danger")
        return redirect(url_for('profile.career_gps'))

@profile_bp.route('/learning-path/<int:path_id>')
@login_required
def view_learning_path(path_id):
    """
    Display a personalized learning path
    """
    learning_path = LearningPath.query.get_or_404(path_id)
    
    # Security check
    if learning_path.user_id != current_user.id:
        flash("You are not authorized to view this learning path.", "danger")
        return redirect(url_for('profile.view_profile', username=current_user.username))
    
    # Parse the learning path data
    import json
    try:
        path_data = json.loads(learning_path.learning_path_data)
        completed_items = json.loads(learning_path.completed_items) if learning_path.completed_items else []
    except json.JSONDecodeError:
        flash("Error loading learning path data.", "danger")
        return redirect(url_for('profile.career_gps'))
    
    return render_template('profile/learning_path.html', 
                         learning_path=learning_path,
                         path_data=path_data,
                         completed_items=completed_items)

@profile_bp.route('/learning-paths')
@login_required
def my_learning_paths():
    """
    View all learning paths for the current user
    """
    learning_paths = LearningPath.query.filter_by(user_id=current_user.id).order_by(LearningPath.created_at.desc()).all()
    return render_template('profile/my_learning_paths.html', learning_paths=learning_paths)

def create_default_learning_path_structure(career_name, career_summary):
    """Create a default learning path structure when AI service is unavailable"""
    return {
        "career_name": career_name,
        "overview": f"This is your personalized learning path to become a {career_name}. {career_summary}",
        "total_duration": "6-12 months",
        "phases": [
            {
                "phase_number": 1,
                "title": "Foundation Building",
                "duration": "2-3 months",
                "description": "Build strong fundamentals",
                "skills_to_learn": ["Core Skills", "Basic Tools", "Fundamentals"],
                "courses": [
                    {
                        "name": f"Introduction to {career_name}",
                        "provider": "Online Learning Platform",
                        "duration": "4-6 weeks",
                        "difficulty": "Beginner",
                        "why_relevant": "Establishes foundation"
                    }
                ],
                "projects": [
                    {
                        "title": "Beginner Project",
                        "description": "Apply what you learned",
                        "skills_practiced": ["Skills"],
                        "estimated_time": "2 weeks"
                    }
                ],
                "milestones": ["Complete courses", "Build first project"]
            }
        ],
        "certifications": [
            {
                "name": f"{career_name} Certificate",
                "provider": "Industry Standard",
                "importance": "Industry recognized",
                "estimated_cost": "$100-$300",
                "preparation_time": "2-4 weeks"
            }
        ],
        "key_resources": [],
        "networking_tips": ["Join communities", "Attend meetups"],
        "success_metrics": ["Build portfolio", "Complete projects"],
        "next_steps": "Continue learning and applying for opportunities"
    }
