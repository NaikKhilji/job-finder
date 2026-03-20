import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()  # loads .env file if present

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-please-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'jobfinder.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Pin hostname for consistent OAuth redirect URI generation (dev only)
    # Remove or leave empty in production
    SERVER_NAME = os.environ.get('OAUTH_SERVER_NAME')

    # File uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    ALLOWED_RESUME_EXTENSIONS = {'pdf', 'doc', 'docx'}
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    WTF_CSRF_ENABLED = True

    # Pagination
    JOBS_PER_PAGE = 9

    # ── Email (Gmail SMTP) ────────────────────────────────────────────────────
    MAIL_SERVER   = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT     = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS  = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')          # set in .env
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')          # set in .env
    MAIL_DEFAULT_SENDER = os.environ.get(
        'MAIL_DEFAULT_SENDER',
        f"JobFinder <{os.environ.get('MAIL_USERNAME', 'noreply@jobfinder.com')}>"
    )
    # Admin address that receives new-job and contact notifications
    ADMIN_EMAIL   = os.environ.get('ADMIN_EMAIL', os.environ.get('MAIL_USERNAME', 'admin@jobfinder.com'))

    # ── Social OAuth ──────────────────────────────────────────────────────────
    GOOGLE_OAUTH_CLIENT_ID     = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
    LINKEDIN_OAUTH_CLIENT_ID     = os.environ.get('LINKEDIN_OAUTH_CLIENT_ID')
    LINKEDIN_OAUTH_CLIENT_SECRET = os.environ.get('LINKEDIN_OAUTH_CLIENT_SECRET')
    # Note: OAUTHLIB_INSECURE_TRANSPORT is set in os.environ directly in app.py
    # (oauthlib reads from os.environ, not Flask config)

    # ── Social media links (shown in footer) ─────────────────────────────────
    SOCIAL_TWITTER  = os.environ.get('SOCIAL_TWITTER', '#')
    SOCIAL_LINKEDIN = os.environ.get('SOCIAL_LINKEDIN', '#')
    SOCIAL_GITHUB   = os.environ.get('SOCIAL_GITHUB', '#')
    SOCIAL_FACEBOOK = os.environ.get('SOCIAL_FACEBOOK', '#')
