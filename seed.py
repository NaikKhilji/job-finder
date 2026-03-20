"""
Seed script — populate the database with sample data for development/demo.
Run with: python seed.py
"""
from app import app, db
from models import User, Company, Job, Application, SavedJob
from werkzeug.security import generate_password_hash


def seed():
    with app.app_context():
        print("Seeding database...")

        # Admin
        if not User.query.filter_by(email='admin@jobfinder.com').first():
            admin = User(
                name='Admin',
                email='admin@jobfinder.com',
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)

        # Job Seekers
        seekers_data = [
            ('Alice Johnson', 'alice@example.com', 'Python, Django, PostgreSQL, REST APIs', 'Senior Python developer with 6 years experience.'),
            ('Bob Smith', 'bob@example.com', 'React, TypeScript, CSS, Node.js', 'Frontend engineer passionate about UX.'),
            ('Carol White', 'carol@example.com', 'Product Management, Agile, SQL, Figma', 'PM with 4 years building B2B SaaS products.'),
        ]

        seekers = []
        for name, email, skills, bio in seekers_data:
            if not User.query.filter_by(email=email).first():
                u = User(
                    name=name, email=email,
                    password_hash=generate_password_hash('test123'),
                    role='user', skills=skills, bio=bio,
                    location='San Francisco, CA'
                )
                db.session.add(u)
                seekers.append(u)

        db.session.flush()

        # Companies
        companies_data = [
            ('techcorp@example.com', 'TechCorp Inc', 'Technology', '51-200', 'San Francisco, CA', '2015',
             'Leading technology company building next-generation software for enterprise clients worldwide.'),
            ('startup@example.com', 'StartupXYZ', 'Finance', '11-50', 'Austin, TX', '2021',
             'Fast-growing fintech startup disrupting traditional banking with AI-powered solutions.'),
            ('megacorp@example.com', 'MegaCorp Global', 'Consulting', '1000+', 'New York, NY', '2000',
             'Global consulting firm helping Fortune 500 companies transform digitally.'),
        ]

        companies = []
        for email, cname, industry, size, location, founded, desc in companies_data:
            if not User.query.filter_by(email=email).first():
                u = User(
                    name=f'{cname} HR', email=email,
                    password_hash=generate_password_hash('test123'),
                    role='company'
                )
                db.session.add(u)
                db.session.flush()
                c = Company(
                    name=cname, industry=industry, size=size,
                    location=location, founded=founded,
                    description=desc, user_id=u.id
                )
                db.session.add(c)
                db.session.flush()
                companies.append(c)

        db.session.flush()

        # Jobs
        all_companies = Company.query.all()
        if all_companies and not Job.query.first():
            jobs_data = [
                (all_companies[0].id, 'Senior Python Developer', 'Full-time', 'San Francisco, CA', 'Senior',
                 120000, 160000, 'Python, Flask, PostgreSQL, Redis, Docker',
                 'We are looking for a senior Python developer to join our backend team.'),
                (all_companies[0].id, 'React Frontend Engineer', 'Remote', 'Remote', 'Mid-level',
                 90000, 130000, 'React, TypeScript, TailwindCSS, GraphQL',
                 'Build beautiful, responsive UIs for millions of users.'),
                (all_companies[0].id, 'DevOps Engineer', 'Full-time', 'San Francisco, CA', 'Senior',
                 130000, 170000, 'Kubernetes, Docker, AWS, Terraform',
                 'Scale our infrastructure and build CI/CD pipelines.'),
                (all_companies[1].id, 'Product Manager', 'Full-time', 'Austin, TX', 'Mid-level',
                 100000, 140000, 'Product Strategy, Agile, SQL, Figma',
                 'Lead product strategy for our AI-powered fintech platform.'),
                (all_companies[1].id, 'UX/UI Designer', 'Remote', 'Remote', 'Mid-level',
                 80000, 110000, 'Figma, User Research, Design Systems',
                 'Design intuitive experiences for our mobile and web apps.'),
                (all_companies[1].id, 'Marketing Intern', 'Internship', 'Austin, TX', 'Entry-level',
                 25000, 35000, 'Social Media, Content Writing, SEO',
                 'Learn digital marketing in a fast-paced startup environment.'),
            ]

            for comp_id, title, jtype, loc, exp, smin, smax, skills, desc in jobs_data:
                job = Job(
                    company_id=comp_id, title=title, job_type=jtype,
                    location=loc, experience_level=exp,
                    salary_min=smin, salary_max=smax,
                    skills_required=skills, description=desc,
                    is_approved=True
                )
                db.session.add(job)

        db.session.commit()
        print("✓ Database seeded successfully!")
        print("\nDemo credentials:")
        print("  Admin:   admin@jobfinder.com / admin123")
        print("  Company: techcorp@example.com / test123")
        print("  Seeker:  alice@example.com   / test123")


if __name__ == '__main__':
    seed()
