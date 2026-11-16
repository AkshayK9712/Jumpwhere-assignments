import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.core.security import create_email_token

logger = logging.getLogger(__name__)

# Used by the "memory" backend so tests can read the "sent" emails.
OUTBOX: list[dict] = []


def send_email(to: str, subject: str, body: str) -> None:
    backend = settings.EMAIL_BACKEND
    if backend == "memory":
        OUTBOX.append({"to": to, "subject": subject, "body": body})
        return
    if backend == "smtp":
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = settings.EMAIL_FROM, to, subject
        msg.set_content(body)
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
                if settings.SMTP_USE_TLS:
                    smtp.starttls()
                if settings.SMTP_USER:
                    smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                smtp.send_message(msg)
        except Exception:  # never fail a request because the mail server is down
            logger.exception("Could not send email to %s", to)
        return
    # console backend (development only: the log contains the verification link)
    logger.info("EMAIL (console backend)\nTo: %s\nSubject: %s\n\n%s", to, subject, body)


def verification_link(token: str) -> str:
    # Opens the frontend page, which then calls GET /api/v1/auth/verify-email
    return f"{settings.API_BASE_URL.rstrip('/')}/ui/#/verify?token={token}"


def send_verification_email(user_id: int, email: str, name: str) -> None:
    token = create_email_token(user_id, "verify")
    send_email(
        to=email,
        subject="Verify your IoT Monitor account",
        body=(
            f"Hi {name},\n\n"
            "Please confirm your email address to activate your account:\n\n"
            f"{verification_link(token)}\n\n"
            f"This link expires in {settings.VERIFY_TOKEN_EXPIRE_HOURS} hours.\n"
            "If you did not sign up, you can ignore this email.\n"
        ),
    )


def send_report_ready_email(to: str, name: str, report_name: str) -> None:
    send_email(
        to=to,
        subject=f"Your report is ready: {report_name}",
        body=(
            f"Hi {name},\n\n"
            f'Your scheduled report "{report_name}" has been generated.\n'
            f"Open it here (login required): {settings.API_BASE_URL.rstrip('/')}/ui/#/reports\n"
        ),
    )
