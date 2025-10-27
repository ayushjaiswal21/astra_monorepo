from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
import os
try:
    from .models import db, User, Education, Experience, Skill, Certification, ProfileView
    from .main_routes import log_activity
except ImportError:
    from models import db, User, Education, Experience, Skill, Certification, ProfileView
    from main_routes import log_activity
from flask_login import current_user, login_required

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

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
    if current_user.id != user.id:
        profile_view = ProfileView(viewer_id=current_user.id, viewed_id=user.id)
        db.session.add(profile_view)
        db.session.commit()
        log_activity(current_user.id, 'viewed_profile', f"viewed {user.username}'s profile")
    return render_template('profile/profile_view.html', user=user)

@profile_bp.route('/edit-about', methods=['POST'])
@login_required
def edit_about():
    new_about_text = request.form.get('about_text')
    current_user.about = new_about_text
    db.session.commit()
    log_activity(current_user.id, 'updated_about_section')
    return redirect(url_for('profile.view_profile', username=current_user.username))

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
    return redirect(url_for('profile.view_profile', username=current_user.username))

@profile_bp.route('/edit-education/<int:edu_id>', methods=['POST'])
@login_required
def edit_education(edu_id):
    edu = Education.query.get_or_404(edu_id)
    if edu.user_id != current_user.id:
        flash("You are not authorized to edit this education.", "danger")
        return redirect(url_for('profile.view_profile', username=current_user.username))

    edu.school = request.form.get('school', edu.school)
    edu.degree = request.form.get('degree', edu.degree)
    edu.dates = request.form.get('dates', edu.dates)
    db.session.commit()
    log_activity(current_user.id, 'edited_education', f'{edu.school}')
    return redirect(url_for('profile.view_profile', username=current_user.username))

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
    return redirect(url_for('profile.view_profile', username=current_user.username))

@profile_bp.route('/edit-experience/<int:exp_id>', methods=['POST'])
@login_required
def edit_experience(exp_id):
    exp = Experience.query.get_or_404(exp_id)
    if exp.user_id != current_user.id:
        flash("You are not authorized to edit this experience.", "danger")
        return redirect(url_for('profile.view_profile', username=current_user.username))

    exp.title = request.form.get('title', exp.title)
    exp.company = request.form.get('company', exp.company)
    exp.location = request.form.get('location', exp.location)
    exp.dates = request.form.get('dates', exp.dates)
    exp.description = request.form.get('description', exp.description)
    db.session.commit()
    log_activity(current_user.id, 'edited_experience', f'{exp.title} at {exp.company}')
    return redirect(url_for('profile.view_profile', username=current_user.username))

@profile_bp.route('/add-skill', methods=['POST'])
@login_required
def add_skill():
    skill_name = request.form.get('skill_name')
    if skill_name:
        existing_skill = Skill.query.filter_by(name=skill_name, user_id=current_user.id).first()
        if not existing_skill:
            new_skill = Skill(name=skill_name, user_id=current_user.id)
            db.session.add(new_skill)
            db.session.commit()
            log_activity(current_user.id, 'added_skill', f'{new_skill.name}')
    return redirect(url_for('profile.view_profile', username=current_user.username))

@profile_bp.route('/add-certification', methods=['POST'])
@login_required
def add_certification():
    new_cert = Certification(
        name=request.form.get('name'),
        issuing_organization=request.form.get('issuing_organization'),
        issue_date=request.form.get('issue_date'),
        credential_url=request.form.get('credential_url'),
        user_id=current_user.id
    )
    db.session.add(new_cert)
    db.session.commit()
    log_activity(current_user.id, 'added_certification', f'{new_cert.name}')
    return redirect(url_for('profile.view_profile', username=current_user.username))

@profile_bp.route('/edit-certification/<int:cert_id>', methods=['POST'])
@login_required
def edit_certification(cert_id):
    cert = Certification.query.get_or_404(cert_id)
    if cert.user_id != current_user.id:
        flash("You are not authorized to edit this certification.", "danger")
        return redirect(url_for('profile.view_profile', username=current_user.username))

    cert.name = request.form.get('name', cert.name)
    cert.issuing_organization = request.form.get('issuing_organization', cert.issuing_organization)
    cert.issue_date = request.form.get('issue_date', cert.issue_date)
    cert.credential_url = request.form.get('credential_url', cert.credential_url)
    db.session.commit()
    log_activity(current_user.id, 'edited_certification', f'{cert.name}')
    return redirect(url_for('profile.view_profile', username=current_user.username))