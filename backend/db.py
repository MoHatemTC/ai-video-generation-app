"""
Database engine/session setup.

Uses SQLite by default (see .env.example -> DATABASE_URL), as recommended
in the PRD for internship-stage local development. Swappable to Postgres
later by changing DATABASE_URL only -- no code changes needed.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./video_studio.db")

# SQLite needs this flag when used from multiple threads (FastAPI workers).
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables if they don't exist. Called once on app startup."""
    # Import models here so they're registered on Base.metadata before create_all.
    from backend.models import db_models  # noqa: F401
    Base.metadata.create_all(bind=engine)
