import os
from datetime import datetime
from flask import Blueprint, render_template, send_from_directory, current_app, abort, request, flash, redirect, url_for, Response
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


@main.route('/robots.txt')
def robots():
    lines = [
        'User-agent: *',
        'Allow: /',
        'Disallow: /admin/',
        'Disallow: /auth/',
        'Disallow: /user/',
        'Disallow: /company/',
        f'Sitemap: {request.host_url}sitemap.xml',
    ]
    return Response('\n'.join(lines), mimetype='text/plain')


@main.route('/sitemap.xml')
def sitemap():
    now = datetime.utcnow().strftime('%Y-%m-%d')
    urls = []

    # Static pages
    static_pages = [
        ('main.index', 'daily', '1.0'),
        ('jobs.listing', 'daily', '0.9'),
        ('main.contact', 'monthly', '0.5'),
        ('main.terms', 'monthly', '0.3'),
        ('main.privacy', 'monthly', '0.3'),
    ]
    for endpoint, freq, priority in static_pages:
        try:
            loc = url_for(endpoint, _external=True)
            urls.append(f'''  <url>
    <loc>{loc}</loc>
    <lastmod>{now}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{priority}</priority>
  </url>''')
        except Exception:
            pass

    # Job detail pages
    jobs = Job.query.filter_by(is_approved=True, is_active=True).all()
    for job in jobs:
        loc = url_for('jobs.detail', job_id=job.id, _external=True)
        lastmod = job.created_at.strftime('%Y-%m-%d')
        urls.append(f'''  <url>
    <loc>{loc}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>''')

    # Company profile pages
    companies = Company.query.all()
    for comp in companies:
        loc = url_for('main.company_profile', company_id=comp.id, _external=True)
        lastmod = comp.created_at.strftime('%Y-%m-%d')
        urls.append(f'''  <url>
    <loc>{loc}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.6</priority>
  </url>''')

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += '\n'.join(urls)
    xml += '\n</urlset>'
    return Response(xml, mimetype='application/xml')


@main.app_errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404


@main.app_errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500
