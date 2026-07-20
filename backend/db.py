import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

from config import DATABASE_PATH

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL DEFAULT '',
    is_verified INTEGER NOT NULL DEFAULT 0,
    subscription_tier TEXT NOT NULL DEFAULT 'free',
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    device_hint TEXT,
    expires_at TEXT NOT NULL,
    is_revoked INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS email_otps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    otp_hash TEXT NOT NULL,
    purpose TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rate_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 1,
    window_start TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_name TEXT NOT NULL,
    billing_period TEXT NOT NULL,
    razorpay_subscription_id TEXT,
    razorpay_payment_id TEXT,
    status TEXT NOT NULL DEFAULT 'created',
    grace_period_ends_at TEXT,
    amount_paid_paise INTEGER NOT NULL DEFAULT 0,
    expires_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS webhook_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    payload TEXT,
    signature_valid INTEGER NOT NULL DEFAULT 0,
    processed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lifetime_deal_counter (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    sold INTEGER NOT NULL DEFAULT 0,
    cap INTEGER NOT NULL DEFAULT 100
);

INSERT OR IGNORE INTO lifetime_deal_counter (id, sold, cap) VALUES (1, 0, 100);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expiry_date TEXT,
    trade_date TEXT NOT NULL,
    entry_time TEXT,
    exit_time TEXT,
    nifty_at_entry REAL,
    nifty_at_exit REAL,
    strike REAL NOT NULL,
    option_type TEXT NOT NULL,
    entry_premium REAL NOT NULL,
    exit_premium REAL,
    lots INTEGER NOT NULL DEFAULT 1,
    stop_loss REAL,
    target REAL,
    max_pain_at_entry REAL,
    vix_at_entry REAL,
    pcr_at_entry REAL,
    oi_signal TEXT,
    signal_score REAL,
    atm_or_otm TEXT,
    range_high REAL,
    range_low REAL,
    trading_window TEXT,
    emotional_state_entry TEXT,
    exit_reason TEXT,
    trade_mode TEXT NOT NULL DEFAULT 'real',
    followed_plan INTEGER,
    revenge_trade INTEGER DEFAULT 0,
    gross_pnl REAL,
    stt REAL,
    brokerage REAL,
    other_charges REAL,
    net_pnl REAL,
    net_pnl_pct REAL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)
