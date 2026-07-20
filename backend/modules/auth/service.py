import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from config import JWT_ACCESS_MINUTES, JWT_REFRESH_DAYS, JWT_SECRET
from db import get_connection, row_to_dict


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: int, email: str, tier: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "email": email, "tier": tier, "type": "access", "exp": exp},
        JWT_SECRET,
        algorithm="HS256",
    )


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Not an access token")
    return payload


def store_refresh_token(user_id: int, refresh_token: str, device_hint: str | None) -> None:
    expires = datetime.utcnow() + timedelta(days=JWT_REFRESH_DAYS)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO refresh_tokens (user_id, token_hash, device_hint, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, hash_token(refresh_token), device_hint, expires.isoformat()),
        )
        conn.commit()


def revoke_refresh_token(refresh_token: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE refresh_tokens SET is_revoked = 1 WHERE token_hash = ?",
            (hash_token(refresh_token),),
        )
        conn.commit()


def revoke_all_refresh_tokens(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE refresh_tokens SET is_revoked = 1 WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()


def validate_refresh_token(refresh_token: str) -> dict[str, Any] | None:
    token_hash = hash_token(refresh_token)
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT rt.*, u.email, u.subscription_tier
            FROM refresh_tokens rt
            JOIN users u ON u.id = rt.user_id
            WHERE rt.token_hash = ? AND rt.is_revoked = 0
            """,
            (token_hash,),
        ).fetchone()
        if not row:
            return None
        if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
            return None
        return row_to_dict(row)


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return row_to_dict(row)


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
        return row_to_dict(row)


def create_user(email: str, password: str, full_name: str) -> dict[str, Any]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO users (email, password_hash, full_name)
            VALUES (?, ?, ?)
            """,
            (email.lower(), hash_password(password), full_name),
        )
        conn.commit()
        user_id = cur.lastrowid
    user = get_user_by_id(int(user_id))
    assert user
    return user


def set_user_verified(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE users SET is_verified = 1 WHERE id = ?", (user_id,))
        conn.commit()


def update_password(user_id: int, password: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(password), user_id),
        )
        conn.commit()


def record_failed_login(user_id: int) -> None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT failed_login_attempts FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        attempts = (row["failed_login_attempts"] if row else 0) + 1
        locked_until = None
        if attempts >= 5:
            locked_until = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
            attempts = 0
        conn.execute(
            """
            UPDATE users SET failed_login_attempts = ?, locked_until = ?
            WHERE id = ?
            """,
            (attempts, locked_until, user_id),
        )
        conn.commit()


def reset_failed_login(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = ?",
            (user_id,),
        )
        conn.commit()


def is_account_locked(user: dict[str, Any]) -> bool:
    locked = user.get("locked_until")
    if not locked:
        return False
    return datetime.fromisoformat(locked) > datetime.utcnow()


def save_otp(user_id: int, otp: str, purpose: str, minutes: int = 10) -> None:
    otp_hash = hash_password(otp)
    expires = datetime.utcnow() + timedelta(minutes=minutes)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO email_otps (user_id, otp_hash, purpose, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, otp_hash, purpose, expires.isoformat()),
        )
        conn.commit()


def verify_otp(user_id: int, otp: str, purpose: str) -> bool:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM email_otps
            WHERE user_id = ? AND purpose = ? AND used = 0
            ORDER BY id DESC LIMIT 5
            """,
            (user_id, purpose),
        ).fetchall()
        for row in rows:
            if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
                continue
            if verify_password(otp, row["otp_hash"]):
                conn.execute("UPDATE email_otps SET used = 1 WHERE id = ?", (row["id"],))
                conn.commit()
                return True
    return False


def check_rate_limit(ip: str, endpoint: str, max_attempts: int = 10, window_minutes: int = 60) -> bool:
    """Returns True if allowed, False if rate limited."""
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=window_minutes)
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM rate_limits
            WHERE ip_address = ? AND endpoint = ?
            ORDER BY id DESC LIMIT 1
            """,
            (ip, endpoint),
        ).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO rate_limits (ip_address, endpoint) VALUES (?, ?)",
                (ip, endpoint),
            )
            conn.commit()
            return True
        if datetime.fromisoformat(row["window_start"]) < window_start:
            conn.execute(
                """
                UPDATE rate_limits SET attempts = 1, window_start = ?
                WHERE id = ?
                """,
                (now.isoformat(), row["id"]),
            )
            conn.commit()
            return True
        if row["attempts"] >= max_attempts:
            return False
        conn.execute(
            "UPDATE rate_limits SET attempts = attempts + 1 WHERE id = ?",
            (row["id"],),
        )
        conn.commit()
        return True
