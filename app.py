import os
from datetime import datetime
from flask import Flask
from config import Config
from extensions import db, login_manager, csrf, mail


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    # User loader
    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ── Context processor: inject data available in all templates ──────────
    from models import Job, Company

    @app.context_processor
    def inject_globals():
        return {
            'current_year': datetime.utcnow().year,
            'footer_job_count': Job.query.filter_by(is_approved=True, is_active=True).count(),
            'footer_company_count': Company.query.count(),
        }

    # Register blueprints
    from routes.main import main
    from routes.auth import auth
    from routes.user import user
    from routes.company import company
    from routes.admin import admin
    from routes.jobs import jobs

    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(user)
    app.register_blueprint(company)
    app.register_blueprint(admin)
    app.register_blueprint(jobs)

    # ── Social Auth (Google + LinkedIn via Flask-Dance) ─────────────────────
    # oauthlib reads this from os.environ directly (not Flask config)
    os.environ.setdefault('OAUTHLIB_INSECURE_TRANSPORT', '1')
    os.environ.setdefault('OAUTHLIB_RELAX_TOKEN_SCOPE', '1')

    google_client_id = app.config.get('GOOGLE_OAUTH_CLIENT_ID')
    google_client_secret = app.config.get('GOOGLE_OAUTH_CLIENT_SECRET')
    if google_client_id and google_client_secret \
            and google_client_id != 'your_google_client_id':
        from flask_dance.contrib.google import make_google_blueprint
        google_bp = make_google_blueprint(
            client_id=google_client_id,
            client_secret=google_client_secret,
            scope=['openid', 'https://www.googleapis.com/auth/userinfo.email',
                   'https://www.googleapis.com/auth/userinfo.profile'],
            redirect_url='/auth/google/callback',
            authorized_url='/authorized',
        )
        app.register_blueprint(google_bp, url_prefix='/auth/google')
        csrf.exempt(google_bp)

    linkedin_client_id = app.config.get('LINKEDIN_OAUTH_CLIENT_ID')
    linkedin_client_secret = app.config.get('LINKEDIN_OAUTH_CLIENT_SECRET')
    if linkedin_client_id and linkedin_client_secret \
            and linkedin_client_id != 'your_linkedin_client_id':
        from flask_dance.contrib.linkedin import make_linkedin_blueprint
        linkedin_bp = make_linkedin_blueprint(
            client_id=linkedin_client_id,
            client_secret=linkedin_client_secret,
            scope='openid profile email',
            redirect_url='/auth/linkedin/callback',
            authorized_url='/authorized',
        )
        app.register_blueprint(linkedin_bp, url_prefix='/auth/linkedin')
        csrf.exempt(linkedin_bp)

    # ── OAuth debug route (dev only) ────────────────────────────────────────
    @app.route('/oauth-uris')
    def oauth_uris():
        from flask import jsonify, url_for
        uris = {}
        try:
            uris['google_redirect_uri'] = url_for('google.authorized', _external=True)
        except Exception:
            uris['google_redirect_uri'] = 'Google OAuth not configured'
        try:
            uris['linkedin_redirect_uri'] = url_for('linkedin.authorized', _external=True)
        except Exception:
            uris['linkedin_redirect_uri'] = 'LinkedIn OAuth not configured'
        uris['note'] = 'Register these EXACT URIs in your developer consoles'
        return jsonify(uris)

    # Create upload directories
    for folder in ['avatars', 'logos', 'resumes']:
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], folder), exist_ok=True)

    # Create database tables and seed admin
    with app.app_context():
        db.create_all()
        _migrate_db()
        seed_admin()

    return app


def _migrate_db():
    """Safely add new columns to existing DB without dropping data."""
    import sqlalchemy as sa

    users_columns = [
        ('reset_token',        'VARCHAR(255)'),
        ('reset_token_expiry', 'DATETIME'),
        ('otp',                'VARCHAR(6)'),
        ('otp_expiry',         'DATETIME'),
        ('google_id',          'VARCHAR(255)'),
        ('linkedin_id',        'VARCHAR(255)'),
    ]
    jobs_columns = [
        ('deadline',           'DATETIME'),
    ]

    with db.engine.connect() as conn:
        existing_users = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(users)"))]
        for col_name, col_type in users_columns:
            if col_name not in existing_users:
                conn.execute(sa.text(f'ALTER TABLE users ADD COLUMN {col_name} {col_type}'))

        existing_jobs = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(jobs)"))]
        for col_name, col_type in jobs_columns:
            if col_name not in existing_jobs:
                conn.execute(sa.text(f'ALTER TABLE jobs ADD COLUMN {col_name} {col_type}'))

        conn.commit()


def seed_admin():
    from models import User
    from werkzeug.security import generate_password_hash
    from extensions import db

    admin = User.query.filter_by(email='admin@jobfinder.com').first()
    if not admin:
        admin = User(
            name='Admin',
            email='admin@jobfinder.com',
            password_hash=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print('Admin user created: admin@jobfinder.com / admin123')


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
