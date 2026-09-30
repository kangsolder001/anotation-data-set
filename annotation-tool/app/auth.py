"""
auth.py — Password hashing, verifikasi, dan session cookie.
Menggunakan bcrypt langsung (kompatibel ARM / Raspberry Pi).
"""

import os
import bcrypt
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, HTTPException, status

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "default-insecure-secret-key-change-me")
SESSION_COOKIE = "annotation_session"
SESSION_MAX_AGE = 60 * 60 * 8  # 8 jam


# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    secret = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(secret, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


# ── Session (signed cookie) ───────────────────────────────────────────────────
_serializer = URLSafeTimedSerializer(SECRET_KEY, salt="annotation-session")


def create_session_token(annotator_id: int, is_admin: bool = False) -> str:
    """Buat signed token berisi annotator_id dan is_admin."""
    return _serializer.dumps({"id": annotator_id, "admin": is_admin})


def decode_session_token(token: str) -> dict | None:
    try:
        return _serializer.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def get_current_annotator_id(request: Request) -> int:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    data = decode_session_token(token)
    if not data:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return data["id"]


def require_admin(request: Request) -> int:
    """Dependency: hanya izinkan admin. Redirect 403 jika bukan admin."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    data = decode_session_token(token)
    if not data:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    if not data.get("admin", False):
        raise HTTPException(status_code=403, detail="Akses ditolak: hanya admin.")
    return data["id"]
