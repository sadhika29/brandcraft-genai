import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from app.config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SERVER_HOST
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, html_content: str):
    # Verify SMTP credentials exist
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("=" * 60)
        logger.warning(f"SMTP CREDENTIALS MISSING! SIMULATING EMAIL TO: {to_email}")
        logger.warning(f"SUBJECT: {subject}")
        logger.warning("HTML CONTENT PREVIEW:")
        logger.warning(html_content)
        logger.warning("=" * 60)
        return True

    # Construct email message
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = SMTP_FROM
    message["To"] = to_email
    message.attach(MIMEText(html_content, "html"))

    try:
        # standard SMTP setup
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, to_email, message.as_string())
        server.quit()
        logger.info(f"Email successfully sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email} via SMTP: {e}")
        logger.warning("=" * 60)
        logger.warning("SMTP CONNECTION FAILED. CONSOLE LOG FALLBACK:")
        logger.warning(f"TO: {to_email}")
        logger.warning(f"SUBJECT: {subject}")
        logger.warning("HTML CONTENT PREVIEW:")
        logger.warning(html_content)
        logger.warning("=" * 60)
        return False

def send_verification_email(email: str, name: str, token: str):
    verification_link = f"{SERVER_HOST}/api/auth/verify-email?token={token}"
    subject = "Verify your BrandCraft Account"
    
    html_content = f"""
    <html>
        <body style="font-family: 'Outfit', sans-serif; background-color: #fff0f3; padding: 20px; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #ffe5ec;">
                <h2 style="color: #d81b60; font-weight: 600;">Welcome to BrandCraft, {name}!</h2>
                <p>Thank you for registering. To active your account and begin building your brand identity, please verify your email address by clicking the link below:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_link}" style="background-color: #d81b60; color: white; padding: 12px 25px; border-radius: 8px; text-decoration: none; font-weight: bold; display: inline-block; box-shadow: 0 4px 6px rgba(216, 27, 96, 0.2);">Verify Account</a>
                </div>
                <p style="font-size: 13px; color: #888;">If the button doesn't work, copy and paste this link into your browser:</p>
                <p style="font-size: 13px; color: #d81b60; word-break: break-all;">{verification_link}</p>
                <hr style="border: 0; border-top: 1px solid #ffe5ec; margin: 20px 0;" />
                <p style="font-size: 12px; color: #aaa;">This email was sent automatically by BrandCraft. If you didn't create an account, please ignore this email.</p>
            </div>
        </body>
    </html>
    """
    return send_email(email, subject, html_content)

def send_reset_password_email(email: str, name: str, token: str):
    # The token is sent in the URL which the frontend catches and redirects to a reset form
    reset_link = f"{SERVER_HOST}/#reset-password?token={token}"
    subject = "Reset your BrandCraft Password"
    
    html_content = f"""
    <html>
        <body style="font-family: 'Outfit', sans-serif; background-color: #fff0f3; padding: 20px; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #ffe5ec;">
                <h2 style="color: #d81b60; font-weight: 600;">Reset Password Request</h2>
                <p>Hello {name},</p>
                <p>We received a request to reset your password. Click the button below to choose a new password:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" style="background-color: #d81b60; color: white; padding: 12px 25px; border-radius: 8px; text-decoration: none; font-weight: bold; display: inline-block; box-shadow: 0 4px 6px rgba(216, 27, 96, 0.2);">Reset Password</a>
                </div>
                <p style="font-size: 13px; color: #888;">If the button doesn't work, copy and paste this link into your browser:</p>
                <p style="font-size: 13px; color: #d81b60; word-break: break-all;">{reset_link}</p>
                <hr style="border: 0; border-top: 1px solid #ffe5ec; margin: 20px 0;" />
                <p style="font-size: 12px; color: #aaa;">If you did not request a password reset, please ignore this email.</p>
            </div>
        </body>
    </html>
    """
    return send_email(email, subject, html_content)
