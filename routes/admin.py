from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from extensions import db
from models import User, Company, Job, Application, JobAlert

admin = Blueprint('admin', __name__, url_prefix='/admin')


@admin.before_request
@login_required
def require_login():
    pass


@admin.before_request
def require_admin_role():
    if current_user.is_authenticated and current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('main.index'))


@admin.route('/dashboard')
def dashboard():
    total_users = User.query.filter_by(role='user').count()
    total_companies = Company.query.count()
    total_jobs = Job.query.count()
    total_applications = Application.query.count()
    pending_jobs = Job.query.filter_by(is_approved=False).count()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_jobs = Job.query.order_by(Job.created_at.desc()).limit(5).all()
    recent_apps = Application.query.order_by(Application.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_companies=total_companies,
                           total_jobs=total_jobs,
                           total_applications=total_applications,
                           pending_jobs=pending_jobs,
                           recent_users=recent_users,
                           recent_jobs=recent_jobs,
                           recent_apps=recent_apps)


@admin.route('/users')
def users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '')

    query = User.query
    if search:
        query = query.filter(
            (User.name.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )
    if role_filter:
        query = query.filter_by(role=role_filter)

    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=15, error_out=False)

    return render_template('admin/users.html',
                           users=pagination.items,
                           pagination=pagination,
                           search=search,
                           role_filter=role_filter)


@admin.route('/users/<int:user_id>/toggle', methods=['POST'])
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Cannot deactivate admin accounts.', 'danger')
        return redirect(url_for('admin.users'))
    user.is_active_account = not user.is_active_account
    db.session.commit()
    status = 'activated' if user.is_active_account else 'deactivated'
    flash(f'User {user.name} has been {status}.', 'success')
    return redirect(url_for('admin.users'))


@admin.route('/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Cannot delete admin accounts.', 'danger')
        return redirect(url_for('admin.users'))
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.name} has been deleted.', 'success')
    return redirect(url_for('admin.users'))


@admin.route('/companies')
def companies():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()

    query = Company.query
    if search:
        query = query.filter(Company.name.ilike(f'%{search}%'))

    pagination = query.order_by(Company.created_at.desc()).paginate(
        page=page, per_page=15, error_out=False)

    return render_template('admin/companies.html',
                           companies=pagination.items,
                           pagination=pagination,
                           search=search)


@admin.route('/companies/<int:company_id>/delete', methods=['POST'])
def delete_company(company_id):
    comp = Company.query.get_or_404(company_id)
    db.session.delete(comp)
    db.session.commit()
    flash(f'Company {comp.name} has been deleted.', 'success')
    return redirect(url_for('admin.companies'))


@admin.route('/jobs')
def jobs():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')

    query = Job.query.join(Company)
    if search:
        query = query.filter(
            (Job.title.ilike(f'%{search}%')) |
            (Company.name.ilike(f'%{search}%'))
        )
    if status_filter == 'pending':
        query = query.filter(Job.is_approved == False)
    elif status_filter == 'approved':
        query = query.filter(Job.is_approved == True)

    pagination = query.order_by(Job.created_at.desc()).paginate(
        page=page, per_page=15, error_out=False)

    return render_template('admin/jobs.html',
                           jobs=pagination.items,
                           pagination=pagination,
                           search=search,
                           status_filter=status_filter)


@admin.route('/jobs/<int:job_id>/approve', methods=['POST'])
def approve_job(job_id):
    job = Job.query.get_or_404(job_id)
    job.is_approved = True
    job.is_active = True
    db.session.commit()
    flash(f'Job "{job.title}" approved and published.', 'success')

    # Notify the company owner
    try:
        owner = job.company.owner
        if owner and owner.email:
            from utils.email import send_job_decision_to_company
            my_jobs_url = url_for('company.my_jobs', _external=True)
            send_job_decision_to_company(owner.email, job.company.name, job.title, True, my_jobs_url)
    except Exception:
        pass

    # Fire job alerts — notify users whose saved alerts match this job
    try:
        from utils.email import send_job_alert_email
        alerts = JobAlert.query.filter_by(is_active=True).all()
        job_text = f"{job.title} {job.description or ''}".lower()
        notified = set()
        for alert in alerts:
            user = alert.user
            if not user or not user.email or user.id in notified:
                continue
            # AND logic: every non-empty criterion must match
            if alert.keywords:
                keywords = [k.strip().lower() for k in alert.keywords.replace(',', ' ').split() if k.strip()]
                if not any(kw in job_text for kw in keywords):
                    continue
            if alert.location:
                if alert.location.lower() not in job.location.lower():
                    continue
            if alert.job_type:
                if alert.job_type.lower() != job.job_type.lower():
                    continue
            job_data = [{
                'title': job.title,
                'company': job.company.name,
                'location': job.location,
                'job_type': job.job_type,
                'salary': job.salary_display,
                'url': url_for('jobs.detail', job_id=job.id, _external=True),
            }]
            send_job_alert_email(user.email, user.name, job_data,
                                 url_for('user.job_alerts', _external=True))
            notified.add(user.id)
    except Exception:
        pass

    return redirect(url_for('admin.jobs'))


@admin.route('/jobs/<int:job_id>/reject', methods=['POST'])
def reject_job(job_id):
    job = Job.query.get_or_404(job_id)
    job.is_approved = False
    job.is_active = False
    db.session.commit()
    flash(f'Job "{job.title}" has been rejected.', 'warning')

    # Notify the company owner
    try:
        owner = job.company.owner
        if owner and owner.email:
            from utils.email import send_job_decision_to_company
            my_jobs_url = url_for('company.my_jobs', _external=True)
            send_job_decision_to_company(owner.email, job.company.name, job.title, False, my_jobs_url)
    except Exception:
        pass

    return redirect(url_for('admin.jobs'))


@admin.route('/jobs/<int:job_id>/delete', methods=['POST'])
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    flash(f'Job "{job.title}" has been deleted.', 'success')
    return redirect(url_for('admin.jobs'))


@admin.route('/applications')
def applications():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')

    query = Application.query
    if status_filter:
        query = query.filter_by(status=status_filter)

    pagination = query.order_by(Application.created_at.desc()).paginate(
        page=page, per_page=15, error_out=False)

    return render_template('admin/applications.html',
                           applications=pagination.items,
                           pagination=pagination,
                           status_filter=status_filter)
