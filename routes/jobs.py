from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, and_
from extensions import db
from models import Job, Company, Application, SavedJob

jobs = Blueprint('jobs', __name__, url_prefix='/jobs')


@jobs.route('/')
def listing():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    location = request.args.get('location', '').strip()
    job_type = request.args.get('job_type', '').strip()
    salary_min = request.args.get('salary_min', 0, type=int)
    salary_max = request.args.get('salary_max', 0, type=int)
    experience = request.args.get('experience', '').strip()

    now = datetime.utcnow()
    query = Job.query.filter_by(is_approved=True, is_active=True).filter(
        or_(Job.deadline == None, Job.deadline >= now)
    ).join(Company)

    if search:
        query = query.filter(
            or_(
                Job.title.ilike(f'%{search}%'),
                Job.description.ilike(f'%{search}%'),
                Company.name.ilike(f'%{search}%'),
                Job.skills_required.ilike(f'%{search}%')
            )
        )
    if location:
        query = query.filter(Job.location.ilike(f'%{location}%'))
    if job_type:
        query = query.filter(Job.job_type == job_type)
    if salary_min:
        query = query.filter(Job.salary_max >= salary_min)
    if salary_max:
        query = query.filter(Job.salary_min <= salary_max)
    if experience:
        query = query.filter(Job.experience_level == experience)

    query = query.order_by(Job.created_at.desc())
    pagination = query.paginate(
        page=page,
        per_page=current_app.config['JOBS_PER_PAGE'],
        error_out=False
    )

    saved_job_ids = set()
    applied_job_ids = set()
    if current_user.is_authenticated and current_user.role == 'user':
        saved_job_ids = {sj.job_id for sj in SavedJob.query.filter_by(user_id=current_user.id).all()}
        applied_job_ids = {app.job_id for app in Application.query.filter_by(user_id=current_user.id).all()}

    job_types = ['Full-time', 'Part-time', 'Remote', 'Contract', 'Internship']
    experience_levels = ['Entry-level', 'Mid-level', 'Senior', 'Lead', 'Executive']

    return render_template('jobs/listing.html',
                           jobs=pagination.items,
                           pagination=pagination,
                           search=search,
                           location=location,
                           job_type=job_type,
                           salary_min=salary_min,
                           salary_max=salary_max,
                           experience=experience,
                           saved_job_ids=saved_job_ids,
                           applied_job_ids=applied_job_ids,
                           job_types=job_types,
                           experience_levels=experience_levels)


@jobs.route('/<int:job_id>')
def detail(job_id):
    job = Job.query.filter_by(id=job_id, is_approved=True, is_active=True).first_or_404()
    is_expired = job.deadline and job.deadline < datetime.utcnow()

    is_saved = False
    is_applied = False
    application = None

    if current_user.is_authenticated and current_user.role == 'user':
        saved = SavedJob.query.filter_by(user_id=current_user.id, job_id=job_id).first()
        is_saved = saved is not None
        application = Application.query.filter_by(
            user_id=current_user.id, job_id=job_id).first()
        is_applied = application is not None

    related_jobs = Job.query.filter(
        Job.company_id == job.company_id,
        Job.id != job_id,
        Job.is_approved == True,
        Job.is_active == True
    ).limit(3).all()

    return render_template('jobs/detail.html',
                           job=job,
                           is_saved=is_saved,
                           is_applied=is_applied,
                           is_expired=is_expired,
                           application=application,
                           related_jobs=related_jobs)


@jobs.route('/<int:job_id>/apply', methods=['POST'])
@login_required
def apply(job_id):
    if current_user.role != 'user':
        flash('Only job seekers can apply for jobs.', 'warning')
        return redirect(url_for('jobs.detail', job_id=job_id))

    job = Job.query.filter_by(id=job_id, is_approved=True, is_active=True).first_or_404()

    if job.deadline and job.deadline < datetime.utcnow():
        flash('This job posting has expired.', 'warning')
        return redirect(url_for('jobs.detail', job_id=job_id))

    existing = Application.query.filter_by(
        user_id=current_user.id, job_id=job_id).first()
    if existing:
        flash('You have already applied to this job.', 'warning')
        return redirect(url_for('jobs.detail', job_id=job_id))

    cover_letter = request.form.get('cover_letter', '').strip()

    application = Application(
        user_id=current_user.id,
        job_id=job_id,
        cover_letter=cover_letter,
        status='Pending'
    )
    db.session.add(application)
    db.session.commit()

    # Notify the company
    try:
        company_owner = job.company.owner  # User who owns the company
        if company_owner and company_owner.email:
            from utils.email import send_application_to_company
            applicants_url = url_for('company.applicants', job_id=job_id, _external=True)
            send_application_to_company(
                company_email=company_owner.email,
                company_name=job.company.name,
                job_title=job.title,
                applicant_name=current_user.name,
                applicant_email=current_user.email,
                cover_letter=cover_letter,
                applicants_url=applicants_url,
            )
    except Exception:
        pass  # Never block application submission due to email failure

    flash('Application submitted successfully! Good luck!', 'success')
    return redirect(url_for('jobs.detail', job_id=job_id))


@jobs.route('/<int:job_id>/save', methods=['POST'])
@login_required
def save_job(job_id):
    if current_user.role != 'user':
        flash('Only job seekers can save jobs.', 'warning')
        return redirect(url_for('jobs.detail', job_id=job_id))

    job = Job.query.get_or_404(job_id)
    existing = SavedJob.query.filter_by(
        user_id=current_user.id, job_id=job_id).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash('Job removed from saved list.', 'info')
    else:
        saved = SavedJob(user_id=current_user.id, job_id=job_id)
        db.session.add(saved)
        db.session.commit()
        flash('Job saved successfully!', 'success')

    next_page = request.form.get('next', url_for('jobs.detail', job_id=job_id))
    return redirect(next_page)
