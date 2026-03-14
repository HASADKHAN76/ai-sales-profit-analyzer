"""
database.py
SQLite database for user management, datasets, and AI usage tracking.
"""

import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "sales_app.db")


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    UNIQUE NOT NULL,
            email       TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            role        TEXT    NOT NULL DEFAULT 'user',
            is_active   INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            last_login  TEXT
        );

        CREATE TABLE IF NOT EXISTS datasets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            filename    TEXT    NOT NULL,
            row_count   INTEGER NOT NULL DEFAULT 0,
            file_size   INTEGER NOT NULL DEFAULT 0,
            uploaded_at TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ai_requests (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            provider    TEXT    NOT NULL,
            question    TEXT    NOT NULL,
            tokens_used INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS login_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            ip_address  TEXT,
            success     INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            token       TEXT    UNIQUE NOT NULL,
            expires_at  TEXT    NOT NULL,
            used        INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_2fa (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER UNIQUE NOT NULL,
            secret          TEXT    NOT NULL,
            is_enabled      INTEGER NOT NULL DEFAULT 0,
            backup_codes    TEXT,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS account_lockouts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            locked_until    TEXT    NOT NULL,
            reason          TEXT    DEFAULT 'failed_attempts',
            unlocked_by     INTEGER,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (unlocked_by) REFERENCES users(id) ON DELETE SET NULL
        );

        -- ══════════════════════════════════════════════════════════════════════════════
        -- MULTI-BUSINESS PLATFORM TABLES
        -- ══════════════════════════════════════════════════════════════════════════════

        CREATE TABLE IF NOT EXISTS businesses (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL,
            business_type   TEXT    NOT NULL CHECK (business_type IN ('retail', 'gym', 'coaching', 'service')),
            description     TEXT,
            address         TEXT,
            phone           TEXT,
            email           TEXT,
            owner_id        INTEGER NOT NULL,
            is_active       INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS business_users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id     INTEGER NOT NULL,
            user_id         INTEGER NOT NULL,
            role            TEXT    NOT NULL CHECK (role IN ('owner', 'admin', 'staff')),
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE (business_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS products_services (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id     INTEGER NOT NULL,
            name            TEXT    NOT NULL,
            type            TEXT    NOT NULL CHECK (type IN ('product', 'service')),
            price           REAL    NOT NULL CHECK (price >= 0),
            cost            REAL    NOT NULL DEFAULT 0 CHECK (cost >= 0),
            stock_quantity  INTEGER DEFAULT NULL,  -- NULL for services
            min_stock_level INTEGER DEFAULT 5,     -- Alert threshold
            duration_days   INTEGER DEFAULT NULL,  -- For memberships/subscriptions
            description     TEXT,
            category        TEXT,
            sku             TEXT,
            is_active       INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id         INTEGER NOT NULL,
            product_service_id  INTEGER NOT NULL,
            user_id             INTEGER NOT NULL,  -- Staff who recorded the sale
            customer_name       TEXT,
            customer_email      TEXT,
            customer_phone      TEXT,
            quantity            INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
            unit_price          REAL    NOT NULL CHECK (unit_price >= 0),
            unit_cost           REAL    NOT NULL DEFAULT 0 CHECK (unit_cost >= 0),
            total_amount        REAL    NOT NULL CHECK (total_amount >= 0),
            payment_method      TEXT    NOT NULL CHECK (payment_method IN ('cash', 'card', 'digital', 'bank_transfer', 'check')),
            notes               TEXT,
            transaction_date    TEXT    NOT NULL DEFAULT (datetime('now')),
            created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
            FOREIGN KEY (product_service_id) REFERENCES products_services(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS inventory_alerts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id     INTEGER NOT NULL,
            product_id      INTEGER NOT NULL,
            alert_type      TEXT    NOT NULL CHECK (alert_type IN ('low_stock', 'out_of_stock')),
            current_stock   INTEGER NOT NULL,
            threshold       INTEGER NOT NULL,
            is_resolved     INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            resolved_at     TEXT,
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products_services(id) ON DELETE CASCADE
        );

        -- ══════════════════════════════════════════════════════════════════════════════
        -- GYM-SPECIFIC TABLES
        -- ══════════════════════════════════════════════════════════════════════════════

        CREATE TABLE IF NOT EXISTS gym_members (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id     INTEGER NOT NULL,
            member_id       TEXT    NOT NULL,  -- Custom member ID (e.g. GYM001)
            first_name      TEXT    NOT NULL,
            last_name       TEXT    NOT NULL,
            email           TEXT,
            phone           TEXT,
            joining_date    TEXT,
            emergency_contact_name  TEXT,
            emergency_contact_phone TEXT,
            medical_conditions TEXT,
            photo_url       TEXT,
            is_active       INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
            UNIQUE (business_id, member_id)
        );

        CREATE TABLE IF NOT EXISTS gym_memberships (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id     INTEGER NOT NULL,
            member_id       INTEGER NOT NULL,
            membership_type_id INTEGER NOT NULL,  -- Links to products_services table
            start_date      TEXT    NOT NULL,
            end_date        TEXT    NOT NULL,
            amount_paid     REAL    NOT NULL,
            payment_method  TEXT    NOT NULL CHECK (payment_method IN ('cash', 'card', 'digital', 'bank_transfer', 'check')),
            is_active       INTEGER NOT NULL DEFAULT 1,
            created_by      INTEGER NOT NULL,  -- Staff who created membership
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
            FOREIGN KEY (member_id) REFERENCES gym_members(id) ON DELETE CASCADE,
            FOREIGN KEY (membership_type_id) REFERENCES products_services(id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gym_check_ins (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id     INTEGER NOT NULL,
            member_id       INTEGER NOT NULL,
            check_in_time   TEXT    NOT NULL DEFAULT (datetime('now')),
            check_out_time  TEXT,
            entry_type      TEXT    NOT NULL CHECK (entry_type IN ('membership', 'day_pass', 'guest', 'trial')),
            amount_paid     REAL    DEFAULT 0,  -- For day passes
            payment_method  TEXT    CHECK (payment_method IN ('cash', 'card', 'digital', 'bank_transfer', 'free')),
            checked_in_by   INTEGER NOT NULL,  -- Staff who processed check-in
            notes           TEXT,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
            FOREIGN KEY (member_id) REFERENCES gym_members(id) ON DELETE CASCADE,
            FOREIGN KEY (checked_in_by) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gym_equipment (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id     INTEGER NOT NULL,
            equipment_name  TEXT    NOT NULL,
            equipment_type  TEXT    NOT NULL,  -- cardio, strength, functional, etc.
            brand           TEXT,
            model           TEXT,
            serial_number   TEXT,
            purchase_date   TEXT,
            warranty_expiry TEXT,
            last_maintenance TEXT,
            next_maintenance TEXT,
            maintenance_notes TEXT,
            is_operational  INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gym_classes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id     INTEGER NOT NULL,
            class_name      TEXT    NOT NULL,
            instructor_name TEXT    NOT NULL,
            class_date      TEXT    NOT NULL,
            start_time      TEXT    NOT NULL,
            end_time        TEXT    NOT NULL,
            max_capacity    INTEGER DEFAULT 20,
            current_bookings INTEGER DEFAULT 0,
            price           REAL    DEFAULT 0,
            description     TEXT,
            is_active       INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS gym_class_bookings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id     INTEGER NOT NULL,
            class_id        INTEGER NOT NULL,
            member_id       INTEGER NOT NULL,
            booking_time    TEXT    NOT NULL DEFAULT (datetime('now')),
            attended        INTEGER NOT NULL DEFAULT 0,
            amount_paid     REAL    DEFAULT 0,
            payment_method  TEXT    CHECK (payment_method IN ('cash', 'card', 'digital', 'bank_transfer', 'membership')),
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
            FOREIGN KEY (class_id) REFERENCES gym_classes(id) ON DELETE CASCADE,
            FOREIGN KEY (member_id) REFERENCES gym_members(id) ON DELETE CASCADE,
            UNIQUE (class_id, member_id)
        );

        -- ══════════════════════════════════════════════════════════════════════════════
        -- COACHING-SPECIFIC TABLES
        -- ══════════════════════════════════════════════════════════════════════════════

        CREATE TABLE IF NOT EXISTS coaching_students (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id     INTEGER NOT NULL,
            student_code    TEXT    NOT NULL,
            first_name      TEXT    NOT NULL,
            last_name       TEXT    NOT NULL,
            email           TEXT,
            phone           TEXT,
            guardian_name   TEXT,
            joined_on       TEXT    NOT NULL DEFAULT (date('now')),
            is_active       INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
            UNIQUE (business_id, student_code)
        );

        CREATE TABLE IF NOT EXISTS coaching_courses (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id     INTEGER NOT NULL,
            course_name     TEXT    NOT NULL,
            instructor_name TEXT,
            monthly_fee     REAL    NOT NULL DEFAULT 0,
            duration_months INTEGER NOT NULL DEFAULT 3,
            is_active       INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS coaching_enrollments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id     INTEGER NOT NULL,
            student_id      INTEGER NOT NULL,
            course_id       INTEGER NOT NULL,
            enrolled_on     TEXT    NOT NULL DEFAULT (date('now')),
            status          TEXT    NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'dropped')),
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES coaching_students(id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES coaching_courses(id) ON DELETE CASCADE,
            UNIQUE (student_id, course_id)
        );

        CREATE TABLE IF NOT EXISTS coaching_fee_payments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id     INTEGER NOT NULL,
            student_id      INTEGER NOT NULL,
            course_id       INTEGER NOT NULL,
            amount_paid     REAL    NOT NULL,
            payment_month   TEXT    NOT NULL,
            payment_date    TEXT    NOT NULL DEFAULT (date('now')),
            payment_method  TEXT    NOT NULL CHECK (payment_method IN ('cash', 'card', 'digital', 'bank_transfer', 'check')),
            notes           TEXT,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES coaching_students(id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES coaching_courses(id) ON DELETE CASCADE
        );

        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_businesses_owner ON businesses(owner_id);
        CREATE INDEX IF NOT EXISTS idx_business_users_business ON business_users(business_id);
        CREATE INDEX IF NOT EXISTS idx_business_users_user ON business_users(user_id);
        CREATE INDEX IF NOT EXISTS idx_products_business ON products_services(business_id);
        CREATE INDEX IF NOT EXISTS idx_transactions_business ON transactions(business_id);
        CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
        CREATE INDEX IF NOT EXISTS idx_inventory_alerts_business ON inventory_alerts(business_id);

        -- Gym indexes
        CREATE INDEX IF NOT EXISTS idx_gym_members_business ON gym_members(business_id);
        CREATE INDEX IF NOT EXISTS idx_gym_members_member_id ON gym_members(business_id, member_id);
        CREATE INDEX IF NOT EXISTS idx_gym_memberships_business ON gym_memberships(business_id);
        CREATE INDEX IF NOT EXISTS idx_gym_memberships_member ON gym_memberships(member_id);
        CREATE INDEX IF NOT EXISTS idx_gym_check_ins_business ON gym_check_ins(business_id);
        CREATE INDEX IF NOT EXISTS idx_gym_check_ins_member ON gym_check_ins(member_id);
        CREATE INDEX IF NOT EXISTS idx_gym_check_ins_date ON gym_check_ins(check_in_time);
        CREATE INDEX IF NOT EXISTS idx_gym_equipment_business ON gym_equipment(business_id);
        CREATE INDEX IF NOT EXISTS idx_gym_classes_business ON gym_classes(business_id);
        CREATE INDEX IF NOT EXISTS idx_gym_classes_date ON gym_classes(class_date);
        CREATE INDEX IF NOT EXISTS idx_gym_class_bookings_business ON gym_class_bookings(business_id);
        CREATE INDEX IF NOT EXISTS idx_gym_class_bookings_class ON gym_class_bookings(class_id);

        CREATE INDEX IF NOT EXISTS idx_coaching_students_business ON coaching_students(business_id);
        CREATE INDEX IF NOT EXISTS idx_coaching_courses_business ON coaching_courses(business_id);
        CREATE INDEX IF NOT EXISTS idx_coaching_enrollments_business ON coaching_enrollments(business_id);
        CREATE INDEX IF NOT EXISTS idx_coaching_fees_business ON coaching_fee_payments(business_id);
        """)
        _migrate_users_table(conn)
        _migrate_gym_members_table(conn)


def _migrate_users_table(conn):
    """Add new columns to users table if they don't exist."""
    cursor = conn.execute("PRAGMA table_info(users)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    migrations = [
        ("failed_login_attempts", "INTEGER NOT NULL DEFAULT 0"),
        ("locked_until", "TEXT"),
        ("password_changed_at", "TEXT"),
    ]

    for col_name, col_def in migrations:
        if col_name not in existing_cols:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")


def _migrate_gym_members_table(conn):
    """Migrate gym_members table to rename date_of_birth to joining_date."""
    # Check if gym_members table exists
    cursor = conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='gym_members'
    """)
    table_exists = cursor.fetchone()

    if not table_exists:
        return  # Table doesn't exist yet, no migration needed

    # Check current columns in gym_members table
    cursor = conn.execute("PRAGMA table_info(gym_members)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    # If old column exists but new one doesn't, migrate
    if 'date_of_birth' in existing_cols and 'joining_date' not in existing_cols:
        # Add the new column
        conn.execute("ALTER TABLE gym_members ADD COLUMN joining_date TEXT")

        # Copy data from old column to new column
        conn.execute("UPDATE gym_members SET joining_date = date_of_birth")

        # Note: We can't drop the old column in SQLite easily, but we'll just ignore it
        # The application will use the new column name


# ── User Operations ──────────────────────────────

def create_user(username: str, email: str, hashed_password: str, role: str = "user") -> int:
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            (username, email, hashed_password, role),
        )
        return cursor.lastrowid


def get_user_by_username(username: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def get_user_by_email(email: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def update_last_login(user_id: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET last_login = datetime('now') WHERE id = ?",
            (user_id,),
        )


def get_all_users() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, username, email, role, is_active, created_at, last_login FROM users ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def toggle_user_active(user_id: int, is_active: bool):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (int(is_active), user_id),
        )


def update_user_role(user_id: int, role: str):
    with get_db() as conn:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))


def delete_user(user_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


def get_user_count() -> int:
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


# ── Dataset Operations ───────────────────────────

def log_dataset(user_id: int, filename: str, row_count: int, file_size: int) -> int:
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO datasets (user_id, filename, row_count, file_size) VALUES (?, ?, ?, ?)",
            (user_id, filename, row_count, file_size),
        )
        return cursor.lastrowid


def get_user_datasets(user_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM datasets WHERE user_id = ? ORDER BY uploaded_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_datasets() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT d.*, u.username
            FROM datasets d JOIN users u ON d.user_id = u.id
            ORDER BY d.uploaded_at DESC
        """).fetchall()
        return [dict(r) for r in rows]


def get_dataset_count() -> int:
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) FROM datasets").fetchone()[0]


# ── AI Request Tracking ─────────────────────────

def log_ai_request(user_id: int, provider: str, question: str, tokens_used: int = 0):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO ai_requests (user_id, provider, question, tokens_used) VALUES (?, ?, ?, ?)",
            (user_id, provider, question, tokens_used),
        )


def get_user_ai_requests(user_id: int, limit: int = 50) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM ai_requests WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_ai_requests(limit: int = 100) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT a.*, u.username
            FROM ai_requests a JOIN users u ON a.user_id = u.id
            ORDER BY a.created_at DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_ai_request_count() -> int:
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) FROM ai_requests").fetchone()[0]


def get_ai_requests_today() -> int:
    with get_db() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM ai_requests WHERE date(created_at) = date('now')"
        ).fetchone()[0]


# ── Login History ────────────────────────────────

def log_login(user_id: int, ip_address: str = None, success: bool = True):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO login_history (user_id, ip_address, success) VALUES (?, ?, ?)",
            (user_id, ip_address, int(success)),
        )


# ── Admin Stats ──────────────────────────────────

def get_admin_stats() -> dict:
    with get_db() as conn:
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM users WHERE is_active = 1").fetchone()[0]
        datasets = conn.execute("SELECT COUNT(*) FROM datasets").fetchone()[0]
        ai_total = conn.execute("SELECT COUNT(*) FROM ai_requests").fetchone()[0]
        ai_today = conn.execute(
            "SELECT COUNT(*) FROM ai_requests WHERE date(created_at) = date('now')"
        ).fetchone()[0]
        logins_today = conn.execute(
            "SELECT COUNT(*) FROM login_history WHERE date(created_at) = date('now') AND success = 1"
        ).fetchone()[0]

        return {
            "total_users": users,
            "active_users": active,
            "total_datasets": datasets,
            "total_ai_requests": ai_total,
            "ai_requests_today": ai_today,
            "logins_today": logins_today,
        }


# ── Password Reset Operations ────────────────────

def create_password_reset_token(user_id: int, token: str, expires_at: str) -> int:
    """Create a password reset token."""
    with get_db() as conn:
        conn.execute(
            "UPDATE password_reset_tokens SET used = 1 WHERE user_id = ? AND used = 0",
            (user_id,)
        )
        cursor = conn.execute(
            "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
            (user_id, token, expires_at)
        )
        return cursor.lastrowid


def get_password_reset_token(token: str) -> dict | None:
    """Get password reset token info."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM password_reset_tokens WHERE token = ? AND used = 0",
            (token,)
        ).fetchone()
        return dict(row) if row else None


def mark_reset_token_used(token: str):
    """Mark a reset token as used."""
    with get_db() as conn:
        conn.execute(
            "UPDATE password_reset_tokens SET used = 1 WHERE token = ?",
            (token,)
        )


def update_user_password(user_id: int, hashed_password: str):
    """Update user's password."""
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET password = ?, password_changed_at = datetime('now') WHERE id = ?",
            (hashed_password, user_id)
        )


# ── Account Lockout Operations ───────────────────

def increment_failed_attempts(user_id: int) -> int:
    """Increment failed login attempts and return new count."""
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET failed_login_attempts = failed_login_attempts + 1 WHERE id = ?",
            (user_id,)
        )
        row = conn.execute(
            "SELECT failed_login_attempts FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        return row[0] if row else 0


def reset_failed_attempts(user_id: int):
    """Reset failed login attempts after successful login."""
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET failed_login_attempts = 0 WHERE id = ?",
            (user_id,)
        )


def lock_account(user_id: int, locked_until: str, reason: str = "failed_attempts"):
    """Lock a user account."""
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET locked_until = ? WHERE id = ?",
            (locked_until, user_id)
        )
        conn.execute(
            "INSERT INTO account_lockouts (user_id, locked_until, reason) VALUES (?, ?, ?)",
            (user_id, locked_until, reason)
        )


def unlock_account(user_id: int, admin_id: int = None):
    """Unlock a user account (by admin or auto)."""
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET locked_until = NULL, failed_login_attempts = 0 WHERE id = ?",
            (user_id,)
        )
        if admin_id:
            conn.execute(
                "UPDATE account_lockouts SET unlocked_by = ? WHERE user_id = ? AND unlocked_by IS NULL",
                (admin_id, user_id)
            )


def get_locked_users() -> list[dict]:
    """Get all currently locked users."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, username, email, locked_until, failed_login_attempts
            FROM users
            WHERE locked_until IS NOT NULL AND locked_until > datetime('now')
        """).fetchall()
        return [dict(r) for r in rows]


# ── 2FA Operations ───────────────────────────────

def create_2fa_setup(user_id: int, encrypted_secret: str, backup_codes_json: str):
    """Create 2FA setup (not enabled yet)."""
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO user_2fa
               (user_id, secret, is_enabled, backup_codes)
               VALUES (?, ?, 0, ?)""",
            (user_id, encrypted_secret, backup_codes_json)
        )


def enable_2fa(user_id: int):
    """Enable 2FA after successful verification."""
    with get_db() as conn:
        conn.execute(
            "UPDATE user_2fa SET is_enabled = 1 WHERE user_id = ?",
            (user_id,)
        )


def disable_2fa(user_id: int):
    """Disable 2FA for a user."""
    with get_db() as conn:
        conn.execute("DELETE FROM user_2fa WHERE user_id = ?", (user_id,))


def get_user_2fa(user_id: int) -> dict | None:
    """Get user's 2FA configuration."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM user_2fa WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None


def use_backup_code(user_id: int, remaining_codes_json: str):
    """Update backup codes after one is used."""
    with get_db() as conn:
        conn.execute(
            "UPDATE user_2fa SET backup_codes = ? WHERE user_id = ?",
            (remaining_codes_json, user_id)
        )


def get_users_with_2fa() -> list[dict]:
    """Get users who have 2FA enabled (for admin view)."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT u.id, u.username, u.email, t.is_enabled, t.created_at
            FROM users u
            JOIN user_2fa t ON u.id = t.user_id
            WHERE t.is_enabled = 1
        """).fetchall()
        return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════════════════════
# MULTI-BUSINESS PLATFORM OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

# ── Business Operations ──────────────────────────

def create_business(name: str, business_type: str, owner_id: int, description: str = None,
                   address: str = None, phone: str = None, email: str = None) -> int:
    """Create a new business and add owner to business_users."""
    with get_db() as conn:
        # Create business
        cursor = conn.execute("""
            INSERT INTO businesses (name, business_type, description, address, phone, email, owner_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, business_type, description, address, phone, email, owner_id))
        business_id = cursor.lastrowid

        # Add owner to business_users
        conn.execute("""
            INSERT INTO business_users (business_id, user_id, role)
            VALUES (?, ?, 'owner')
        """, (business_id, owner_id))

        return business_id


def get_user_businesses(user_id: int) -> list[dict]:
    """Get all businesses a user has access to."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT b.*, bu.role
            FROM businesses b
            JOIN business_users bu ON b.id = bu.business_id
            WHERE bu.user_id = ? AND b.is_active = 1
            ORDER BY b.name
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]


def get_business_by_id(business_id: int) -> dict | None:
    """Get business by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM businesses WHERE id = ?", (business_id,)).fetchone()
        return dict(row) if row else None


def update_business(business_id: int, **kwargs):
    """Update business information."""
    valid_fields = ['name', 'business_type', 'description', 'address', 'phone', 'email']
    updates = {k: v for k, v in kwargs.items() if k in valid_fields}

    if not updates:
        return

    set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [business_id]

    with get_db() as conn:
        conn.execute(f"UPDATE businesses SET {set_clause} WHERE id = ?", values)


def get_business_users(business_id: int) -> list[dict]:
    """Get all users for a business with their roles."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT u.id, u.username, u.email, bu.role, bu.created_at as joined_at
            FROM users u
            JOIN business_users bu ON u.id = bu.user_id
            WHERE bu.business_id = ?
            ORDER BY bu.created_at
        """, (business_id,)).fetchall()
        return [dict(r) for r in rows]


def add_user_to_business(business_id: int, user_id: int, role: str):
    """Add a user to a business with a specific role."""
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO business_users (business_id, user_id, role)
            VALUES (?, ?, ?)
        """, (business_id, user_id, role))


def remove_user_from_business(business_id: int, user_id: int):
    """Remove a user from a business."""
    with get_db() as conn:
        conn.execute("""
            DELETE FROM business_users
            WHERE business_id = ? AND user_id = ?
        """, (business_id, user_id))


def user_has_business_access(user_id: int, business_id: int) -> str | None:
    """Check if user has access to business. Returns role or None."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT bu.role FROM business_users bu
            JOIN businesses b ON bu.business_id = b.id
            WHERE bu.user_id = ? AND bu.business_id = ? AND b.is_active = 1
        """, (user_id, business_id)).fetchone()
        return row[0] if row else None


# ── Products/Services Operations ─────────────────

def create_product_service(business_id: int, name: str, type: str, price: float,
                          cost: float = 0, stock_quantity: int = None,
                          min_stock_level: int = 5, duration_days: int = None,
                          description: str = None, category: str = None, sku: str = None) -> int:
    """Create a new product or service."""
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO products_services
            (business_id, name, type, price, cost, stock_quantity, min_stock_level,
             duration_days, description, category, sku)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (business_id, name, type, price, cost, stock_quantity, min_stock_level,
              duration_days, description, category, sku))
        return cursor.lastrowid


def get_business_products_services(business_id: int, active_only: bool = True) -> list[dict]:
    """Get all products/services for a business."""
    with get_db() as conn:
        where_clause = "WHERE business_id = ?"
        params = [business_id]

        if active_only:
            where_clause += " AND is_active = 1"

        rows = conn.execute(f"""
            SELECT * FROM products_services
            {where_clause}
            ORDER BY name
        """, params).fetchall()
        return [dict(r) for r in rows]


def get_product_service_by_id(product_service_id: int) -> dict | None:
    """Get product/service by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM products_services WHERE id = ?",
            (product_service_id,)
        ).fetchone()
        return dict(row) if row else None


def update_product_service(product_service_id: int, **kwargs):
    """Update product/service information."""
    valid_fields = [
        'name', 'type', 'price', 'cost', 'stock_quantity', 'min_stock_level',
        'duration_days', 'description', 'category', 'sku', 'is_active'
    ]
    updates = {k: v for k, v in kwargs.items() if k in valid_fields}

    if not updates:
        return

    updates['updated_at'] = datetime.now().isoformat()
    set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [product_service_id]

    with get_db() as conn:
        conn.execute(f"UPDATE products_services SET {set_clause} WHERE id = ?", values)


def delete_product_service(product_service_id: int):
    """Soft delete a product/service."""
    with get_db() as conn:
        conn.execute(
            "UPDATE products_services SET is_active = 0 WHERE id = ?",
            (product_service_id,)
        )


def update_stock_quantity(product_id: int, new_quantity: int):
    """Update stock quantity for a product."""
    with get_db() as conn:
        conn.execute("""
            UPDATE products_services
            SET stock_quantity = ?, updated_at = datetime('now')
            WHERE id = ? AND type = 'product'
        """, (new_quantity, product_id))


def get_low_stock_products(business_id: int) -> list[dict]:
    """Get products with low stock levels."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM products_services
            WHERE business_id = ?
              AND type = 'product'
              AND is_active = 1
              AND stock_quantity IS NOT NULL
              AND stock_quantity <= min_stock_level
            ORDER BY stock_quantity ASC
        """, (business_id,)).fetchall()
        return [dict(r) for r in rows]


# ── Transaction Operations ──────────────────────

def create_transaction(business_id: int, product_service_id: int, user_id: int,
                      quantity: int, unit_price: float, unit_cost: float = 0,
                      payment_method: str = 'cash', customer_name: str = None,
                      customer_email: str = None, customer_phone: str = None,
                      notes: str = None, transaction_date: str = None) -> int:
    """Create a new transaction and update inventory."""
    if transaction_date is None:
        transaction_date = datetime.now().isoformat()

    total_amount = quantity * unit_price

    with get_db() as conn:
        # Create transaction
        cursor = conn.execute("""
            INSERT INTO transactions
            (business_id, product_service_id, user_id, customer_name, customer_email,
             customer_phone, quantity, unit_price, unit_cost, total_amount,
             payment_method, notes, transaction_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (business_id, product_service_id, user_id, customer_name, customer_email,
              customer_phone, quantity, unit_price, unit_cost, total_amount,
              payment_method, notes, transaction_date))
        transaction_id = cursor.lastrowid

        # Update inventory for products
        product = get_product_service_by_id(product_service_id)
        if product and product['type'] == 'product' and product['stock_quantity'] is not None:
            new_quantity = max(0, product['stock_quantity'] - quantity)
            update_stock_quantity(product_service_id, new_quantity)

            # Check if low stock alert needed
            if new_quantity <= product['min_stock_level']:
                _create_inventory_alert(business_id, product_service_id,
                                      'low_stock' if new_quantity > 0 else 'out_of_stock',
                                      new_quantity, product['min_stock_level'])

        return transaction_id


def get_business_transactions(business_id: int, limit: int = 100, offset: int = 0) -> list[dict]:
    """Get transactions for a business."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT t.*, ps.name as product_service_name, ps.type as product_service_type,
                   u.username as staff_name
            FROM transactions t
            JOIN products_services ps ON t.product_service_id = ps.id
            JOIN users u ON t.user_id = u.id
            WHERE t.business_id = ?
            ORDER BY t.transaction_date DESC, t.created_at DESC
            LIMIT ? OFFSET ?
        """, (business_id, limit, offset)).fetchall()
        return [dict(r) for r in rows]


def get_transaction_by_id(transaction_id: int) -> dict | None:
    """Get transaction by ID with product/service details."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT t.*, ps.name as product_service_name, ps.type as product_service_type,
                   u.username as staff_name
            FROM transactions t
            JOIN products_services ps ON t.product_service_id = ps.id
            JOIN users u ON t.user_id = u.id
            WHERE t.id = ?
        """, (transaction_id,)).fetchone()
        return dict(row) if row else None


def get_business_revenue_summary(business_id: int, start_date: str = None, end_date: str = None) -> dict:
    """Get revenue summary for a business."""
    with get_db() as conn:
        where_clause = "WHERE business_id = ?"
        params = [business_id]

        if start_date:
            where_clause += " AND date(transaction_date) >= ?"
            params.append(start_date)
        if end_date:
            where_clause += " AND date(transaction_date) <= ?"
            params.append(end_date)

        row = conn.execute(f"""
            SELECT
                COUNT(*) as total_transactions,
                SUM(total_amount) as total_revenue,
                SUM((unit_price - unit_cost) * quantity) as total_profit,
                AVG(total_amount) as avg_transaction_value,
                SUM(quantity) as total_items_sold
            FROM transactions
            {where_clause}
        """, params).fetchone()

        if row:
            result = dict(row)
            result['total_revenue'] = result['total_revenue'] or 0
            result['total_profit'] = result['total_profit'] or 0
            result['avg_transaction_value'] = result['avg_transaction_value'] or 0
            result['profit_margin'] = (
                (result['total_profit'] / result['total_revenue'] * 100)
                if result['total_revenue'] > 0 else 0
            )
            return result
        return {
            'total_transactions': 0, 'total_revenue': 0, 'total_profit': 0,
            'avg_transaction_value': 0, 'total_items_sold': 0, 'profit_margin': 0
        }


def get_daily_revenue_data(business_id: int, days: int = 30) -> list[dict]:
    """Get daily revenue data for charts."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                date(transaction_date) as date,
                COUNT(*) as transactions,
                SUM(total_amount) as revenue,
                SUM((unit_price - unit_cost) * quantity) as profit
            FROM transactions
            WHERE business_id = ?
              AND date(transaction_date) >= date('now', '-' || ? || ' days')
            GROUP BY date(transaction_date)
            ORDER BY date(transaction_date)
        """, (business_id, days)).fetchall()
        return [dict(r) for r in rows]


def get_top_products_services(business_id: int, limit: int = 10) -> list[dict]:
    """Get top selling products/services."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                ps.id, ps.name, ps.type,
                COUNT(t.id) as transactions_count,
                SUM(t.quantity) as total_quantity_sold,
                SUM(t.total_amount) as total_revenue,
                SUM((t.unit_price - t.unit_cost) * t.quantity) as total_profit
            FROM products_services ps
            JOIN transactions t ON ps.id = t.product_service_id
            WHERE ps.business_id = ?
            GROUP BY ps.id, ps.name, ps.type
            ORDER BY total_revenue DESC
            LIMIT ?
        """, (business_id, limit)).fetchall()
        return [dict(r) for r in rows]


# ── Inventory Alert Operations ──────────────────

def _create_inventory_alert(business_id: int, product_id: int, alert_type: str,
                           current_stock: int, threshold: int):
    """Create an inventory alert (internal function)."""
    with get_db() as conn:
        # Check if alert already exists and is not resolved
        existing = conn.execute("""
            SELECT id FROM inventory_alerts
            WHERE business_id = ? AND product_id = ? AND alert_type = ?
              AND is_resolved = 0
        """, (business_id, product_id, alert_type)).fetchone()

        if not existing:
            conn.execute("""
                INSERT INTO inventory_alerts
                (business_id, product_id, alert_type, current_stock, threshold)
                VALUES (?, ?, ?, ?, ?)
            """, (business_id, product_id, alert_type, current_stock, threshold))


def get_business_inventory_alerts(business_id: int, unresolved_only: bool = True) -> list[dict]:
    """Get inventory alerts for a business."""
    with get_db() as conn:
        where_clause = "WHERE ia.business_id = ?"
        params = [business_id]

        if unresolved_only:
            where_clause += " AND ia.is_resolved = 0"

        rows = conn.execute(f"""
            SELECT ia.*, ps.name as product_name, ps.sku
            FROM inventory_alerts ia
            JOIN products_services ps ON ia.product_id = ps.id
            {where_clause}
            ORDER BY ia.created_at DESC
        """, params).fetchall()
        return [dict(r) for r in rows]


def resolve_inventory_alert(alert_id: int):
    """Mark an inventory alert as resolved."""
    with get_db() as conn:
        conn.execute("""
            UPDATE inventory_alerts
            SET is_resolved = 1, resolved_at = datetime('now')
            WHERE id = ?
        """, (alert_id,))


# ══════════════════════════════════════════════════════════════════════════════
# GYM MANAGEMENT FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def create_gym_member(business_id: int, member_id: str, first_name: str, last_name: str,
                     email: str = None, phone: str = None, joining_date: str = None,
                     emergency_contact_name: str = None, emergency_contact_phone: str = None,
                     medical_conditions: str = None) -> int:
    """Create a new gym member."""
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO gym_members
            (business_id, member_id, first_name, last_name, email, phone, joining_date,
             emergency_contact_name, emergency_contact_phone, medical_conditions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (business_id, member_id, first_name, last_name, email, phone, joining_date,
              emergency_contact_name, emergency_contact_phone, medical_conditions))
        return cursor.lastrowid


def get_gym_members(business_id: int, active_only: bool = True) -> list[dict]:
    """Get all gym members for a business."""
    with get_db() as conn:
        where_clause = "WHERE business_id = ?"
        params = [business_id]

        if active_only:
            where_clause += " AND is_active = 1"

        rows = conn.execute(f"""
            SELECT * FROM gym_members
            {where_clause}
            ORDER BY first_name, last_name
        """, params).fetchall()
        return [dict(r) for r in rows]


def get_gym_member_by_id(member_id: int) -> dict:
    """Get gym member by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM gym_members WHERE id = ?", (member_id,)).fetchone()
        return dict(row) if row else None


def get_gym_member_by_member_id(business_id: int, member_id: str) -> dict:
    """Get gym member by custom member ID."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM gym_members
            WHERE business_id = ? AND member_id = ?
        """, (business_id, member_id)).fetchone()
        return dict(row) if row else None


def update_gym_member(member_id: int, **kwargs):
    """Update gym member information."""
    if not kwargs:
        return

    # Filter valid columns
    valid_columns = ['first_name', 'last_name', 'email', 'phone', 'joining_date',
                    'emergency_contact_name', 'emergency_contact_phone', 'medical_conditions', 'is_active']
    updates = {k: v for k, v in kwargs.items() if k in valid_columns}

    if not updates:
        return

    updates['updated_at'] = 'datetime("now")'

    with get_db() as conn:
        set_clause = ", ".join([f"{k} = ?" if k != 'updated_at' else f"{k} = {v}"
                               for k in updates.keys()])
        values = [v for k, v in updates.items() if k != 'updated_at']
        values.append(member_id)

        conn.execute(f"""
            UPDATE gym_members
            SET {set_clause}
            WHERE id = ?
        """, values)


def create_gym_membership(business_id: int, member_id: int, membership_type_id: int,
                         start_date: str, end_date: str, amount_paid: float,
                         payment_method: str, created_by: int) -> int:
    """Create a new gym membership."""
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO gym_memberships
            (business_id, member_id, membership_type_id, start_date, end_date,
             amount_paid, payment_method, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (business_id, member_id, membership_type_id, start_date, end_date,
              amount_paid, payment_method, created_by))
        return cursor.lastrowid


def get_gym_memberships(business_id: int, member_id: int = None, active_only: bool = True) -> list[dict]:
    """Get gym memberships."""
    with get_db() as conn:
        where_clause = "WHERE gm.business_id = ?"
        params = [business_id]

        if member_id:
            where_clause += " AND gm.member_id = ?"
            params.append(member_id)

        if active_only:
            where_clause += " AND gm.is_active = 1 AND gm.end_date >= date('now')"

        rows = conn.execute(f"""
            SELECT gm.*,
                   gym.first_name, gym.last_name, gym.member_id as custom_member_id,
                   ps.name as membership_type_name, ps.price
            FROM gym_memberships gm
            JOIN gym_members gym ON gm.member_id = gym.id
            JOIN products_services ps ON gm.membership_type_id = ps.id
            {where_clause}
            ORDER BY gm.end_date DESC
        """, params).fetchall()
        return [dict(r) for r in rows]


def create_gym_check_in(business_id: int, member_id: int, entry_type: str,
                       amount_paid: float = 0, payment_method: str = 'free',
                       checked_in_by: int = None, notes: str = None) -> int:
    """Record a gym check-in."""
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO gym_check_ins
            (business_id, member_id, entry_type, amount_paid, payment_method,
             checked_in_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (business_id, member_id, entry_type, amount_paid, payment_method,
              checked_in_by, notes))
        return cursor.lastrowid


def get_gym_check_ins(business_id: int, date_filter: str = None, limit: int = 50) -> list[dict]:
    """Get gym check-ins with optional date filtering."""
    with get_db() as conn:
        where_clause = "WHERE gc.business_id = ?"
        params = [business_id]

        if date_filter:
            where_clause += " AND date(gc.check_in_time) = ?"
            params.append(date_filter)

        rows = conn.execute(f"""
            SELECT gc.*,
                   gm.first_name, gm.last_name, gm.member_id as custom_member_id,
                   u.username as checked_in_by_name
            FROM gym_check_ins gc
            JOIN gym_members gm ON gc.member_id = gm.id
            LEFT JOIN users u ON gc.checked_in_by = u.id
            {where_clause}
            ORDER BY gc.check_in_time DESC
            LIMIT ?
        """, params + [limit]).fetchall()
        return [dict(r) for r in rows]


def update_gym_check_out(check_in_id: int):
    """Update check-out time for a gym check-in."""
    with get_db() as conn:
        conn.execute("""
            UPDATE gym_check_ins
            SET check_out_time = datetime('now')
            WHERE id = ?
        """, (check_in_id,))


def create_gym_equipment(business_id: int, equipment_name: str, equipment_type: str,
                        brand: str = None, model: str = None, serial_number: str = None,
                        purchase_date: str = None, warranty_expiry: str = None) -> int:
    """Add new gym equipment."""
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO gym_equipment
            (business_id, equipment_name, equipment_type, brand, model,
             serial_number, purchase_date, warranty_expiry)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (business_id, equipment_name, equipment_type, brand, model,
              serial_number, purchase_date, warranty_expiry))
        return cursor.lastrowid


def get_gym_equipment(business_id: int, operational_only: bool = False) -> list[dict]:
    """Get gym equipment list."""
    with get_db() as conn:
        where_clause = "WHERE business_id = ?"
        params = [business_id]

        if operational_only:
            where_clause += " AND is_operational = 1"

        rows = conn.execute(f"""
            SELECT * FROM gym_equipment
            {where_clause}
            ORDER BY equipment_type, equipment_name
        """, params).fetchall()
        return [dict(r) for r in rows]


def update_gym_equipment_maintenance(equipment_id: int, maintenance_notes: str,
                                   next_maintenance: str = None):
    """Update equipment maintenance records."""
    with get_db() as conn:
        conn.execute("""
            UPDATE gym_equipment
            SET last_maintenance = datetime('now'),
                next_maintenance = ?,
                maintenance_notes = ?,
                updated_at = datetime('now')
            WHERE id = ?
        """, (next_maintenance, maintenance_notes, equipment_id))


def get_gym_daily_summary(business_id: int, date: str = None) -> dict:
    """Get daily gym summary statistics."""
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')

    with get_db() as conn:
        # Daily check-ins
        check_ins = conn.execute("""
            SELECT COUNT(*) as count, SUM(amount_paid) as revenue
            FROM gym_check_ins
            WHERE business_id = ? AND date(check_in_time) = ?
        """, (business_id, date)).fetchone()

        # Active members
        active_members = conn.execute("""
            SELECT COUNT(*) as count
            FROM gym_members
            WHERE business_id = ? AND is_active = 1
        """, (business_id,)).fetchone()

        # Equipment status
        equipment_status = conn.execute("""
            SELECT
                COUNT(*) as total_equipment,
                SUM(CASE WHEN is_operational = 1 THEN 1 ELSE 0 END) as operational_equipment
            FROM gym_equipment
            WHERE business_id = ?
        """, (business_id,)).fetchone()

        return {
            'date': date,
            'daily_check_ins': check_ins['count'] if check_ins else 0,
            'daily_revenue': check_ins['revenue'] if check_ins and check_ins['revenue'] else 0,
            'total_active_members': active_members['count'] if active_members else 0,
            'total_equipment': equipment_status['total_equipment'] if equipment_status else 0,
            'operational_equipment': equipment_status['operational_equipment'] if equipment_status else 0
        }


def get_gym_membership_expiring_soon(business_id: int, days_ahead: int = 7) -> list[dict]:
    """Get memberships expiring within specified days."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT gm.*,
                   gym.first_name, gym.last_name, gym.member_id as custom_member_id,
                   gym.phone, gym.email,
                   ps.name as membership_type_name
            FROM gym_memberships gm
            JOIN gym_members gym ON gm.member_id = gym.id
            JOIN products_services ps ON gm.membership_type_id = ps.id
            WHERE gm.business_id = ?
            AND gm.is_active = 1
            AND gm.end_date BETWEEN date('now') AND date('now', '+' || ? || ' days')
            ORDER BY gm.end_date ASC
        """, (business_id, days_ahead)).fetchall()
        return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════════════════════
# COACHING MANAGEMENT FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def create_coaching_student(
    business_id: int,
    student_code: str,
    first_name: str,
    last_name: str,
    email: str = None,
    phone: str = None,
    guardian_name: str = None,
) -> int:
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO coaching_students
            (business_id, student_code, first_name, last_name, email, phone, guardian_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (business_id, student_code, first_name, last_name, email, phone, guardian_name),
        )
        return cursor.lastrowid


def get_coaching_students(business_id: int, active_only: bool = True) -> list[dict]:
    with get_db() as conn:
        where_clause = "WHERE business_id = ?"
        params = [business_id]
        if active_only:
            where_clause += " AND is_active = 1"

        rows = conn.execute(
            f"""
            SELECT * FROM coaching_students
            {where_clause}
            ORDER BY first_name, last_name
            """,
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def create_coaching_course(
    business_id: int,
    course_name: str,
    instructor_name: str = None,
    monthly_fee: float = 0,
    duration_months: int = 3,
) -> int:
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO coaching_courses
            (business_id, course_name, instructor_name, monthly_fee, duration_months)
            VALUES (?, ?, ?, ?, ?)
            """,
            (business_id, course_name, instructor_name, monthly_fee, duration_months),
        )
        return cursor.lastrowid


def get_coaching_courses(business_id: int, active_only: bool = True) -> list[dict]:
    with get_db() as conn:
        where_clause = "WHERE business_id = ?"
        params = [business_id]
        if active_only:
            where_clause += " AND is_active = 1"

        rows = conn.execute(
            f"""
            SELECT * FROM coaching_courses
            {where_clause}
            ORDER BY course_name
            """,
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def enroll_student_in_course(business_id: int, student_id: int, course_id: int) -> int:
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO coaching_enrollments
            (business_id, student_id, course_id)
            VALUES (?, ?, ?)
            """,
            (business_id, student_id, course_id),
        )
        return cursor.lastrowid


def get_coaching_enrollments(business_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT e.*, s.student_code, s.first_name, s.last_name, c.course_name, c.monthly_fee
            FROM coaching_enrollments e
            JOIN coaching_students s ON e.student_id = s.id
            JOIN coaching_courses c ON e.course_id = c.id
            WHERE e.business_id = ?
            ORDER BY e.enrolled_on DESC
            """,
            (business_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def record_coaching_fee_payment(
    business_id: int,
    student_id: int,
    course_id: int,
    amount_paid: float,
    payment_month: str,
    payment_method: str,
    notes: str = None,
) -> int:
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO coaching_fee_payments
            (business_id, student_id, course_id, amount_paid, payment_month, payment_method, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (business_id, student_id, course_id, amount_paid, payment_month, payment_method, notes),
        )
        return cursor.lastrowid


def get_coaching_fee_payments(business_id: int, limit: int = 100) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT p.*, s.student_code, s.first_name, s.last_name, c.course_name
            FROM coaching_fee_payments p
            JOIN coaching_students s ON p.student_id = s.id
            JOIN coaching_courses c ON p.course_id = c.id
            WHERE p.business_id = ?
            ORDER BY p.payment_date DESC, p.created_at DESC
            LIMIT ?
            """,
            (business_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_coaching_summary(business_id: int) -> dict:
    with get_db() as conn:
        students = conn.execute(
            "SELECT COUNT(*) FROM coaching_students WHERE business_id = ? AND is_active = 1",
            (business_id,),
        ).fetchone()[0]
        courses = conn.execute(
            "SELECT COUNT(*) FROM coaching_courses WHERE business_id = ? AND is_active = 1",
            (business_id,),
        ).fetchone()[0]
        revenue = conn.execute(
            "SELECT COALESCE(SUM(amount_paid), 0) FROM coaching_fee_payments WHERE business_id = ?",
            (business_id,),
        ).fetchone()[0]
        return {
            "active_students": students,
            "active_courses": courses,
            "fee_revenue": revenue,
        }


# Initialize on import
init_db()
