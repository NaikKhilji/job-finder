from datetime import datetime
from flask_login import UserMixin
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # user, company, admin
    profile_picture = db.Column(db.String(255), default='default_avatar.png')
    skills = db.Column(db.Text, default='')
    resume = db.Column(db.String(255), nullable=True)
    bio = db.Column(db.Text, default='')
    location = db.Column(db.String(100), default='')
    phone = db.Column(db.String(20), default='')
    linkedin = db.Column(db.String(255), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active_account = db.Column(db.Boolean, default=True)
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    google_id = db.Column(db.String(255), nullable=True)
    linkedin_id = db.Column(db.String(255), nullable=True)
    is_email_verified = db.Column(db.Boolean, default=False)
    email_verify_token = db.Column(db.String(255), nullable=True)

    # Relationships
    company = db.relationship('Company', backref='owner', uselist=False, lazy=True)
    applications = db.relationship('Application', backref='applicant', lazy=True,
                                   foreign_keys='Application.user_id')
    saved_jobs = db.relationship('SavedJob', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'


class Company(db.Model):
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default='')
    logo = db.Column(db.String(255), default='default_company.png')
    website = db.Column(db.String(255), default='')
    industry = db.Column(db.String(100), default='')
    size = db.Column(db.String(50), default='')  # e.g., "1-10", "11-50", etc.
    location = db.Column(db.String(100), default='')
    founded = db.Column(db.String(10), default='')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_approved = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    jobs = db.relationship('Job', backref='company', lazy=True,
                           cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Company {self.name}>'


class Job(db.Model):
    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, default='')
    responsibilities = db.Column(db.Text, default='')
    salary_min = db.Column(db.Integer, default=0)
    salary_max = db.Column(db.Integer, default=0)
    location = db.Column(db.String(100), nullable=False)
    job_type = db.Column(db.String(50), nullable=False)  # Full-time, Part-time, Remote, Contract
    experience_level = db.Column(db.String(50), default='Mid-level')
    skills_required = db.Column(db.Text, default='')
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.DateTime, nullable=True)

    # Relationships
    applications = db.relationship('Application', backref='job', lazy=True,
                                   cascade='all, delete-orphan')
    saved_by = db.relationship('SavedJob', backref='job', lazy=True,
                               cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Job {self.title}>'

    @property
    def salary_display(self):
        if self.salary_min and self.salary_max:
            return f'${self.salary_min:,} - ${self.salary_max:,}'
        elif self.salary_min:
            return f'From ${self.salary_min:,}'
        elif self.salary_max:
            return f'Up to ${self.salary_max:,}'
        return 'Negotiable'

    @property
    def application_count(self):
        return len(self.applications)


class Application(db.Model):
    __tablename__ = 'applications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, Accepted, Rejected
    cover_letter = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Application user={self.user_id} job={self.job_id}>'


class NewsletterSubscriber(db.Model):
    __tablename__ = 'newsletter_subscribers'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<NewsletterSubscriber {self.email}>'


class SavedJob(db.Model):
    __tablename__ = 'saved_jobs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'job_id', name='unique_saved_job'),)

    def __repr__(self):
        return f'<SavedJob user={self.user_id} job={self.job_id}>'


class JobAlert(db.Model):
    __tablename__ = 'job_alerts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    keywords = db.Column(db.String(255), default='')
    location = db.Column(db.String(100), default='')
    job_type = db.Column(db.String(50), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    user = db.relationship('User', backref='job_alerts', lazy=True)

    def __repr__(self):
        return f'<JobAlert user={self.user_id} keywords={self.keywords}>'


class Interview(db.Model):
    __tablename__ = 'interviews'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    interview_type = db.Column(db.String(20), default='Video')  # Phone, Video, In-person
    location_or_link = db.Column(db.String(255), default='')
    notes = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='Scheduled')  # Scheduled, Completed, Cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    application = db.relationship('Application', backref='interviews', lazy=True)

    def __repr__(self):
        return f'<Interview app={self.application_id} at={self.scheduled_at}>'
