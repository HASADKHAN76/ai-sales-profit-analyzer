"""
security.py
Security utilities: encryption, 2FA (TOTP), rate limiting, email sending.
"""

import os
import secrets
import json
import io
import base64
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Optional imports for 2FA (may not be installed)
try:
    import pyotp
    PYOTP_AVAILABLE = True
except ImportError:
    PYOTP_AVAILABLE = False
    pyotp = None

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    qrcode = None

load_dotenv()

# ── Configuration ────────────────────────────────
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@salesapp.com")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8501")

MAX_FAILED_ATTEMPTS = int(os.getenv("MAX_FAILED_ATTEMPTS", "5"))
LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", "30"))
RESET_TOKEN_EXPIRY_HOURS = int(os.getenv("RESET_TOKEN_EXPIRY_HOURS", "1"))


# ── Encryption ───────────────────────────────────

def get_fernet() -> Fernet:
    """Get Fernet instance for encryption/decryption."""
    if not ENCRYPTION_KEY:
        key = Fernet.generate_key()
        print(f"[WARNING] ENCRYPTION_KEY not set. Generated temporary key (add to .env):\n{key.decode()}")
        return Fernet(key)
    return Fernet(ENCRYPTION_KEY.encode())


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a string (e.g., TOTP secret)."""
    return get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt an encrypted string."""
    return get_fernet().decrypt(ciphertext.encode()).decode()


# ── Token Generation ─────────────────────────────

def generate_reset_token() -> str:
    """Generate a secure random token for password reset."""
    return secrets.token_urlsafe(32)


def generate_backup_codes(count: int = 8) -> list[str]:
    """Generate backup codes for 2FA recovery."""
    return [secrets.token_hex(4).upper() for _ in range(count)]


# ── TOTP (2FA) ───────────────────────────────────

def generate_totp_secret() -> str:
    """Generate a new TOTP secret."""
    if not PYOTP_AVAILABLE:
        raise ImportError("pyotp package not installed. Run: pip install pyotp --user --break-system-packages")
    return pyotp.random_base32()


def get_totp_uri(secret: str, username: str, issuer: str = "SalesIQ") -> str:
    """Get provisioning URI for authenticator apps."""
    if not PYOTP_AVAILABLE:
        raise ImportError("pyotp package not installed. Run: pip install pyotp --user --break-system-packages")
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=username, issuer_name=issuer)


def generate_qr_code_base64(uri: str) -> str:
    """Generate QR code as base64 string for display in Streamlit."""
    if not QRCODE_AVAILABLE:
        raise ImportError("qrcode package not installed. Run: pip install qrcode[pil] --user --break-system-packages")
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def verify_totp(secret: str, code: str) -> bool:
    """Verify a TOTP code."""
    if not PYOTP_AVAILABLE:
        raise ImportError("pyotp package not installed. Run: pip install pyotp --user --break-system-packages")
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


# ── Email Sending ────────────────────────────────

def send_password_reset_email(to_email: str, reset_token: str, username: str) -> bool:
    """Send password reset email. Returns True if successful."""
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f"[INFO] Email not configured. Reset link for {username}:")
        print(f"       {APP_BASE_URL}?reset_token={reset_token}")
        return False

    reset_link = f"{APP_BASE_URL}?reset_token={reset_token}"

    subject = "SalesIQ - Password Reset Request"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #0d1526; padding: 20px; text-align: center;">
            <h1 style="color: #e2e8f0; margin: 0;">SalesIQ</h1>
        </div>
        <div style="padding: 30px; background: #f8fafc;">
            <h2 style="color: #1a1a2e;">Password Reset Request</h2>
            <p>Hi {username},</p>
            <p>We received a request to reset your password. Click the button below to proceed:</p>
            <p style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}"
                   style="background: #6366f1; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 6px; font-weight: bold;">
                    Reset Password
                </a>
            </p>
            <p style="color: #64748b; font-size: 14px;">
                This link expires in {RESET_TOKEN_EXPIRY_HOURS} hour(s).<br>
                If you didn't request this, you can safely ignore this email.
            </p>
        </div>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM_EMAIL
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
        return False


# ── Lockout Helpers ──────────────────────────────

def is_account_locked(locked_until: str | None) -> bool:
    """Check if account is currently locked."""
    if not locked_until:
        return False
    try:
        lock_time = datetime.fromisoformat(locked_until.replace("Z", "+00:00"))
        if lock_time.tzinfo is None:
            lock_time = lock_time.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < lock_time
    except ValueError:
        return False


def get_lockout_expiry() -> str:
    """Get the lockout expiry timestamp."""
    return (datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)).isoformat()


def get_reset_token_expiry() -> str:
    """Get the reset token expiry timestamp."""
    return (datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_EXPIRY_HOURS)).isoformat()
