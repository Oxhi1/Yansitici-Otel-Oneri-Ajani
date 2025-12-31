import sqlite3
import os

# app/db/app.db konumunu ayarlıyoruz
DB_PATH = os.path.join(os.path.dirname(__file__), "app.db")


def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # users tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_identifier TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # sessions tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_token TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # feedback tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id INTEGER,
            otel_id INTEGER,
            restoran_id INTEGER,
            rating INTEGER,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()
    print("✅ Veritabanı ve tablolar oluşturuldu! Yol:", DB_PATH)


if __name__ == "__main__":
    create_tables()
