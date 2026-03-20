import os
import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, Response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models import Company, Job, Application, User, Interview

company = Blueprint('company', __name__, url_prefix='/company')

ALLOWED_IMAGE = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set


@company.before_request
@login_required
def require_login():
    pass


@company.before_request
def require_company_role():
    if current_user.is_authenticated and current_user.role != 'company':
        flash('Access denied. Company account required.', 'danger')
        return redirect(url_for('main.index'))


@company.route('/dashboard')
def dashboard():
    comp = current_user.company
    if not comp:
        flash('Please complete your company profile first.', 'warning')
        return redirect(url_for('company.profile'))

    jobs = Job.query.filter_by(company_id=comp.id).order_by(Job.created_at.desc()).all()
    total_jobs = len(jobs)
    active_jobs = sum(1 for j in jobs if j.is_active and j.is_approved)
    pending_jobs = sum(1 for j in jobs if not j.is_approved)
    total_applications = sum(j.application_count for j in jobs)

    recent_apps = Application.query.join(Job).filter(
        Job.company_id == comp.id
    ).order_by(Application.created_at.desc()).limit(5).all()

    return render_template('company/dashboard.html',
                           company=comp,
                           jobs=jobs[:6],
                           total_jobs=total_jobs,
                           active_jobs=active_jobs,
                           pending_jobs=pending_jobs,
                           total_applications=total_applications,
                           recent_apps=recent_apps)


@company.route('/profile', methods=['GET', 'POST'])
def profile():
    comp = current_user.company
    if not comp:
        comp = Company(name=f"{current_user.name}'s Company", user_id=current_user.id)
        db.session.add(comp)
        db.session.commit()

    if request.method == 'POST':
        comp.name = request.form.get('name', '').strip()
        comp.description = request.form.get('description', '').strip()
        comp.website = request.form.get('website', '').strip()
        comp.industry = request.form.get('industry', '').strip()
        comp.size = request.form.get('size', '').strip()
        comp.location = request.form.get('location', '').strip()
        comp.founded = request.form.get('founded', '').strip()

        if not comp.name:
            flash('Company name is required.', 'danger')
            return render_template('company/profile.html', company=comp)

        # Handle logo upload
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename and allowed_file(file.filename, ALLOWED_IMAGE):
                filename = secure_filename(f"logo_{comp.id}_{file.filename}")
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'logos')
                os.makedirs(upload_path, exist_ok=True)
                file.save(os.path.join(upload_path, filename))
                comp.logo = filename

        db.session.commit()
        flash('Company profile updated successfully!', 'success')
        return redirect(url_for('company.profile'))

    return render_template('company/profile.html', company=comp)


@company.route('/jobs/post', methods=['GET', 'POST'])
def post_job():
    comp = current_user.company
    if not comp:
        flash('Please complete your company profile first.', 'warning')
        return redirect(url_for('company.profile'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        requirements = request.form.get('requirements', '').strip()
        responsibilities = request.form.get('responsibilities', '').strip()
        location = request.form.get('location', '').strip()
        job_type = request.form.get('job_type', '').strip()
        experience_level = request.form.get('experience_level', 'Mid-level').strip()
        skills_required = request.form.get('skills_required', '').strip()
        salary_min = request.form.get('salary_min', 0, type=int)
        salary_max = request.form.get('salary_max', 0, type=int)
        deadline_str = request.form.get('deadline', '').strip()
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
            except ValueError:
                pass

        errors = []
        if not title:
            errors.append('Job title is required.')
        if not description or len(description) < 50:
            errors.append('Description must be at least 50 characters.')
        if not location:
            errors.append('Location is required.')
        if not job_type:
            errors.append('Job type is required.')

        # Duplicate job detection
        duplicate = Job.query.filter(
            Job.company_id == comp.id,
            Job.title.ilike(title),
            Job.is_active == True,
        ).first()
        if duplicate:
            flash(
                f'You already have an active job posting titled "{duplicate.title}". '
                'Please edit the existing one or choose a different title.',
                'warning'
            )

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('company/post_job.html', company=comp,
                                   job_types=['Full-time', 'Part-time', 'Remote', 'Contract', 'Internship'],
                                   experience_levels=['Entry-level', 'Mid-level', 'Senior', 'Lead', 'Executive'])

        job = Job(
            title=title,
            description=description,
            requirements=requirements,
            responsibilities=responsibilities,
            location=location,
            job_type=job_type,
            experience_level=experience_level,
            skills_required=skills_required,
            salary_min=salary_min,
            salary_max=salary_max,
            deadline=deadline,
            company_id=comp.id,
            is_approved=False
        )
        db.session.add(job)
        db.session.commit()

        # Notify admin that a new job needs approval
        try:
            admin_email = current_app.config.get('ADMIN_EMAIL')
            if admin_email:
                from utils.email import send_new_job_to_admin
                admin_jobs_url = url_for('admin.jobs', status='pending', _external=True)
                send_new_job_to_admin(admin_email, title, comp.name, admin_jobs_url)
        except Exception:
            pass

        flash('Job posted successfully! It will be visible after admin approval.', 'success')
        return redirect(url_for('company.my_jobs'))

    job_types = ['Full-time', 'Part-time', 'Remote', 'Contract', 'Internship']
    experience_levels = ['Entry-level', 'Mid-level', 'Senior', 'Lead', 'Executive']
    return render_template('company/post_job.html',
                           company=comp,
                           job_types=job_types,
                           experience_levels=experience_levels)


@company.route('/jobs')
def my_jobs():
    comp = current_user.company
    if not comp:
        return redirect(url_for('company.profile'))

    page = request.args.get('page', 1, type=int)
    jobs_pagination = Job.query.filter_by(company_id=comp.id)\
        .order_by(Job.created_at.desc())\
        .paginate(page=page, per_page=10, error_out=False)

    return render_template('company/my_jobs.html',
                           pagination=jobs_pagination,
                           jobs=jobs_pagination.items,
                           company=comp)


@company.route('/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
def edit_job(job_id):
    comp = current_user.company
    job = Job.query.filter_by(id=job_id, company_id=comp.id).first_or_404()

    if request.method == 'POST':
        job.title = request.form.get('title', '').strip()
        job.description = request.form.get('description', '').strip()
        job.requirements = request.form.get('requirements', '').strip()
        job.responsibilities = request.form.get('responsibilities', '').strip()
        job.location = request.form.get('location', '').strip()
        job.job_type = request.form.get('job_type', '').strip()
        job.experience_level = request.form.get('experience_level', 'Mid-level').strip()
        job.skills_required = request.form.get('skills_required', '').strip()
        job.salary_min = request.form.get('salary_min', 0, type=int)
        job.salary_max = request.form.get('salary_max', 0, type=int)
        job.is_active = 'is_active' in request.form
        job.is_approved = False  # Re-approval needed after edit
        deadline_str = request.form.get('deadline', '').strip()
        if deadline_str:
            try:
                job.deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
            except ValueError:
                pass
        else:
            job.deadline = None

        db.session.commit()
        flash('Job updated! It will need re-approval by admin.', 'success')
        return redirect(url_for('company.my_jobs'))

    job_types = ['Full-time', 'Part-time', 'Remote', 'Contract', 'Internship']
    experience_levels = ['Entry-level', 'Mid-level', 'Senior', 'Lead', 'Executive']
    return render_template('company/post_job.html',
                           job=job,
                           company=comp,
                           job_types=job_types,
                           experience_levels=experience_levels,
                           editing=True)


@company.route('/jobs/<int:job_id>/delete', methods=['POST'])
def delete_job(job_id):
    comp = current_user.company
    job = Job.query.filter_by(id=job_id, company_id=comp.id).first_or_404()
    db.session.delete(job)
    db.session.commit()
    flash('Job deleted successfully.', 'success')
    return redirect(url_for('company.my_jobs'))


@company.route('/jobs/<int:job_id>/applicants')
def applicants(job_id):
    comp = current_user.company
    job = Job.query.filter_by(id=job_id, company_id=comp.id).first_or_404()
    status_filter = request.args.get('status', '')

    query = Application.query.filter_by(job_id=job_id)
    if status_filter:
        query = query.filter_by(status=status_filter)

    apps = query.order_by(Application.created_at.desc()).all()

    return render_template('company/applicants.html',
                           job=job,
                           applications=apps,
                           company=comp,
                           status_filter=status_filter)


@company.route('/applications/<int:app_id>/update', methods=['POST'])
def update_application(app_id):
    comp = current_user.company
    application = Application.query.get_or_404(app_id)

    # Verify the job belongs to this company
    if application.job.company_id != comp.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('company.dashboard'))

    status = request.form.get('status')
    if status in ['Pending', 'Accepted', 'Rejected']:
        old_status = application.status
        application.status = status
        db.session.commit()
        flash(f'Application status updated to {status}.', 'success')

        # Email the job seeker only when status meaningfully changes
        if status != old_status and status in ('Accepted', 'Rejected'):
            try:
                seeker = application.applicant
                from utils.email import send_application_status_to_seeker
                jobs_url = url_for('jobs.listing', _external=True)
                send_application_status_to_seeker(
                    seeker_email=seeker.email,
                    seeker_name=seeker.name,
                    job_title=application.job.title,
                    company_name=comp.name,
                    status=status,
                    jobs_url=jobs_url,
                )
            except Exception:
                pass

    return redirect(url_for('company.applicants', job_id=application.job_id))


@company.route('/applications/<int:app_id>/interview', methods=['POST'])
def schedule_interview(app_id):
    comp = current_user.company
    application = Application.query.get_or_404(app_id)

    if application.job.company_id != comp.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('company.dashboard'))

    scheduled_str = request.form.get('scheduled_at', '').strip()
    interview_type = request.form.get('interview_type', 'Video').strip()
    location_or_link = request.form.get('location_or_link', '').strip()
    notes = request.form.get('notes', '').strip()

    if not scheduled_str:
        flash('Please provide a date and time for the interview.', 'danger')
        return redirect(url_for('company.applicants', job_id=application.job_id))

    try:
        scheduled_at = datetime.strptime(scheduled_str, '%Y-%m-%dT%H:%M')
    except ValueError:
        flash('Invalid date/time format.', 'danger')
        return redirect(url_for('company.applicants', job_id=application.job_id))

    interview = Interview(
        application_id=app_id,
        scheduled_at=scheduled_at,
        interview_type=interview_type,
        location_or_link=location_or_link,
        notes=notes,
        status='Scheduled',
    )
    db.session.add(interview)
    db.session.commit()

    # Notify the seeker
    try:
        seeker = application.applicant
        from utils.email import send_interview_scheduled
        send_interview_scheduled(
            seeker_email=seeker.email,
            seeker_name=seeker.name,
            job_title=application.job.title,
            company_name=comp.name,
            scheduled_at=scheduled_at.strftime('%B %d, %Y at %I:%M %p'),
            interview_type=interview_type,
            location_or_link=location_or_link,
            notes=notes,
        )
    except Exception:
        pass

    flash(f'Interview scheduled for {scheduled_at.strftime("%b %d, %Y at %I:%M %p")}!', 'success')
    return redirect(url_for('company.applicants', job_id=application.job_id))


@company.route('/jobs/<int:job_id>/applicants/export')
def export_applicants_csv(job_id):
    """Export applicants for a job as CSV."""
    comp = current_user.company
    job = Job.query.filter_by(id=job_id, company_id=comp.id).first_or_404()
    apps = Application.query.filter_by(job_id=job_id).order_by(Application.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Applicant Name', 'Email', 'Status', 'Applied On', 'Cover Letter'])
    for app in apps:
        writer.writerow([
            app.applicant.name,
            app.applicant.email,
            app.status,
            app.created_at.strftime('%Y-%m-%d %H:%M'),
            app.cover_letter.replace('\n', ' ') if app.cover_letter else '',
        ])

    output.seek(0)
    filename = f"applicants_{job.title.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@company.route('/interviews/<int:interview_id>/update', methods=['POST'])
def update_interview(interview_id):
    comp = current_user.company
    interview = Interview.query.get_or_404(interview_id)

    if interview.application.job.company_id != comp.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('company.dashboard'))

    new_status = request.form.get('status')
    if new_status in ('Completed', 'Cancelled'):
        interview.status = new_status
        db.session.commit()
        flash(f'Interview marked as {new_status}.', 'success')

    return redirect(url_for('company.applicants', job_id=interview.application.job_id))
