"""
Email Delivery Service for Beyond Identity.

Handles sending real verification emails via SMTP (e.g. Gmail SMTP with App Password).
Designed as an independent, modular service so the delivery mechanism can be
seamlessly updated (e.g., to SendGrid, AWS SES, Resend) without touching routes.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_verification_email(to_email: str, user_name: str, verification_token: str) -> bool:
    """
    Sends an account verification email containing a signed 24-hour verification link.
    
    Parameters:
    - to_email: The recipient's verified @gmail.com address.
    - user_name: The recipient's chosen name.
    - verification_token: A cryptographically signed JWT token.
    
    Returns:
    - True if sent successfully (or mock-printed in dev mode), False if an SMTP error occurred.
    """
    # 1. Build the verification link
    # FRONTEND_URL is loaded from .env (e.g., http://localhost:8000 or http://localhost:5500)
    base_url = (os.getenv("FRONTEND_URL") or "http://localhost:8000").rstrip("/")
    verification_link = f"{base_url}/auth/verify-email?token={verification_token}"

    # 2. Read SMTP credentials from .env
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_APP_PASSWORD", "").strip()
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    # 3. Development / Mock Mode fallback
    # If the student or developer hasn't configured a Gmail App Password yet,
    # log the activation link directly to the console so local testing always works!
    if (
        not smtp_user
        or not smtp_password
        or "your" in smtp_password.lower()
        or "example" in smtp_user.lower()
    ):
        print("\n" + "=" * 72)
        print("[BEYOND IDENTITY EMAIL SERVICE - LOCAL DEV MODE]")
        print(f"Recipient: {user_name} <{to_email}>")
        print("Subject  : Verify your Beyond Identity Account")
        print(f"Link     : {verification_link}")
        print("TIP: To send real emails, set SMTP_USER and SMTP_APP_PASSWORD in .env")
        print("=" * 72 + "\n")
        return True

    # 4. Real SMTP Dispatch via Gmail App Password
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Verify your Beyond Identity Account"
        msg["From"] = f"Beyond Identity <{smtp_user}>"
        msg["To"] = to_email

        # Plain text fallback
        plain_text = (
            f"Namaste {user_name}!\n\n"
            f"Welcome to Beyond Identity — an inclusion and legal rights platform for the transgender community.\n\n"
            f"Please verify your Gmail address by clicking this link:\n{verification_link}\n\n"
            f"This link will expire in 24 hours.\n\n"
            f"If you did not sign up for Beyond Identity, you can safely ignore this email.\n\n"
            f"Warm regards,\nBeyond Identity Team"
        )

        # Responsive HTML email
        html_text = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 24px; }}
    .card {{ max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 18px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.08); }}
    .header {{ background: linear-gradient(135deg, #18153F 0%, #241E5C 100%); padding: 32px 24px; text-align: center; color: #ffffff; }}
    .header h1 {{ margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.02em; }}
    .header p {{ margin: 8px 0 0; color: #cbd5e1; font-size: 13px; font-weight: 500; }}
    .content {{ padding: 32px 28px; color: #1e293b; font-size: 15px; line-height: 1.6; }}
    .btn-wrap {{ text-align: center; margin: 28px 0; }}
    .btn {{ display: inline-block; background: #0F766E; color: #ffffff !important; font-weight: 700; text-decoration: none; padding: 13px 32px; border-radius: 10px; font-size: 15px; box-shadow: 0 4px 12px rgba(15,118,110,0.35); }}
    .subtext {{ font-size: 13px; color: #64748b; margin-top: 24px; line-height: 1.5; }}
    .footer {{ background: #f8fafc; padding: 18px 24px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>🏳️‍⚧️ Beyond Identity</h1>
      <p>Beyond Labels, Everyone Equal</p>
    </div>
    <div class="content">
      <p>🙏 <strong>Namaste {user_name}!</strong></p>
      <p>Thank you for joining <strong>Beyond Identity</strong>. To activate your account and start accessing verified opportunities, healthcare schemes, and crisis support, please verify your Gmail address:</p>
      <div class="btn-wrap">
        <a href="{verification_link}" class="btn" target="_blank">Verify My Gmail Address</a>
      </div>
      <div class="subtext">
        <p>Or paste this URL into your browser:<br/><a href="{verification_link}" style="color: #0F766E; word-break: break-all;">{verification_link}</a></p>
        <p>⏱️ This verification link expires in <strong>24 hours</strong>.</p>
      </div>
    </div>
    <div class="footer">
      If you did not register for an account, please disregard this email.<br/>
      24/7 Community Crisis Helpline: 868989330 • Tele-MANAS: 14416
    </div>
  </div>
</body>
</html>"""

        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(html_text, "html"))

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
            server.starttls()

        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        return True

    except Exception as e:
        print(f"[SMTP ERROR] Could not send email to {to_email}: {e}")
        return False
