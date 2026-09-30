"""
models.py — Definisi tabel SQLAlchemy Core.
"""

from sqlalchemy import (
    Table, Column, Integer, String, Float, Text,
    DateTime, ForeignKey, Boolean, func
)
from app.database import metadata, engine


# ── Tabel annotators ──────────────────────────────────────────────────────────
annotators = Table(
    "annotators",
    metadata,
    Column("id",            Integer,     primary_key=True, autoincrement=True),
    Column("nama",          String(100), nullable=False),
    Column("pekerjaan",     String(100), nullable=False),
    Column("umur",          Integer,     nullable=False),
    Column("email",         String(150), nullable=False, unique=True),
    Column("password_hash", Text,        nullable=False),
    Column("is_admin",      Boolean,     nullable=False, server_default="false"),
    Column("created_at",    DateTime,    server_default=func.now()),
)

# ── Tabel dataset ─────────────────────────────────────────────────────────────
dataset = Table(
    "dataset",
    metadata,
    Column("id",             Integer,    primary_key=True, autoincrement=True),
    Column("comment_id",     String(64), nullable=False, unique=True),
    Column("keyword_search", Text),
    Column("cleaned_text",   Text,       nullable=False),
    Column("lex_label",      String(10)),
    Column("bert_label",     String(10)),
    Column("bert_conf",      Float),
    Column("label_manual",   String(10), default=None),
    Column("annotator_id",   Integer,    ForeignKey("annotators.id"), default=None),
    Column("annotated_at",   DateTime,   default=None),
)


def create_tables():
    """Buat semua tabel jika belum ada."""
    metadata.create_all(engine)
