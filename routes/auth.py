import re
import secrets
from datetime import datetime, timedelta
import random
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from markupsafe import Markup
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, limiter
from models import User, Company

auth = Blueprint('auth', __name__, url_prefix='/auth')

# Password strength: 8+ chars, at least one uppercase, one digit
_PASSWORD_RE = re.compile(r'^(?=.*[A-Z])(?=.*\d).{8,}$')


def _validate_password(password: str) -> str | None:
    """Return an error string if password is too weak, else None."""
    if len(password) < 8:
        return 'Password must be at least 8 characters.'
    if not re.search(r'[A-Z]', password):
        return 'Password must contain at least one uppercase letter.'
    if not re.search(r'\d', password):
        return 'Password must contain at least one number.'
    return None


@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("20 per minute")
def login():
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html')

        if not user.is_active_account:
            flash('Your account has been suspended. Contact support.', 'danger')
            return render_template('auth/login.html')

        # Warn unverified users but still allow login
        if not user.is_email_verified and user.role not in ('admin',):
            flash(
                Markup('Your email is not verified. '
                       f'<a href="{url_for("auth.resend_verification")}">Resend verification email</a>.'),
                'warning'
            )

        login_user(user, remember=bool(remember))
        flash(f'Welcome back, {user.name}!', 'success')

        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect_by_role(user.role)

    return render_template('auth/login.html')


@auth.route('/signup', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def signup():
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'user')

        errors = []
        if not name or len(name) < 2:
            errors.append('Name must be at least 2 characters.')
        if not email or '@' not in email:
            errors.append('Please enter a valid email address.')
        pw_error = _validate_password(password)
        if pw_error:
            errors.append(pw_error)
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if role not in ['user', 'company']:
            errors.append('Invalid role selected.')
        if User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('auth/signup.html')

        verify_token = secrets.token_urlsafe(32)
        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            is_email_verified=False,
            email_verify_token=verify_token,
        )
        db.session.add(user)
        db.session.flush()

        if role == 'company':
            company_name = request.form.get('company_name', '').strip() or f"{name}'s Company"
            company = Company(name=company_name, user_id=user.id)
            db.session.add(company)

        db.session.commit()

        # Send verification email; fall back to showing the link in dev (no SMTP)
        try:
            from utils.email import send_email_verification
            verify_url = request.host_url.rstrip('/') + url_for('auth.verify_email', token=verify_token)
            sent = send_email_verification(email, name, verify_url)
        except Exception:
            sent = False

        login_user(user)
        if sent:
            flash(
                Markup(f'Account created! Welcome, {name}! '
                       'A verification email has been sent — please check your inbox.'),
                'success'
            )
        else:
            flash(
                Markup(
                    f'Account created! Welcome, {name}! '
                    f'<strong>Dev mode (no SMTP):</strong> '
                    f'<a href="{url_for("auth.verify_email", token=verify_token)}" class="alert-link">'
                    f'Click here to verify your email</a> — configure MAIL_USERNAME in .env to send real emails.'
                ),
                'warning'
            )
        return redirect_by_role(user.role)

    return render_template('auth/signup.html')


@auth.route('/verify-email/<token>')
def verify_email(token):
    user = User.query.filter_by(email_verify_token=token).first()
    if not user:
        flash('Invalid or expired verification link.', 'danger')
        return redirect(url_for('auth.login'))

    user.is_email_verified = True
    user.email_verify_token = None
    db.session.commit()
    flash('Email verified successfully! Your account is fully active.', 'success')
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)
    return redirect(url_for('auth.login'))


@auth.route('/resend-verification')
@login_required
@limiter.limit("3 per hour")
def resend_verification():
    if current_user.is_email_verified:
        flash('Your email is already verified.', 'info')
        return redirect_by_role(current_user.role)

    verify_token = secrets.token_urlsafe(32)
    current_user.email_verify_token = verify_token
    db.session.commit()

    try:
        from utils.email import send_email_verification
        verify_url = request.host_url.rstrip('/') + url_for('auth.verify_email', token=verify_token)
        sent = send_email_verification(current_user.email, current_user.name, verify_url)
        if sent:
            flash('Verification email sent! Please check your inbox.', 'success')
        else:
            flash(
                Markup(
                    f'<strong>Dev mode (no SMTP):</strong> '
                    f'<a href="{url_for("auth.verify_email", token=verify_token)}" class="alert-link">'
                    f'Click here to verify your email</a>'
                ),
                'warning'
            )
    except Exception:
        flash('Could not send verification email. Please try again later.', 'danger')

    return redirect_by_role(current_user.role)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


# ── FORGOT PASSWORD ──────────────────────────────────────────────────────────

@auth.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def forgot_password():
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if not email or '@' not in email:
            flash('Please enter a valid email address.', 'danger')
            return render_template('auth/forgot_password.html')

        user = User.query.filter_by(email=email).first()

        if user and user.is_active_account:
            otp = str(random.randint(100000, 999999))
            user.otp = otp
            user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
            db.session.commit()

            session['reset_email'] = email

            from utils.email import send_otp_email
            sent = send_otp_email(email, otp, user.name)
            if sent:
                flash('A 6-digit OTP has been sent to your email address.', 'info')
            else:
                flash(Markup(
                    f'<strong>Dev mode (no SMTP):</strong> Your OTP is '
                    f'<strong class="fs-5 font-monospace">{otp}</strong> — '
                    f'configure MAIL_USERNAME in .env to send real emails.'
                ), 'warning')
            return redirect(url_for('auth.verify_otp'))
        else:
            flash('If an account exists for that email, an OTP has been sent.', 'info')

        return redirect(url_for('auth.forgot_password'))

    return render_template('auth/forgot_password.html')


# ── VERIFY OTP ───────────────────────────────────────────────────────────────

@auth.route('/verify-otp', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def verify_otp():
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)

    email = session.get('reset_email')
    if not email:
        flash('Session expired. Please start over.', 'warning')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()
        user = User.query.filter_by(email=email).first()

        if not user or not user.otp or not user.otp_expiry:
            flash('Invalid request. Please start over.', 'danger')
            session.pop('reset_email', None)
            return redirect(url_for('auth.forgot_password'))

        if user.otp_expiry < datetime.utcnow():
            user.otp = None
            user.otp_expiry = None
            db.session.commit()
            session.pop('reset_email', None)
            flash('OTP has expired. Please request a new one.', 'danger')
            return redirect(url_for('auth.forgot_password'))

        if entered_otp != user.otp:
            flash('Incorrect OTP. Please try again.', 'danger')
            return render_template('auth/verify_otp.html', email=email)

        user.otp = None
        user.otp_expiry = None
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expiry = datetime.utcnow() + timedelta(minutes=15)
        db.session.commit()
        session.pop('reset_email', None)

        return redirect(url_for('auth.reset_password', token=token))

    return render_template('auth/verify_otp.html', email=email)


@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect_by_role(current_user.role)

    user = User.query.filter_by(reset_token=token).first()

    if not user or not user.reset_token_expiry or \
            user.reset_token_expiry < datetime.utcnow():
        flash('This password reset link is invalid or has expired. Please request a new one.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        errors = []
        pw_error = _validate_password(password)
        if pw_error:
            errors.append(pw_error)
        if password != confirm_password:
            errors.append('Passwords do not match.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('auth/reset_password.html', token=token)

        user.password_hash = generate_password_hash(password)
        user.reset_token = None
        user.reset_token_expiry = None
        # Invalidate all existing sessions by rotating the session
        session.clear()
        db.session.commit()

        flash('Your password has been reset successfully. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token, user=user)


def redirect_by_role(role):
    if role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif role == 'company':
        return redirect(url_for('company.dashboard'))
    else:
        return redirect(url_for('user.dashboard'))


# ── GOOGLE OAUTH CALLBACK ─────────────────────────────────────────────────────

@auth.route('/google/callback')
def google_callback():
    from flask import current_app
    if not current_app.config.get('GOOGLE_OAUTH_CLIENT_ID'):
        flash('Google login is not configured.', 'warning')
        return redirect(url_for('auth.login'))

    try:
        from flask_dance.contrib.google import google as google_oauth
        if not google_oauth.authorized:
            flash('Google authorization failed. Please try again.', 'danger')
            return redirect(url_for('auth.login'))

        resp = google_oauth.get('/oauth2/v2/userinfo')
        if not resp.ok:
            flash('Failed to fetch Google profile.', 'danger')
            return redirect(url_for('auth.login'))

        info = resp.json()
        google_id = info.get('id')
        email = info.get('email', '').lower()
        name = info.get('name', email.split('@')[0])

        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            user = User.query.filter_by(email=email).first()
            if user:
                user.google_id = google_id
                user.is_email_verified = True  # Google verifies emails
            else:
                user = User(
                    name=name, email=email,
                    password_hash=generate_password_hash(secrets.token_hex(16)),
                    role='user', google_id=google_id,
                    is_email_verified=True,
                )
                db.session.add(user)
            db.session.commit()

        if not user.is_active_account:
            flash('Your account has been suspended.', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user)
        flash(f'Welcome, {user.name}!', 'success')
        return redirect_by_role(user.role)
    except Exception:
        flash('Google login failed. Please try again.', 'danger')
        return redirect(url_for('auth.login'))


# ── LINKEDIN OAUTH CALLBACK ───────────────────────────────────────────────────

@auth.route('/linkedin/callback')
def linkedin_callback():
    from flask import current_app
    if not current_app.config.get('LINKEDIN_OAUTH_CLIENT_ID'):
        flash('LinkedIn login is not configured.', 'warning')
        return redirect(url_for('auth.login'))

    try:
        from flask_dance.contrib.linkedin import linkedin as linkedin_oauth
        if not linkedin_oauth.authorized:
            flash('LinkedIn authorization failed. Please try again.', 'danger')
            return redirect(url_for('auth.login'))

        profile_resp = linkedin_oauth.get('https://api.linkedin.com/v2/userinfo')
        if not profile_resp.ok:
            flash('Failed to fetch LinkedIn profile.', 'danger')
            return redirect(url_for('auth.login'))

        info = profile_resp.json()
        linkedin_id = info.get('sub')
        email = info.get('email', '').lower()
        name = info.get('name', email.split('@')[0] if email else 'LinkedIn User')

        user = User.query.filter_by(linkedin_id=linkedin_id).first()
        if not user:
            user = User.query.filter_by(email=email).first()
            if user:
                user.linkedin_id = linkedin_id
                user.is_email_verified = True  # LinkedIn verifies emails
            else:
                user = User(
                    name=name, email=email,
                    password_hash=generate_password_hash(secrets.token_hex(16)),
                    role='user', linkedin_id=linkedin_id,
                    is_email_verified=True,
                )
                db.session.add(user)
            db.session.commit()

        if not user.is_active_account:
            flash('Your account has been suspended.', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user)
        flash(f'Welcome, {user.name}!', 'success')
        return redirect_by_role(user.role)
    except Exception:
        flash('LinkedIn login failed. Please try again.', 'danger')
        return redirect(url_for('auth.login'))
