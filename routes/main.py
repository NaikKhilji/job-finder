import os
from datetime import datetime
from flask import Blueprint, render_template, send_from_directory, current_app, abort, request, flash, redirect, url_for
from models import Job, Company, NewsletterSubscriber
from extensions import db

main = Blueprint('main', __name__)


@main.route('/')
def index():
    featured_jobs = Job.query.filter_by(is_approved=True, is_active=True)\
        .order_by(Job.created_at.desc()).limit(6).all()
    total_jobs = Job.query.filter_by(is_approved=True, is_active=True).count()
    total_companies = Company.query.count()

    return render_template('index.html',
                           featured_jobs=featured_jobs,
                           total_jobs=total_jobs,
                           total_companies=total_companies)


@main.route('/uploads/<folder>/<filename>')
def uploaded_file(folder, filename):
    allowed_folders = ['avatars', 'logos', 'resumes']
    if folder not in allowed_folders:
        abort(404)
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder)
    return send_from_directory(upload_path, filename)


@main.route('/terms')
def terms():
    return render_template('main/terms.html')


@main.route('/privacy')
def privacy():
    return render_template('main/privacy.html')


@main.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name    = request.form.get('name', '').strip()
        email   = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        errors = []
        if not name or len(name) < 2:
            errors.append('Please enter your name.')
        if not email or '@' not in email:
            errors.append('Please enter a valid email address.')
        if not subject:
            errors.append('Please select a subject.')
        if not message or len(message) < 10:
            errors.append('Message must be at least 10 characters.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('main/contact.html',
                                   form_data={'name': name, 'email': email,
                                              'subject': subject, 'message': message})

        # Forward message to admin
        admin_email = current_app.config.get('ADMIN_EMAIL')
        if admin_email:
            from utils.email import send_contact_to_admin
            send_contact_to_admin(admin_email, name, email, subject, message)

        flash(f"Thanks {name}! Your message has been received. We'll get back to you within 24 hours.", 'success')
        return redirect(url_for('main.contact'))

    return render_template('main/contact.html', form_data={})


@main.route('/newsletter', methods=['POST'])
def newsletter():
    email = request.form.get('email', '').strip().lower()
    if not email or '@' not in email:
        flash('Please enter a valid email address.', 'danger')
        return redirect(request.referrer or url_for('main.index'))

    existing = NewsletterSubscriber.query.filter_by(email=email).first()
    if existing:
        if existing.is_active:
            flash('You are already subscribed to job alerts!', 'info')
        else:
            existing.is_active = True
            db.session.commit()
            flash(f"Welcome back! Job alerts re-enabled for {email}.", 'success')
    else:
        subscriber = NewsletterSubscriber(email=email)
        db.session.add(subscriber)
        db.session.commit()

        from utils.email import send_newsletter_confirmation
        send_newsletter_confirmation(email)

        flash(f"You're subscribed! Check your inbox for a confirmation email.", 'success')

    return redirect(request.referrer or url_for('main.index'))


@main.route('/companies/<int:company_id>')
def company_profile(company_id):
    comp = Company.query.get_or_404(company_id)
    now = datetime.utcnow()
    active_jobs = Job.query.filter_by(
        company_id=comp.id, is_approved=True, is_active=True
    ).filter(
        (Job.deadline == None) | (Job.deadline >= now)
    ).order_by(Job.created_at.desc()).all()

    return render_template('main/company_profile.html', company=comp, jobs=active_jobs)


@main.app_errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404


@main.app_errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500
