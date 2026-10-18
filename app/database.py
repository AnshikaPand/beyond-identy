"""
Database connection setup.
Uses SQLite for local/dev by default (mock data phase from your project timeline).
Swap DATABASE_URL to a Postgres URL later for the "real data" phase — no other code changes needed.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DEFAULT_DB_FILE = BASE_DIR / "beyond_identity.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_FILE.as_posix()}")

# check_same_thread only needed for SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_sqlite_columns(target_engine=None):
    """Lightweight SQLite schema migration for columns added without Alembic."""
    eng = target_engine or engine
    try:
        with eng.connect() as conn:
            cursor = conn.connection.cursor()
            
            # Check users table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(users)")
                cols = {row[1]: row for row in cursor.fetchall()}
                if "is_verified" not in cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 1")
                if "google_id" not in cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN google_id VARCHAR")
                if "auth_provider" not in cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN auth_provider VARCHAR DEFAULT 'local'")

            # Check incident_reports table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='incident_reports'")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(incident_reports)")
                inc_cols = {row[1]: row for row in cursor.fetchall()}
                if "public_visible" not in inc_cols:
                    cursor.execute("ALTER TABLE incident_reports ADD COLUMN public_visible BOOLEAN DEFAULT 1")
                if "reporter_consent_public" not in inc_cols:
                    cursor.execute("ALTER TABLE incident_reports ADD COLUMN reporter_consent_public BOOLEAN DEFAULT 0")
                if "public_summary" not in inc_cols:
                    cursor.execute("ALTER TABLE incident_reports ADD COLUMN public_summary TEXT")
                if "entity_type" not in inc_cols:
                    cursor.execute("ALTER TABLE incident_reports ADD COLUMN entity_type VARCHAR")

            conn.connection.commit()
    except Exception:
        pass


ensure_sqlite_columns()


def get_db():
    """FastAPI dependency: yields a DB session per request, closes it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

