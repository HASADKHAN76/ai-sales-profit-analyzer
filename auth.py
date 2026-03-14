"""
auth.py
Authentication module - login, register, JWT tokens, password hashing, 2FA.
"""

import os
import re
import json
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv

import database as db
import security as sec

load_dotenv()

# Secret key for JWT - generate once and store in .env for production
JWT_SECRET = os.getenv("JWT_SECRET", "sales-app-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

# File upload validation
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
MAX_FILE_SIZE_MB = 50


# ── Password Hashing ────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT Tokens ───────────────────────────────────

def create_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ── Validation ───────────────────────────────────

def validate_username(username: str) -> str | None:
    """Return error message or None if valid."""
    if not username or len(username) < 3:
        return "Username must be at least 3 characters."
    if len(username) > 30:
        return "Username must be at most 30 characters."
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return "Username can only contain letters, numbers, and underscores."
    return None


def validate_email(email: str) -> str | None:
    if not email or not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return "Please enter a valid email address."
    return None


def validate_password(password: str) -> str | None:
    if not password or len(password) < 6:
        return "Password must be at least 6 characters."
    if len(password) > 128:
        return "Password must be at most 128 characters."
    return None


def validate_file(filename: str, file_size: int) -> str | None:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        return f"File too large. Maximum size: {MAX_FILE_SIZE_MB} MB."
    return None


# ── Auth Operations ──────────────────────────────

def register(username: str, email: str, password: str, role: str = "user") -> tuple[bool, str]:
    """Register a new user. Returns (success, message)."""
    # Validate inputs
    err = validate_username(username)
    if err:
        return False, err
    err = validate_email(email)
    if err:
        return False, err
    err = validate_password(password)
    if err:
        return False, err

    # Check duplicates
    if db.get_user_by_username(username):
        return False, "Username already taken."
    if db.get_user_by_email(email):
        return False, "Email already registered."

    # Create user
    hashed = hash_password(password)
    user_id = db.create_user(username, email, hashed, role)
    return True, f"Account created successfully! Welcome, {username}."


def login(username: str, password: str, totp_code: str = None) -> tuple[bool, str, str | None, bool]:
    """
    Login user.
    Returns (success, message, token_or_none, requires_2fa).
    """
    if not username or not password:
        return False, "Please enter both username and password.", None, False

    user = db.get_user_by_username(username)
    if not user:
        return False, "Invalid username or password.", None, False

    # Check if account is locked
    if sec.is_account_locked(user.get("locked_until")):
        remaining = _get_lockout_remaining(user["locked_until"])
        return False, f"Account locked. Try again in {remaining}.", None, False

    if not user["is_active"]:
        return False, "Your account has been deactivated. Contact admin.", None, False

    if not verify_password(password, user["password"]):
        failed_count = db.increment_failed_attempts(user["id"])
        db.log_login(user["id"], success=False)

        # Check if should lock account
        if failed_count >= sec.MAX_FAILED_ATTEMPTS:
            lockout_expiry = sec.get_lockout_expiry()
            db.lock_account(user["id"], lockout_expiry)
            return False, f"Too many failed attempts. Account locked for {sec.LOCKOUT_DURATION_MINUTES} minutes.", None, False

        remaining = sec.MAX_FAILED_ATTEMPTS - failed_count
        return False, f"Invalid username or password. {remaining} attempts remaining.", None, False

    # Check if 2FA is required
    user_2fa = db.get_user_2fa(user["id"])
    if user_2fa and user_2fa["is_enabled"]:
        if not totp_code:
            return True, "2FA required", None, True

        # Verify TOTP code
        decrypted_secret = sec.decrypt_secret(user_2fa["secret"])
        if not sec.verify_totp(decrypted_secret, totp_code):
            # Check backup codes
            if not _verify_backup_code(user["id"], user_2fa, totp_code):
                db.log_login(user["id"], success=False)
                return False, "Invalid 2FA code.", None, False

    # Success - reset failed attempts
    db.reset_failed_attempts(user["id"])
    db.update_last_login(user["id"])
    db.log_login(user["id"], success=True)
    token = create_token(user["id"], user["username"], user["role"])
    return True, f"Welcome back, {user['username']}!", token, False


def _get_lockout_remaining(locked_until: str) -> str:
    """Get human-readable remaining lockout time."""
    try:
        lock_time = datetime.fromisoformat(locked_until.replace("Z", "+00:00"))
        if lock_time.tzinfo is None:
            lock_time = lock_time.replace(tzinfo=timezone.utc)
        remaining = lock_time - datetime.now(timezone.utc)
        minutes = int(remaining.total_seconds() / 60)
        if minutes < 1:
            return "less than a minute"
        return f"{minutes} minute(s)"
    except ValueError:
        return "some time"


def _verify_backup_code(user_id: int, user_2fa: dict, code: str) -> bool:
    """Verify and consume a backup code."""
    if not user_2fa.get("backup_codes"):
        return False

    backup_codes = json.loads(user_2fa["backup_codes"])
    code_upper = code.upper().replace("-", "").replace(" ", "")

    for stored_hash in backup_codes:
        if verify_password(code_upper, stored_hash):
            backup_codes.remove(stored_hash)
            db.use_backup_code(user_id, json.dumps(backup_codes))
            return True
    return False


def get_current_user(token: str) -> dict | None:
    """Decode token and return user dict, or None if invalid."""
    payload = decode_token(token)
    if not payload:
        return None
    user = db.get_user_by_id(payload["user_id"])
    if not user or not user["is_active"]:
        return None
    return user


def is_admin(user: dict) -> bool:
    return user.get("role") == "admin"


def ensure_default_admin():
    """Create a default admin account if no admins exist."""
    with db.get_db() as conn:
        admin = conn.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1").fetchone()
        if not admin:
            register("admin", "admin@salesapp.com", "admin123", role="admin")
            print("Default admin created: admin / admin123")


# ── Password Reset ───────────────────────────────

def request_password_reset(email: str) -> tuple[bool, str]:
    """
    Initiate password reset. Returns (success, message).
    Always returns success message to prevent email enumeration.
    """
    user = db.get_user_by_email(email)
    if not user:
        return True, "If an account exists with this email, you will receive reset instructions."

    token = sec.generate_reset_token()
    expires_at = sec.get_reset_token_expiry()

    db.create_password_reset_token(user["id"], token, expires_at)
    sec.send_password_reset_email(user["email"], token, user["username"])

    return True, "If an account exists with this email, you will receive reset instructions."


def reset_password(token: str, new_password: str) -> tuple[bool, str]:
    """Reset password using token. Returns (success, message)."""
    reset_record = db.get_password_reset_token(token)

    if not reset_record:
        return False, "Invalid or expired reset link."

    # Check expiry
    try:
        expires_at = datetime.fromisoformat(reset_record["expires_at"].replace("Z", "+00:00"))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            return False, "Reset link has expired. Please request a new one."
    except ValueError:
        return False, "Invalid reset token."

    # Validate new password
    err = validate_password(new_password)
    if err:
        return False, err

    # Update password
    hashed = hash_password(new_password)
    db.update_user_password(reset_record["user_id"], hashed)
    db.mark_reset_token_used(token)

    # Also reset any lockout
    db.unlock_account(reset_record["user_id"])

    return True, "Password reset successfully. You can now log in."


# ── Password Change (Logged-in User) ─────────────

def change_password(user_id: int, current_password: str, new_password: str) -> tuple[bool, str]:
    """Change password for logged-in user. Returns (success, message)."""
    user = db.get_user_by_id(user_id)
    if not user:
        return False, "User not found."

    # Verify current password
    if not verify_password(current_password, user["password"]):
        return False, "Current password is incorrect."

    # Validate new password
    err = validate_password(new_password)
    if err:
        return False, err

    # Check new password is different
    if verify_password(new_password, user["password"]):
        return False, "New password must be different from current password."

    # Update password
    hashed = hash_password(new_password)
    db.update_user_password(user_id, hashed)

    return True, "Password changed successfully."


def validate_password_strength(password: str) -> tuple[bool, str, int]:
    """
    Enhanced password validation with strength score.
    Returns (is_valid, message, strength_score 0-100).
    """
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters.", 0

    score = 0
    feedback = []

    # Length scoring
    if len(password) >= 8:
        score += 20
    if len(password) >= 12:
        score += 10

    # Character variety
    if any(c.islower() for c in password):
        score += 15
    else:
        feedback.append("lowercase letter")

    if any(c.isupper() for c in password):
        score += 15
    else:
        feedback.append("uppercase letter")

    if any(c.isdigit() for c in password):
        score += 20
    else:
        feedback.append("number")

    if any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in password):
        score += 20
    else:
        feedback.append("special character")

    message = "Strong password!" if score >= 70 else f"Consider adding: {', '.join(feedback)}"
    return True, message, score


# ── 2FA Setup ────────────────────────────────────

def setup_2fa(user_id: int) -> tuple[str, str, list[str]]:
    """
    Initialize 2FA setup for user.
    Returns (qr_code_base64, secret, backup_codes).
    """
    user = db.get_user_by_id(user_id)
    if not user:
        raise ValueError("User not found")

    # Generate secret and backup codes
    secret = sec.generate_totp_secret()
    backup_codes = sec.generate_backup_codes(8)

    # Encrypt secret for storage
    encrypted_secret = sec.encrypt_secret(secret)

    # Hash backup codes for storage
    hashed_codes = [hash_password(code) for code in backup_codes]

    # Store in database (not enabled yet)
    db.create_2fa_setup(user_id, encrypted_secret, json.dumps(hashed_codes))

    # Generate QR code
    uri = sec.get_totp_uri(secret, user["username"])
    qr_base64 = sec.generate_qr_code_base64(uri)

    return qr_base64, secret, backup_codes


def verify_and_enable_2fa(user_id: int, code: str) -> tuple[bool, str]:
    """Verify TOTP code and enable 2FA. Returns (success, message)."""
    user_2fa = db.get_user_2fa(user_id)
    if not user_2fa:
        return False, "2FA not initialized. Please start setup again."

    if user_2fa["is_enabled"]:
        return False, "2FA is already enabled."

    decrypted_secret = sec.decrypt_secret(user_2fa["secret"])
    if sec.verify_totp(decrypted_secret, code):
        db.enable_2fa(user_id)
        return True, "2FA enabled successfully!"

    return False, "Invalid code. Please try again."


def disable_2fa_for_user(user_id: int, admin_id: int = None) -> tuple[bool, str]:
    """Disable 2FA for a user. Returns (success, message)."""
    user_2fa = db.get_user_2fa(user_id)
    if not user_2fa or not user_2fa["is_enabled"]:
        return False, "2FA is not enabled for this user."

    db.disable_2fa(user_id)
    return True, "2FA disabled successfully."


def has_2fa_enabled(user_id: int) -> bool:
    """Check if user has 2FA enabled."""
    user_2fa = db.get_user_2fa(user_id)
    return bool(user_2fa and user_2fa["is_enabled"])


# Create default admin on import
ensure_default_admin()
