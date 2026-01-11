from __future__ import annotations

from typing import Optional, Union, List, Tuple, Any
import sqlite3
import os
from pathlib import Path


# DB dosyası: app/db/app.db
BASE_DIR = Path(__file__).resolve().parent.parent   # app/
DB_PATH = BASE_DIR / "db" / "app.db"


def get_conn() -> sqlite3.Connection:
    """
    SQLite bağlantısı döndürür.
    check_same_thread=False: Streamlit/çoklu thread gibi senaryolarda işe yarar.
    """
    # DB klasörü yoksa oluştur
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _to_text_id(v: Optional[Union[int, str]]) -> Optional[str]:
    """
    Places place_id string, CSV id int olabilir.
    feedback tablosunda TEXT tuttuğumuz için hepsini str'a çeviriyoruz.
    """
    if v is None:
        return None
    s = str(v).strip()
    return s if s != "" else None


def get_or_create_user(user_identifier: str) -> int:
    user_identifier = (user_identifier or "").strip() or "anon"

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE user_identifier = ?", (user_identifier,))
    row = cur.fetchone()
    if row:
        conn.close()
        return int(row[0])

    cur.execute("INSERT INTO users (user_identifier) VALUES (?)", (user_identifier,))
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return int(user_id)


def create_session(user_id: int, session_token: str = "") -> int:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO sessions (user_id, session_token) VALUES (?, ?)",
        (int(user_id), session_token or "")
    )
    conn.commit()
    session_id = cur.lastrowid
    conn.close()
    return int(session_id)


def insert_feedback(
    user_id: int,
    session_id: int,
    otel_id: Union[int, str],
    restoran_id: Optional[Union[int, str]],
    rating: int,
    comment: str = ""
) -> None:
    """
    feedback tablosuna kayıt atar.
    - otel_id/restoran_id: int veya str olabilir (CSV int, Places str)
    - DB'de TEXT olarak saklanır (migration yaptıysan uyumlu)
    """
    otel_id_txt = _to_text_id(otel_id)
    restoran_id_txt = _to_text_id(restoran_id)
    comment = (comment or "").strip()

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO feedback (user_id, session_id, otel_id, restoran_id, rating, comment)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (int(user_id), int(session_id), otel_id_txt, restoran_id_txt, int(rating), comment)
    )

    conn.commit()
    conn.close()


def get_recent_feedback(user_id: int, limit: int = 20) -> List[Tuple[Any, ...]]:
    """
    Son feedback kayıtlarını döndürür:
    (rating, comment, created_at, otel_id, restoran_id)
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT rating, comment, created_at, otel_id, restoran_id
        FROM feedback
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (int(user_id), int(limit))
    )

    rows = cur.fetchall()
    conn.close()
    return rows

def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_identifier TEXT UNIQUE NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id INTEGER NOT NULL,
            otel_id TEXT,
            restoran_id TEXT,
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
    """)

    conn.commit()
    conn.close()
