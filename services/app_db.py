# services/app_db.py
# services/app_service/app_db.py
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List

APP_DB_PATH = Path("app.db")


def get_connection():
    return sqlite3.connect(APP_DB_PATH)


def init_app_db():
    conn = get_connection()
    cur = conn.cursor()

    # User profile
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profile (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            fingerprint TEXT UNIQUE NOT NULL,
            avatar_url TEXT,
            theme TEXT DEFAULT 'light',
            accent_color TEXT DEFAULT 'violet'
        )
        """
    )

    # Contacts
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS contact (
            id TEXT PRIMARY KEY,
            owner_user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            display_name TEXT,
            fingerprint TEXT NOT NULL,
            avatar_url TEXT,
            is_blocked INTEGER DEFAULT 0,
            UNIQUE (owner_user_id, fingerprint),
            FOREIGN KEY (owner_user_id) REFERENCES user_profile(id)
        )
        """
    )

    # Conversations
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation (
            id TEXT PRIMARY KEY,
            owner_user_id TEXT NOT NULL,
            contact_id TEXT NOT NULL,
            last_message_text TEXT,
            last_message_time TEXT,
            unread_count INTEGER DEFAULT 0,
            FOREIGN KEY (owner_user_id) REFERENCES user_profile(id),
            FOREIGN KEY (contact_id)    REFERENCES contact(id)
        )
        """
    )

    # Messages
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS message (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            from_fp TEXT NOT NULL,
            to_fp TEXT NOT NULL,
            text TEXT NOT NULL,
            status TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            msg_id TEXT,           -- envelope.header.msg_id
            envelope_json TEXT,    -- serialized MessageEnvelope
            FOREIGN KEY (conversation_id) REFERENCES conversation(id)
        )
        """
    )

    conn.commit()
    conn.close()


# ---- simple helpers for UI backend ----

def get_profile_by_username(username: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, username, display_name, fingerprint, avatar_url, theme, accent_color "
        "FROM user_profile WHERE username = ?",
        (username,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    keys = ["id", "username", "display_name", "fingerprint", "avatar_url", "theme", "accent_color"]
    return dict(zip(keys, row))


def create_profile(
    id_: str,
    username: str,
    password_hash: str,
    fingerprint: str,
    display_name: Optional[str] = None,
    avatar_url: Optional[str] = None,
    theme: str = "light",
    accent_color: str = "violet",
) -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO user_profile (id, username, password_hash, display_name,
                                  fingerprint, avatar_url, theme, accent_color)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (id_, username, password_hash, display_name, fingerprint, avatar_url, theme, accent_color),
    )
    conn.commit()
    conn.close()
    return {
        "id": id_,
        "username": username,
        "display_name": display_name,
        "fingerprint": fingerprint,
        "avatar_url": avatar_url,
        "theme": theme,
        "accent_color": accent_color,
    }
