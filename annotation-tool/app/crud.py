"""
crud.py — Query database untuk annotators dan dataset.
"""

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, update, func, and_
from app.models import annotators, dataset


# ═══════════════════════════════════════════════════════════
# ANNOTATORS
# ═══════════════════════════════════════════════════════════

def get_annotator_by_email(db: Session, email: str) -> dict | None:
    row = db.execute(
        select(annotators).where(annotators.c.email == email)
    ).mappings().first()
    return dict(row) if row else None


def get_annotator_by_id(db: Session, annotator_id: int) -> dict | None:
    row = db.execute(
        select(annotators).where(annotators.c.id == annotator_id)
    ).mappings().first()
    return dict(row) if row else None


def create_annotator(
    db: Session,
    nama: str,
    pekerjaan: str,
    umur: int,
    email: str,
    password_hash: str,
    is_admin: bool = False,
) -> int:
    existing = get_annotator_by_email(db, email)
    if existing:
        raise ValueError("Email sudah terdaftar.")
    result = db.execute(
        annotators.insert().values(
            nama=nama,
            pekerjaan=pekerjaan,
            umur=umur,
            email=email,
            password_hash=password_hash,
            is_admin=is_admin,
        )
    )
    db.commit()
    return result.inserted_primary_key[0]


def ensure_admin(
    db: Session,
    nama: str,
    pekerjaan: str,
    umur: int,
    email: str,
    password_hash: str,
) -> None:
    """
    Buat akun admin jika belum ada, atau update password jika sudah ada.
    Idempoten — aman dijalankan berulang saat startup.
    """
    existing = get_annotator_by_email(db, email)
    if existing:
        db.execute(
            annotators.update()
            .where(annotators.c.email == email)
            .values(is_admin=True, password_hash=password_hash)
        )
        db.commit()
        return
    db.execute(
        annotators.insert().values(
            nama=nama,
            pekerjaan=pekerjaan,
            umur=umur,
            email=email,
            password_hash=password_hash,
            is_admin=True,
        )
    )
    db.commit()


# ═══════════════════════════════════════════════════════════
# DATASET
# ═══════════════════════════════════════════════════════════

VALID_LABELS = {"positif", "negatif", "netral"}


def get_next_unannotated(db: Session) -> dict | None:
    row = db.execute(
        select(dataset)
        .where(dataset.c.annotator_id == None)  # noqa: E711
        .order_by(dataset.c.id)
        .limit(1)
    ).mappings().first()
    return dict(row) if row else None


def get_item_by_comment_id(db: Session, comment_id: str) -> dict | None:
    row = db.execute(
        select(dataset).where(dataset.c.comment_id == comment_id)
    ).mappings().first()
    return dict(row) if row else None


def submit_annotation(
    db: Session,
    comment_id: str,
    annotator_id: int,
    label: str,
) -> bool:
    """
    Idempoten: hanya update jika annotator_id IS NULL.
    Return True jika berhasil, False jika sudah dianotasi orang lain.
    """
    if label not in VALID_LABELS:
        raise ValueError(f"Label tidak valid: {label}")
    result = db.execute(
        update(dataset)
        .where(
            and_(
                dataset.c.comment_id == comment_id,
                dataset.c.annotator_id == None,  # noqa: E711
            )
        )
        .values(
            label_manual=label,
            annotator_id=annotator_id,
            annotated_at=datetime.utcnow(),
        )
    )
    db.commit()
    return result.rowcount > 0


def update_annotation(
    db: Session,
    comment_id: str,
    annotator_id: int,
    label: str,
    is_admin: bool = False,
) -> bool:
    """
    Update label anotasi yang sudah dibuat oleh annotator ini.
    Hanya annotator pemilik anotasi (atau admin) yang berhak mengubah.
    """
    if label not in VALID_LABELS:
        raise ValueError(f"Label tidak valid: {label}")

    condition = dataset.c.comment_id == comment_id
    if not is_admin:
        condition = and_(condition, dataset.c.annotator_id == annotator_id)

    result = db.execute(
        update(dataset)
        .where(condition)
        .values(
            label_manual=label,
            annotated_at=datetime.utcnow(),
        )
    )
    db.commit()
    return result.rowcount > 0


# ═══════════════════════════════════════════════════════════
# STATISTIK
# ═══════════════════════════════════════════════════════════

def get_stats(db: Session, annotator_id: int) -> dict:
    total = db.execute(select(func.count()).select_from(dataset)).scalar()
    done_all = db.execute(
        select(func.count()).select_from(dataset)
        .where(dataset.c.annotator_id != None)  # noqa: E711
    ).scalar()
    done_by_me = db.execute(
        select(func.count()).select_from(dataset)
        .where(dataset.c.annotator_id == annotator_id)
    ).scalar()
    remaining = total - done_all

    label_counts = {lbl: 0 for lbl in VALID_LABELS}
    rows = db.execute(
        select(dataset.c.label_manual, func.count().label("cnt"))
        .where(dataset.c.annotator_id == annotator_id)
        .group_by(dataset.c.label_manual)
    ).all()
    for row in rows:
        if row.label_manual in label_counts:
            label_counts[row.label_manual] = row.cnt

    return {
        "total":       total,
        "done_all":    done_all,
        "done_by_me":  done_by_me,
        "remaining":   remaining,
        "label_counts": label_counts,
        "pct_all":     round(done_all / total * 100, 1) if total else 0,
        "pct_me":      round(done_by_me / total * 100, 1) if total else 0,
    }


def get_my_annotations(db: Session, annotator_id: int, limit: int = 20, offset: int = 0) -> list[dict]:
    rows = db.execute(
        select(dataset)
        .where(dataset.c.annotator_id == annotator_id)
        .order_by(dataset.c.annotated_at.desc())
        .limit(limit)
        .offset(offset)
    ).mappings().all()
    return [dict(r) for r in rows]
