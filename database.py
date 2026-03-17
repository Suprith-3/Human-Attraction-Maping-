import sqlite3
import os
from datetime import datetime

DB_PATH = 'focusos.db'

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    schema = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        start_time DATETIME,
        end_time DATETIME,
        keystrokes INTEGER DEFAULT 0,
        clicks INTEGER DEFAULT 0,
        actions INTEGER DEFAULT 0,
        tab_shifts INTEGER DEFAULT 0,
        mouse_px REAL DEFAULT 0,
        mouse_cm REAL DEFAULT 0,
        focus_score REAL DEFAULT 0,
        app_label TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS key_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, count INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        session_id INTEGER
    );

    CREATE TABLE IF NOT EXISTS mouse_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, clicks INTEGER, actions INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        session_id INTEGER
    );

    CREATE TABLE IF NOT EXISTS tab_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, shift_count INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        session_id INTEGER
    );

    CREATE TABLE IF NOT EXISTS mouse_path (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, total_pixels REAL, total_cm REAL,
        session_id INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS gravity_maps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, session_id INTEGER,
        grid_json TEXT, app_label TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS engagement_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, target_app TEXT,
        planned_duration INTEGER, actual_focus_time INTEGER,
        break_count INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS cv_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, alert_type TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS focus_lock_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, target_app TEXT,
        attempted_switch_time DATETIME,
        overridden INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS blocking_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, shift_count INTEGER,
        blocked_at DATETIME, unlocked_at DATETIME
    );

    CREATE TABLE IF NOT EXISTS rewards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, reward_type TEXT,
        earned_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS user_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        total_coins INTEGER DEFAULT 0,
        streak_days INTEGER DEFAULT 0,
        last_session_date DATE
    );

    CREATE TABLE IF NOT EXISTS heatmap_points (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, session_id INTEGER,
        x REAL, y REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    conn = get_db()
    conn.executescript(schema)
    conn.commit()
    conn.close()

def log_cv_alert(user_id, alert_type):
    conn = get_db()
    conn.execute("INSERT INTO cv_alerts (user_id, alert_type) VALUES (?, ?)", (user_id, alert_type))
    conn.commit()
    conn.close()

def get_user_by_email(email):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return user

def create_user(name, email, password_hash):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", (name, email, password_hash))
        user_id = cursor.lastrowid
        cursor.execute("INSERT INTO user_stats (user_id, last_session_date) VALUES (?, date('now'))", (user_id,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
