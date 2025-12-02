# services/crypto_service/keystore_db.py
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List

KEYSTORE_DB_PATH = Path("keystore.db")


def get_connection():
    return sqlite3.connect(KEYSTORE_DB_PATH)


def init_keystore_db():
    conn = get_connection()
    cur = conn.cursor()

    # Long-term identity key (one row for now)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS identity_key (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            private_key BLOB NOT NULL,      -- serialized, may be encrypted at rest
            public_key  BLOB NOT NULL,
            fingerprint TEXT UNIQUE NOT NULL,
            created_at  TEXT NOT NULL
        )
        """
    )

    # Known peers
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS peer_key (
            fingerprint TEXT PRIMARY KEY,
            public_key  BLOB NOT NULL,
            label       TEXT,
            first_seen  TEXT,
            last_seen   TEXT
        )
        """
    )

    # Sessions (ECDH-derived)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS session (
            id TEXT PRIMARY KEY,               -- session_id (uuid)
            peer_fingerprint TEXT NOT NULL,
            send_key BLOB NOT NULL,            -- AES-GCM key (32 bytes)
            recv_key BLOB NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            usage_count INTEGER DEFAULT 0,
            max_uses    INTEGER DEFAULT 1000,
            is_active   INTEGER DEFAULT 1,
            FOREIGN KEY(peer_fingerprint) REFERENCES peer_key(fingerprint)
        )
        """
    )

    # Nonce / replay log (for AES-GCM)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS nonce_log (
            session_id TEXT NOT NULL,
            nonce      BLOB NOT NULL,
            direction  TEXT NOT NULL,          -- 'enc' or 'dec'
            used_at    TEXT NOT NULL,
            PRIMARY KEY(session_id, nonce, direction),
            FOREIGN KEY(session_id) REFERENCES session(id)
        )
        """
    )

    # Optional: replay log by msg_id if you want extra protection
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS replay_log (
            msg_id TEXT PRIMARY KEY,
            seen_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()
