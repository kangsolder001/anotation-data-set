"""
main.py — FastAPI routes, template rendering, session handling.
"""

import os
import csv
import io
from fastapi import FastAPI, Request, Form, Depends, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select
from dotenv import load_dotenv

from app.database import get_db
from app.models import create_tables, dataset as ds, annotators as ann
from app import crud, auth

load_dotenv()

app = FastAPI(title="Annotation Tool", docs_url=None, redoc_url=None)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    create_tables()
    _seed_admin()


def _seed_admin():
    """Buat akun admin dari environment variable (idempoten)."""
    admin_email    = os.getenv("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
    admin_nama     = os.getenv("ADMIN_NAME", "Administrator").strip()

    if not admin_email or not admin_password:
        return  # tidak dikonfigurasi, skip

    db = next(get_db())
    try:
        crud.ensure_admin(
            db=db,
            nama=admin_nama,
            pekerjaan="Admin",
            umur=0,
            email=admin_email,
            password_hash=auth.hash_password(admin_password),
        )
        print(f"  [Admin] Akun admin '{admin_email}' siap.")
    finally:
        db.close()


# ── Helper ────────────────────────────────────────────────────────────────────
def _get_annotator_or_redirect(request: Request, db: Session):
    token = request.cookies.get(auth.SESSION_COOKIE)
    if not token:
        return None, RedirectResponse(url="/login", status_code=303)
    data = auth.decode_session_token(token)
    if not data:
        return None, RedirectResponse(url="/login", status_code=303)
    annotator = crud.get_annotator_by_id(db, data["id"])
    if not annotator:
        return None, RedirectResponse(url="/login", status_code=303)
    # Sertakan is_admin dari token (lebih efisien dari query DB)
    annotator = dict(annotator)
    annotator["is_admin"] = data.get("admin", False)
    return annotator, None


# ═══════════════════════════════════════════════════════════
# ROOT
# ═══════════════════════════════════════════════════════════
@app.get("/", response_class=HTMLResponse)
def root(request: Request, db: Session = Depends(get_db)):
    annotator, redirect = _get_annotator_or_redirect(request, db)
    if redirect:
        return redirect
    return RedirectResponse(url="/annotate", status_code=303)


# ═══════════════════════════════════════════════════════════
# REGISTER
# ═══════════════════════════════════════════════════════════
@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request, error: str = ""):
    return templates.TemplateResponse("register.html", {"request": request, "error": error})


@app.post("/register", response_class=HTMLResponse)
def register_post(
    request: Request,
    nama: str = Form(...),
    pekerjaan: str = Form(...),
    umur: int = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
    db: Session = Depends(get_db),
):
    errors = []
    if not nama.strip():          errors.append("Nama tidak boleh kosong.")
    if not pekerjaan.strip():     errors.append("Pekerjaan tidak boleh kosong.")
    if umur < 1 or umur > 120:   errors.append("Umur tidak valid.")
    if "@" not in email:          errors.append("Format email tidak valid.")
    if len(password) < 8:         errors.append("Password minimal 8 karakter.")
    if password != password2:     errors.append("Konfirmasi password tidak cocok.")

    form = {"nama": nama, "pekerjaan": pekerjaan, "umur": umur, "email": email}

    if errors:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": " ".join(errors), "form": form},
        )
    try:
        crud.create_annotator(
            db, nama.strip(), pekerjaan.strip(), umur,
            email.strip().lower(), auth.hash_password(password),
        )
    except ValueError as e:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": str(e), "form": form},
        )
    return RedirectResponse(url="/login?success=Akun+berhasil+dibuat", status_code=303)


# ═══════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = "", success: str = ""):
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": error, "success": success}
    )


@app.post("/login", response_class=HTMLResponse)
def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    clean_email = email.strip().lower()
    clean_pass = password.strip()
    annotator = crud.get_annotator_by_email(db, clean_email)
    
    # Coba verifikasi password asli dan password tanpa leading/trailing whitespace
    is_valid = False
    if annotator:
        if auth.verify_password(password, annotator["password_hash"]) or auth.verify_password(clean_pass, annotator["password_hash"]):
            is_valid = True

    if not annotator or not is_valid:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Email atau password salah.", "success": ""},
        )
    token = auth.create_session_token(annotator["id"], is_admin=annotator["is_admin"])
    resp = RedirectResponse(url="/annotate", status_code=303)
    resp.set_cookie(
        key=auth.SESSION_COOKIE, value=token,
        httponly=True, samesite="lax", max_age=auth.SESSION_MAX_AGE,
    )
    return resp


# ═══════════════════════════════════════════════════════════
# LOGOUT
# ═══════════════════════════════════════════════════════════
@app.post("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(auth.SESSION_COOKIE)
    return resp


# ═══════════════════════════════════════════════════════════
# ANOTASI
# ═══════════════════════════════════════════════════════════
@app.get("/annotate", response_class=HTMLResponse)
def annotate_page(request: Request, msg: str = "", db: Session = Depends(get_db)):
    annotator, redirect = _get_annotator_or_redirect(request, db)
    if redirect:
        return redirect
    item  = crud.get_next_unannotated(db)
    stats = crud.get_stats(db, annotator["id"])
    return templates.TemplateResponse(
        "annotate.html",
        {"request": request, "annotator": annotator, "item": item, "stats": stats, "msg": msg},
    )


@app.post("/annotate/{comment_id}", response_class=HTMLResponse)
def annotate_post(
    request: Request,
    comment_id: str,
    label: str = Form(...),
    db: Session = Depends(get_db),
):
    annotator, redirect = _get_annotator_or_redirect(request, db)
    if redirect:
        return redirect
    if label not in crud.VALID_LABELS:
        return RedirectResponse(url="/annotate?msg=Label+tidak+valid", status_code=303)
    success = crud.submit_annotation(db, comment_id, annotator["id"], label)
    if not success:
        return RedirectResponse(
            url="/annotate?msg=Item+sudah+dianotasi+anotator+lain,+lanjut+ke+item+berikutnya",
            status_code=303,
        )
    return RedirectResponse(url="/annotate", status_code=303)


# ═══════════════════════════════════════════════════════════
# PROGRESS
# ═══════════════════════════════════════════════════════════
@app.get("/progress", response_class=HTMLResponse)
def progress_page(request: Request, page: int = 1, db: Session = Depends(get_db)):
    annotator, redirect = _get_annotator_or_redirect(request, db)
    if redirect:
        return redirect
    stats = crud.get_stats(db, annotator["id"])
    per_page = 20
    offset = (page - 1) * per_page
    my_annotations = crud.get_my_annotations(db, annotator["id"], limit=per_page, offset=offset)
    total_pages = max(1, (stats["done_by_me"] + per_page - 1) // per_page)
    return templates.TemplateResponse(
        "progress.html",
        {
            "request": request,
            "annotator": annotator,
            "stats": stats,
            "my_annotations": my_annotations,
            "page": page,
            "total_pages": total_pages,
        },
    )


# ═══════════════════════════════════════════════════════════
# EXPORT CSV — hanya admin
# ═══════════════════════════════════════════════════════════
@app.get("/export")
def export_csv(request: Request, db: Session = Depends(get_db)):
    annotator, redirect = _get_annotator_or_redirect(request, db)
    if redirect:
        return redirect
    if not annotator.get("is_admin"):
        raise HTTPException(status_code=403, detail="Akses ditolak: hanya admin.")

    rows = db.execute(
        select(
            ds.c.comment_id, ds.c.keyword_search, ds.c.cleaned_text,
            ds.c.lex_label, ds.c.bert_label, ds.c.bert_conf,
            ds.c.label_manual, ds.c.annotated_at,
            ann.c.nama.label("annotator_nama"),
            ann.c.email.label("annotator_email"),
        )
        .join(ann, ds.c.annotator_id == ann.c.id, isouter=True)
        .order_by(ds.c.id)
    ).mappings().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "comment_id", "keyword_search", "cleaned_text",
        "lex_label", "bert_label", "bert_conf",
        "label_manual", "annotated_at",
        "annotator_nama", "annotator_email",
    ])
    for r in rows:
        writer.writerow([
            r["comment_id"],
            r["keyword_search"] or "",
            r["cleaned_text"],
            r["lex_label"] or "",
            r["bert_label"] or "",
            r["bert_conf"] or "",
            r["label_manual"] or "",
            r["annotated_at"] or "",
            r["annotator_nama"] or "",
            r["annotator_email"] or "",
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=gold_set_annotated.csv"},
    )
