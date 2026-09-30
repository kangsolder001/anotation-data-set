"""
database.py — SQLAlchemy engine, session, dan metadata.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://annotation_user:password@localhost:5432/annotation_db")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
metadata = MetaData()


def get_db():
    """Dependency: yield DB session, pastikan selalu ditutup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
