from flask import Blueprint, render_template, request, redirect, url_for, g, flash, current_app
from werkzeug.utils import secure_filename
import os
from models import db, User, Education, Experience, Skill, Certification

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@profile_bp.route('/upload-images', methods=['POST'])
def upload_images():
    if not g.user:
        return redirect(url_for('auth.signin'))

    if 'banner_image' in request.files:
        file = request.files['banner_image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            g.user.banner_url = url_for('static', filename='uploads/' + filename)

    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            g.user.profile_pic_url = url_for('static', filename='uploads/' + filename)
    
    db.session.commit()
    return redirect(url_for('profile.view_profile', username=g.user.username))


@profile_bp.route('/<username>')
def view_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('profile/profile_view.html', user=user)

@profile_bp.route('/edit-about', methods=['POST'])
def edit_about():
    if not g.user:
        return redirect(url_for('auth.signin'))
    
    new_about_text = request.form.get('about_text')
    g.user.about = new_about_text
    db.session.commit()
    return redirect(url_for('profile.view_profile', username=g.user.username))

@profile_bp.route('/add-education', methods=['POST'])
def add_education():
    if not g.user:
        return redirect(url_for('auth.signin'))

    new_edu = Education(
        school=request.form.get('school'),
        degree=request.form.get('degree'),
        dates=request.form.get('dates'),
        user_id=g.user.id
    )
    db.session.add(new_edu)
    db.session.commit()
    return redirect(url_for('profile.view_profile', username=g.user.username))

@profile_bp.route('/edit-education/<int:edu_id>', methods=['POST'])
def edit_education(edu_id):
    if not g.user:
        return redirect(url_for('auth.signin'))
    
    edu = Education.query.get_or_404(edu_id)
    if edu.user_id != g.user.id:
        flash("You are not authorized to edit this education.", "danger")
        return redirect(url_for('profile.view_profile', username=g.user.username))

    edu.school = request.form.get('school', edu.school)
    edu.degree = request.form.get('degree', edu.degree)
    edu.dates = request.form.get('dates', edu.dates)
    db.session.commit()
    return redirect(url_for('profile.view_profile', username=g.user.username))

@profile_bp.route('/add-experience', methods=['POST'])
def add_experience():
    if not g.user:
        return redirect(url_for('auth.signin'))

    new_exp = Experience(
        title=request.form.get('title'),
        company=request.form.get('company'),
        dates=f"{request.form.get('start_date')} - {request.form.get('end_date')}",
        location=request.form.get('location'),
        description=request.form.get('description'),
        user_id=g.user.id
    )
    db.session.add(new_exp)
    db.session.commit()
    return redirect(url_for('profile.view_profile', username=g.user.username))

@profile_bp.route('/edit-experience/<int:exp_id>', methods=['POST'])
def edit_experience(exp_id):
    if not g.user:
        return redirect(url_for('auth.signin'))
        
    exp = Experience.query.get_or_404(exp_id)
    if exp.user_id != g.user.id:
        flash("You are not authorized to edit this experience.", "danger")
        return redirect(url_for('profile.view_profile', username=g.user.username))

    exp.title = request.form.get('title', exp.title)
    exp.company = request.form.get('company', exp.company)
    exp.location = request.form.get('location', exp.location)
    exp.dates = request.form.get('dates', exp.dates)
    exp.description = request.form.get('description', exp.description)
    db.session.commit()
    return redirect(url_for('profile.view_profile', username=g.user.username))

@profile_bp.route('/add-skill', methods=['POST'])
def add_skill():
    if not g.user:
        return redirect(url_for('auth.signin'))

    skill_name = request.form.get('skill_name')
    if skill_name:
        # Check if skill already exists for the user
        existing_skill = Skill.query.filter_by(name=skill_name, user_id=g.user.id).first()
        if not existing_skill:
            new_skill = Skill(name=skill_name, user_id=g.user.id)
            db.session.add(new_skill)
            db.session.commit()
    return redirect(url_for('profile.view_profile', username=g.user.username))

@profile_bp.route('/add-certification', methods=['POST'])
def add_certification():
    if not g.user:
        return redirect(url_for('auth.signin'))

    new_cert = Certification(
        name=request.form.get('name'),
        issuing_organization=request.form.get('issuing_organization'),
        issue_date=request.form.get('issue_date'),
        credential_url=request.form.get('credential_url'),
        user_id=g.user.id
    )
    db.session.add(new_cert)
    db.session.commit()
    return redirect(url_for('profile.view_profile', username=g.user.username))

@profile_bp.route('/edit-certification/<int:cert_id>', methods=['POST'])
def edit_certification(cert_id):
    if not g.user:
        return redirect(url_for('auth.signin'))

    cert = Certification.query.get_or_404(cert_id)
    if cert.user_id != g.user.id:
        flash("You are not authorized to edit this certification.", "danger")
        return redirect(url_for('profile.view_profile', username=g.user.username))

    cert.name = request.form.get('name', cert.name)
    cert.issuing_organization = request.form.get('issuing_organization', cert.issuing_organization)
    cert.issue_date = request.form.get('issue_date', cert.issue_date)
    cert.credential_url = request.form.get('credential_url', cert.credential_url)
    db.session.commit()
    return redirect(url_for('profile.view_profile', username=g.user.username))
