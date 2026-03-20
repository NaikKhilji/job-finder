"""
Email utility – wraps Flask-Mail with a safe fallback.

If MAIL_USERNAME is not set in the environment the function prints to the
Flask logger instead of crashing, so the app keeps running during development.
"""
from flask import current_app
from flask_mail import Message
from extensions import mail


# ─────────────────────────────────────────────────────────────────────────────
# Internal helper
# ─────────────────────────────────────────────────────────────────────────────

def _send(subject: str, recipients: list, html: str, text: str = ""):
    """
    Send an email.
    Returns True on success, False if unconfigured or on error.
    When unconfigured, the subject + first 300 chars of the body are logged
    so developers can see what *would* have been sent.
    """
    if not current_app.config.get("MAIL_USERNAME"):
        current_app.logger.warning(
            "[EMAIL – no SMTP configured] "
            f"To: {recipients} | Subject: {subject}\n"
            f"Body preview: {(text or html)[:300]}"
        )
        return False
    try:
        msg = Message(
            subject=subject,
            recipients=recipients,
            html=html,
            body=text or "Please view this email in an HTML-capable client.",
        )
        mail.send(msg)
        return True
    except Exception as exc:
        current_app.logger.error(f"Email send failed: {exc}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Auth emails
# ─────────────────────────────────────────────────────────────────────────────

def send_otp_email(to_email: str, otp: str, name: str = "") -> bool:
    greeting = f"Hi {name}," if name else "Hello,"
    html = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px;background:#f8fafc;border-radius:12px;">
      <div style="text-align:center;margin-bottom:24px;">
        <h2 style="color:#2563eb;margin:0;">&#128274; Password Reset OTP</h2>
      </div>
      <p style="color:#374151;">{greeting}</p>
      <p style="color:#374151;">You requested a password reset for your <strong>JobFinder</strong> account.
         Use the OTP below to verify your identity.</p>
      <div style="background:#ffffff;border:2px dashed #2563eb;border-radius:10px;
                  text-align:center;padding:20px 0;margin:24px 0;">
        <span style="font-size:2.5rem;font-weight:900;letter-spacing:0.6rem;color:#0f172a;">{otp}</span>
      </div>
      <p style="color:#6b7280;font-size:0.875rem;">
        &#8987; This OTP expires in <strong>10 minutes</strong>.<br>
        If you did not request this, ignore this email — your account is safe.
      </p>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
      <p style="color:#9ca3af;font-size:0.75rem;text-align:center;">
        JobFinder &mdash; Find Your Dream Job
      </p>
    </div>
    """
    text = f"{greeting}\n\nYour JobFinder password reset OTP is: {otp}\n\nIt expires in 10 minutes."
    return _send("Your JobFinder Password Reset OTP", [to_email], html, text)


# ─────────────────────────────────────────────────────────────────────────────
# Newsletter emails
# ─────────────────────────────────────────────────────────────────────────────

def send_newsletter_confirmation(to_email: str) -> bool:
    html = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px;background:#f8fafc;border-radius:12px;">
      <div style="text-align:center;margin-bottom:24px;">
        <h2 style="color:#2563eb;margin:0;">&#127881; Welcome to JobFinder Alerts!</h2>
      </div>
      <p style="color:#374151;">Hi there,</p>
      <p style="color:#374151;">
        You're now subscribed to <strong>JobFinder</strong> job alerts.
        We'll send you the latest job openings that match your interests directly to
        <strong>{to_email}</strong>.
      </p>
      <div style="background:#eff6ff;border-left:4px solid #2563eb;padding:14px 18px;border-radius:6px;margin:20px 0;">
        <p style="margin:0;color:#1d4ed8;font-weight:600;">What to expect:</p>
        <ul style="color:#374151;margin:8px 0 0;padding-left:18px;">
          <li>Weekly job digest with top openings</li>
          <li>Instant alerts for high-demand roles</li>
          <li>Tips to improve your job search</li>
        </ul>
      </div>
      <p style="color:#6b7280;font-size:0.875rem;">
        To unsubscribe at any time, reply to this email with "Unsubscribe".
      </p>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
      <p style="color:#9ca3af;font-size:0.75rem;text-align:center;">
        JobFinder &mdash; Find Your Dream Job
      </p>
    </div>
    """
    text = f"Welcome to JobFinder Alerts!\n\nYou've subscribed to job alerts at {to_email}."
    return _send("Welcome to JobFinder Job Alerts!", [to_email], html, text)


# ─────────────────────────────────────────────────────────────────────────────
# Application notification emails
# ─────────────────────────────────────────────────────────────────────────────

def send_application_to_company(company_email: str, company_name: str,
                                 job_title: str, applicant_name: str,
                                 applicant_email: str, cover_letter: str,
                                 applicants_url: str) -> bool:
    snippet = (cover_letter[:250] + "…") if len(cover_letter) > 250 else cover_letter
    html = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:520px;margin:0 auto;padding:24px;background:#f8fafc;border-radius:12px;">
      <div style="text-align:center;margin-bottom:24px;">
        <h2 style="color:#2563eb;margin:0;">&#128221; New Application Received</h2>
      </div>
      <p style="color:#374151;">Hi <strong>{company_name}</strong>,</p>
      <p style="color:#374151;">
        <strong>{applicant_name}</strong> has applied for your job posting
        <strong>"{job_title}"</strong>.
      </p>
      <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin:20px 0;">
        <p style="margin:0 0 6px;color:#374151;"><strong>Applicant:</strong> {applicant_name}</p>
        <p style="margin:0 0 6px;color:#374151;"><strong>Email:</strong> {applicant_email}</p>
        {"<p style='margin:0;color:#374151;'><strong>Cover Letter:</strong><br>" + snippet + "</p>" if snippet else ""}
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{applicants_url}"
           style="background:#2563eb;color:white;text-decoration:none;padding:12px 28px;
                  border-radius:8px;font-weight:600;display:inline-block;">
          View All Applicants
        </a>
      </div>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
      <p style="color:#9ca3af;font-size:0.75rem;text-align:center;">
        JobFinder &mdash; Find Your Dream Job
      </p>
    </div>
    """
    text = (f"Hi {company_name},\n\n{applicant_name} ({applicant_email}) applied for '{job_title}'.\n\n"
            f"Cover letter:\n{cover_letter}\n\nView applicants: {applicants_url}")
    return _send(f"New Application for '{job_title}'", [company_email], html, text)


def send_application_status_to_seeker(seeker_email: str, seeker_name: str,
                                       job_title: str, company_name: str,
                                       status: str, jobs_url: str) -> bool:
    is_accepted = status == "Accepted"
    color = "#16a34a" if is_accepted else "#dc2626"
    icon = "&#9989;" if is_accepted else "&#10060;"
    headline = "Congratulations! You've been accepted!" if is_accepted else "Application Update"
    message = (
        f"Great news! <strong>{company_name}</strong> has reviewed your application for "
        f"<strong>'{job_title}'</strong> and <strong style='color:{color};'>accepted</strong> it. "
        "They will be in touch with you shortly."
        if is_accepted else
        f"Thank you for your interest. After careful review, <strong>{company_name}</strong> has decided "
        f"not to move forward with your application for <strong>'{job_title}'</strong> at this time. "
        "Don't be discouraged — keep applying!"
    )
    html = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:520px;margin:0 auto;padding:24px;background:#f8fafc;border-radius:12px;">
      <div style="text-align:center;margin-bottom:24px;">
        <h2 style="color:{color};margin:0;">{icon} {headline}</h2>
      </div>
      <p style="color:#374151;">Hi <strong>{seeker_name}</strong>,</p>
      <p style="color:#374151;">{message}</p>
      <div style="text-align:center;margin:24px 0;">
        <a href="{jobs_url}"
           style="background:#2563eb;color:white;text-decoration:none;padding:12px 28px;
                  border-radius:8px;font-weight:600;display:inline-block;">
          Browse More Jobs
        </a>
      </div>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
      <p style="color:#9ca3af;font-size:0.75rem;text-align:center;">
        JobFinder &mdash; Find Your Dream Job
      </p>
    </div>
    """
    text = f"Hi {seeker_name},\n\nYour application for '{job_title}' at {company_name} has been {status}."
    subject = (f"Accepted: '{job_title}' at {company_name}" if is_accepted
               else f"Application Update: '{job_title}' at {company_name}")
    return _send(subject, [seeker_email], html, text)


# ─────────────────────────────────────────────────────────────────────────────
# Admin / company notification emails
# ─────────────────────────────────────────────────────────────────────────────

def send_new_job_to_admin(admin_email: str, job_title: str, company_name: str,
                           admin_jobs_url: str) -> bool:
    html = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:520px;margin:0 auto;padding:24px;background:#f8fafc;border-radius:12px;">
      <div style="text-align:center;margin-bottom:24px;">
        <h2 style="color:#f59e0b;margin:0;">&#128338; Job Pending Approval</h2>
      </div>
      <p style="color:#374151;">Hi Admin,</p>
      <p style="color:#374151;">
        <strong>{company_name}</strong> has posted a new job titled
        <strong>"{job_title}"</strong> that requires your approval before going live.
      </p>
      <div style="text-align:center;margin:24px 0;">
        <a href="{admin_jobs_url}"
           style="background:#f59e0b;color:white;text-decoration:none;padding:12px 28px;
                  border-radius:8px;font-weight:600;display:inline-block;">
          Review Job Postings
        </a>
      </div>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
      <p style="color:#9ca3af;font-size:0.75rem;text-align:center;">
        JobFinder Admin Panel
      </p>
    </div>
    """
    text = (f"Hi Admin,\n\n{company_name} posted '{job_title}' — review it here: {admin_jobs_url}")
    return _send(f"[Action Required] New Job Pending: '{job_title}'", [admin_email], html, text)


def send_job_decision_to_company(company_email: str, company_name: str,
                                  job_title: str, approved: bool,
                                  my_jobs_url: str) -> bool:
    color = "#16a34a" if approved else "#dc2626"
    icon = "&#9989;" if approved else "&#10060;"
    status_word = "Approved & Published" if approved else "Rejected"
    msg = (
        f"Your job posting <strong>'{job_title}'</strong> has been "
        f"<strong style='color:{color};'>approved</strong> and is now live on JobFinder!"
        if approved else
        f"Unfortunately your job posting <strong>'{job_title}'</strong> did not meet our guidelines "
        "and has been <strong style='color:#dc2626;'>rejected</strong>. "
        "Please review our posting guidelines and try again."
    )
    html = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:520px;margin:0 auto;padding:24px;background:#f8fafc;border-radius:12px;">
      <div style="text-align:center;margin-bottom:24px;">
        <h2 style="color:{color};margin:0;">{icon} Job {status_word}</h2>
      </div>
      <p style="color:#374151;">Hi <strong>{company_name}</strong>,</p>
      <p style="color:#374151;">{msg}</p>
      <div style="text-align:center;margin:24px 0;">
        <a href="{my_jobs_url}"
           style="background:#2563eb;color:white;text-decoration:none;padding:12px 28px;
                  border-radius:8px;font-weight:600;display:inline-block;">
          View My Jobs
        </a>
      </div>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
      <p style="color:#9ca3af;font-size:0.75rem;text-align:center;">
        JobFinder &mdash; Find Your Dream Job
      </p>
    </div>
    """
    text = f"Hi {company_name},\n\nYour job '{job_title}' has been {status_word}."
    subject = f"Job {status_word}: '{job_title}'"
    return _send(subject, [company_email], html, text)


def send_contact_to_admin(admin_email: str, sender_name: str,
                           sender_email: str, subject: str, message: str) -> bool:
    html = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:520px;margin:0 auto;padding:24px;background:#f8fafc;border-radius:12px;">
      <h2 style="color:#2563eb;">&#128140; Contact Form Message</h2>
      <p style="color:#374151;"><strong>From:</strong> {sender_name} ({sender_email})</p>
      <p style="color:#374151;"><strong>Subject:</strong> {subject}</p>
      <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin:16px 0;">
        <p style="color:#374151;white-space:pre-wrap;margin:0;">{message}</p>
      </div>
      <p style="color:#6b7280;font-size:0.875rem;">Reply to: <a href="mailto:{sender_email}">{sender_email}</a></p>
    </div>
    """
    text = f"From: {sender_name} ({sender_email})\nSubject: {subject}\n\n{message}"
    return _send(f"[Contact] {subject} – from {sender_name}", [admin_email], html, text)


def send_job_alert_email(to_email: str, user_name: str, jobs: list, alerts_url: str) -> bool:
    """Send digest of matching jobs to a job alert subscriber."""
    jobs_html = ''
    for job in jobs:
        jobs_html += f"""
        <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin-bottom:12px;">
          <h3 style="margin:0 0 4px;color:#1e40af;font-size:1rem;">{job['title']}</h3>
          <p style="margin:0 0 4px;color:#374151;">{job['company']} &mdash; {job['location']}</p>
          <p style="margin:0 0 8px;color:#6b7280;font-size:0.875rem;">{job['job_type']} &bull; {job['salary']}</p>
          <a href="{job['url']}" style="background:#2563eb;color:white;text-decoration:none;padding:8px 16px;border-radius:6px;font-size:0.875rem;font-weight:600;">View Job</a>
        </div>"""
    html = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:24px;background:#f8fafc;border-radius:12px;">
      <div style="text-align:center;margin-bottom:24px;">
        <h2 style="color:#2563eb;margin:0;">&#128276; New Jobs Matching Your Alerts</h2>
      </div>
      <p style="color:#374151;">Hi {user_name},</p>
      <p style="color:#374151;">We found <strong>{len(jobs)} new job(s)</strong> matching your saved alerts:</p>
      {jobs_html}
      <div style="text-align:center;margin:24px 0;">
        <a href="{alerts_url}" style="background:#2563eb;color:white;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;display:inline-block;">Manage Alerts</a>
      </div>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
      <p style="color:#9ca3af;font-size:0.75rem;text-align:center;">JobFinder &mdash; Find Your Dream Job</p>
    </div>
    """
    text = f"Hi {user_name},\n\n{len(jobs)} new job(s) match your alerts."
    return _send("New Jobs Matching Your Alerts — JobFinder", [to_email], html, text)


def send_interview_scheduled(seeker_email: str, seeker_name: str, job_title: str,
                               company_name: str, scheduled_at: str, interview_type: str,
                               location_or_link: str, notes: str) -> bool:
    """Notify job seeker that an interview has been scheduled."""
    link_html = f'<p style="color:#374151;"><strong>Link/Location:</strong> <a href="{location_or_link}">{location_or_link}</a></p>' if location_or_link else ''
    notes_html = f'<p style="color:#374151;"><strong>Notes:</strong> {notes}</p>' if notes else ''
    html = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:520px;margin:0 auto;padding:24px;background:#f8fafc;border-radius:12px;">
      <div style="text-align:center;margin-bottom:24px;">
        <h2 style="color:#16a34a;margin:0;">&#127881; Interview Scheduled!</h2>
      </div>
      <p style="color:#374151;">Hi {seeker_name},</p>
      <p style="color:#374151;">Great news! <strong>{company_name}</strong> has scheduled an interview for <strong>{job_title}</strong>.</p>
      <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:16px;margin:16px 0;">
        <p style="color:#374151;margin:0 0 8px;"><strong>&#128197; Date &amp; Time:</strong> {scheduled_at}</p>
        <p style="color:#374151;margin:0 0 8px;"><strong>&#128222; Type:</strong> {interview_type}</p>
        {link_html}
        {notes_html}
      </div>
      <p style="color:#6b7280;font-size:0.875rem;">Make sure to be on time and prepare well. Best of luck!</p>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
      <p style="color:#9ca3af;font-size:0.75rem;text-align:center;">JobFinder &mdash; Find Your Dream Job</p>
    </div>
    """
    text = f"Hi {seeker_name},\n\nAn interview has been scheduled for {job_title} at {company_name}.\nDate: {scheduled_at}\nType: {interview_type}"
    return _send(f"Interview Scheduled: {job_title} at {company_name}", [seeker_email], html, text)

