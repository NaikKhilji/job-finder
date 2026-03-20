import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from werkzeug.utils import secure_filename
from extensions import db
from models import User, Application, SavedJob, Job, JobAlert, Interview

user = Blueprint('user', __name__, url_prefix='/user')

ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_RESUME = {'pdf', 'doc', 'docx'}


def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set


@user.before_request
@login_required
def require_login():
    pass


@user.before_request
def require_user_role():
    if current_user.is_authenticated and current_user.role not in ['user']:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))


@user.route('/dashboard')
def dashboard():
    applications = Application.query.filter_by(user_id=current_user.id)\
        .order_by(Application.created_at.desc()).limit(5).all()
    saved_count = SavedJob.query.filter_by(user_id=current_user.id).count()
    app_count = Application.query.filter_by(user_id=current_user.id).count()
    pending = Application.query.filter_by(user_id=current_user.id, status='Pending').count()
    accepted = Application.query.filter_by(user_id=current_user.id, status='Accepted').count()
    rejected = Application.query.filter_by(user_id=current_user.id, status='Rejected').count()

    # Recommended jobs based on user skills
    recommended_jobs = []
    if current_user.skills:
        now = datetime.utcnow()
        user_skills = [s.strip().lower() for s in current_user.skills.split(',') if s.strip()]
        applied_ids = {a.job_id for a in Application.query.filter_by(user_id=current_user.id).all()}
        if user_skills:
            skill_filters = [Job.skills_required.ilike(f'%{skill}%') for skill in user_skills]
            recommended_jobs = Job.query.filter_by(is_approved=True, is_active=True)\
                .filter(or_(*skill_filters))\
                .filter(or_(Job.deadline == None, Job.deadline >= now))\
                .filter(~Job.id.in_(applied_ids) if applied_ids else True)\
                .order_by(Job.created_at.desc()).limit(6).all()

    # Upcoming interviews
    upcoming_interviews = Interview.query.join(Application)\
        .filter(Application.user_id == current_user.id)\
        .filter(Interview.status == 'Scheduled')\
        .filter(Interview.scheduled_at >= datetime.utcnow())\
        .order_by(Interview.scheduled_at.asc()).limit(3).all()

    return render_template('user/dashboard.html',
                           recent_applications=applications,
                           saved_count=saved_count,
                           app_count=app_count,
                           pending=pending,
                           accepted=accepted,
                           rejected=rejected,
                           recommended_jobs=recommended_jobs,
                           upcoming_interviews=upcoming_interviews)


@user.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        bio = request.form.get('bio', '').strip()
        skills = request.form.get('skills', '').strip()
        location = request.form.get('location', '').strip()
        phone = request.form.get('phone', '').strip()
        linkedin = request.form.get('linkedin', '').strip()

        if not name or len(name) < 2:
            flash('Name must be at least 2 characters.', 'danger')
            return render_template('user/profile.html')

        # Normalize skills: split on commas, strip whitespace, rejoin cleanly
        if skills:
            skills = ', '.join(s.strip() for s in skills.split(',') if s.strip())

        current_user.name = name
        current_user.bio = bio
        current_user.skills = skills
        current_user.location = location
        current_user.phone = phone
        current_user.linkedin = linkedin

        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename and allowed_file(file.filename, ALLOWED_IMAGE):
                filename = secure_filename(f"avatar_{current_user.id}_{file.filename}")
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')
                os.makedirs(upload_path, exist_ok=True)
                file.save(os.path.join(upload_path, filename))
                current_user.profile_picture = filename

        # Handle resume upload
        if 'resume' in request.files:
            file = request.files['resume']
            if file and file.filename and allowed_file(file.filename, ALLOWED_RESUME):
                filename = secure_filename(f"resume_{current_user.id}_{file.filename}")
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'resumes')
                os.makedirs(upload_path, exist_ok=True)
                file.save(os.path.join(upload_path, filename))
                current_user.resume = filename

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user.profile'))

    return render_template('user/profile.html')


@user.route('/applied-jobs')
def applied_jobs():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')

    query = Application.query.filter_by(user_id=current_user.id)
    if status_filter:
        query = query.filter_by(status=status_filter)

    pagination = query.order_by(Application.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False)

    return render_template('user/applied_jobs.html',
                           pagination=pagination,
                           applications=pagination.items,
                           status_filter=status_filter)


@user.route('/saved-jobs')
def saved_jobs():
    page = request.args.get('page', 1, type=int)
    saved = SavedJob.query.filter_by(user_id=current_user.id)\
        .order_by(SavedJob.created_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)

    return render_template('user/saved_jobs.html',
                           pagination=saved,
                           saved_jobs=saved.items)


@user.route('/extract-skills', methods=['POST'])
def extract_skills():
    """Parse uploaded resume PDF and return suggested skills as JSON."""
    if not current_user.resume:
        return jsonify({'skills': [], 'error': 'No resume uploaded yet.'})

    resume_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'resumes', current_user.resume)
    if not os.path.exists(resume_path):
        return jsonify({'skills': [], 'error': 'Resume file not found.'})

    if not current_user.resume.lower().endswith('.pdf'):
        return jsonify({'skills': [], 'error': 'Skill extraction only works with PDF resumes.'})

    try:
        from pypdf import PdfReader
        reader = PdfReader(resume_path)
        text = ' '.join(page.extract_text() or '' for page in reader.pages).lower()
    except Exception as e:
        return jsonify({'skills': [], 'error': 'Could not read PDF.'})

    # Comprehensive skill keyword list
    KNOWN_SKILLS = [
        'python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'ruby', 'go', 'rust',
        'php', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl', 'bash', 'shell',
        'react', 'angular', 'vue', 'next.js', 'nuxt', 'svelte', 'jquery',
        'node.js', 'express', 'django', 'flask', 'fastapi', 'spring', 'rails', 'laravel',
        'postgresql', 'mysql', 'sqlite', 'mongodb', 'redis', 'elasticsearch', 'cassandra',
        'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'terraform', 'ansible', 'jenkins',
        'git', 'github', 'gitlab', 'bitbucket', 'ci/cd', 'devops',
        'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn',
        'pandas', 'numpy', 'data analysis', 'data science', 'nlp', 'computer vision',
        'html', 'css', 'sass', 'tailwind', 'bootstrap', 'graphql', 'rest api', 'restful',
        'microservices', 'agile', 'scrum', 'jira', 'figma', 'photoshop', 'linux', 'unix',
        'sql', 'nosql', 'firebase', 'supabase', 'heroku', 'nginx', 'apache',
        'excel', 'tableau', 'power bi', 'looker', 'spark', 'hadoop', 'kafka',
        'selenium', 'cypress', 'jest', 'pytest', 'junit', 'testing',
    ]

    found = []
    for skill in KNOWN_SKILLS:
        if skill in text and skill not in found:
            found.append(skill)

    # Format: capitalize first letter of each word
    formatted = [s.title() if ' ' not in s else s.upper() if len(s) <= 3 else s.title() for s in found]
    return jsonify({'skills': formatted[:25]})


@user.route('/job-alerts')
def job_alerts():
    alerts = JobAlert.query.filter_by(user_id=current_user.id).order_by(JobAlert.created_at.desc()).all()
    job_types = ['Full-time', 'Part-time', 'Remote', 'Contract', 'Internship']
    return render_template('user/job_alerts.html', alerts=alerts, job_types=job_types)


@user.route('/job-alerts/create', methods=['POST'])
def create_job_alert():
    keywords = request.form.get('keywords', '').strip()
    location = request.form.get('location', '').strip()
    job_type = request.form.get('job_type', '').strip()

    if not keywords and not location and not job_type:
        flash('Please specify at least one alert criterion.', 'warning')
        return redirect(url_for('user.job_alerts'))

    alert = JobAlert(
        user_id=current_user.id,
        keywords=keywords,
        location=location,
        job_type=job_type,
    )
    db.session.add(alert)
    db.session.commit()
    flash('Job alert created! You will be notified of matching jobs.', 'success')
    return redirect(url_for('user.job_alerts'))


@user.route('/job-alerts/<int:alert_id>/delete', methods=['POST'])
def delete_job_alert(alert_id):
    alert = JobAlert.query.filter_by(id=alert_id, user_id=current_user.id).first_or_404()
    db.session.delete(alert)
    db.session.commit()
    flash('Job alert deleted.', 'info')
    return redirect(url_for('user.job_alerts'))


@user.route('/saved-jobs/<int:job_id>/remove', methods=['POST'])
def remove_saved(job_id):
    saved = SavedJob.query.filter_by(
        user_id=current_user.id, job_id=job_id).first_or_404()
    db.session.delete(saved)
    db.session.commit()
    flash('Job removed from saved list.', 'info')
    return redirect(url_for('user.saved_jobs'))
