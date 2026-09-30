#!/usr/bin/env python3
"""
scripts/import_csv.py
─────────────────────
Script sekali-jalan untuk mengimpor gold_set_manual.csv ke tabel dataset PostgreSQL.

Cara menjalankan (dari direktori annotation-tool/):
    source venv/bin/activate
    python scripts/import_csv.py --csv ../gold_set_manual.csv

Atau dengan path custom:
    python scripts/import_csv.py --csv /path/to/gold_set_manual.csv
"""

import sys
import os
import csv
import argparse
from pathlib import Path

# Pastikan kita bisa import dari app/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.database import engine
from app.models import create_tables, dataset
from sqlalchemy import text


def import_csv(csv_path: str):
    csv_file = Path(csv_path).resolve()
    if not csv_file.exists():
        print(f"❌ File tidak ditemukan: {csv_file}")
        sys.exit(1)

    print(f"📂 Membaca file: {csv_file}")

    # Buat tabel jika belum ada
    create_tables()
    print("✅ Tabel database siap.")

    inserted = 0
    skipped = 0

    with engine.begin() as conn:
        with open(csv_file, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            expected_cols = {"comment_id", "keyword_search", "cleaned_text",
                             "lex_label", "bert_label", "bert_conf", "label_manual"}
            actual_cols = set(reader.fieldnames or [])
            missing = expected_cols - actual_cols - {"label_manual"}
            if missing:
                print(f"❌ Kolom yang hilang di CSV: {missing}")
                sys.exit(1)

            batch = []
            for i, row in enumerate(reader, 1):
                comment_id = (row.get("comment_id") or "").strip()
                if not comment_id:
                    print(f"  ⚠️  Baris {i}: comment_id kosong, dilewati.")
                    skipped += 1
                    continue

                cleaned_text = (row.get("cleaned_text") or "").strip()
                if not cleaned_text:
                    print(f"  ⚠️  Baris {i} ({comment_id}): cleaned_text kosong, dilewati.")
                    skipped += 1
                    continue

                bert_conf_raw = row.get("bert_conf", "").strip()
                try:
                    bert_conf = float(bert_conf_raw) if bert_conf_raw else None
                except ValueError:
                    bert_conf = None

                batch.append({
                    "comment_id":     comment_id,
                    "keyword_search": (row.get("keyword_search") or "").strip() or None,
                    "cleaned_text":   cleaned_text,
                    "lex_label":      (row.get("lex_label") or "").strip() or None,
                    "bert_label":     (row.get("bert_label") or "").strip() or None,
                    "bert_conf":      bert_conf,
                    "label_manual":   None,
                    "annotator_id":   None,
                    "annotated_at":   None,
                })

                # Insert per batch 50
                if len(batch) >= 50:
                    n = _insert_batch(conn, batch)
                    inserted += n
                    skipped += len(batch) - n
                    batch = []

            # Sisa batch
            if batch:
                n = _insert_batch(conn, batch)
                inserted += n
                skipped += len(batch) - n

    print(f"\n🎉 Import selesai!")
    print(f"   ✅ Berhasil dimasukkan : {inserted} baris")
    print(f"   ⏭️  Dilewati (duplikat) : {skipped} baris")


def _insert_batch(conn, batch: list) -> int:
    """Insert batch dengan ON CONFLICT DO NOTHING (idempoten)."""
    if not batch:
        return 0

    # Build INSERT ... ON CONFLICT DO NOTHING
    cols = ["comment_id", "keyword_search", "cleaned_text",
            "lex_label", "bert_label", "bert_conf",
            "label_manual", "annotator_id", "annotated_at"]

    placeholders = ", ".join(
        f"(:comment_id_{i}, :keyword_search_{i}, :cleaned_text_{i}, "
        f":lex_label_{i}, :bert_label_{i}, :bert_conf_{i}, "
        f":label_manual_{i}, :annotator_id_{i}, :annotated_at_{i})"
        for i in range(len(batch))
    )

    params = {}
    for i, row in enumerate(batch):
        params[f"comment_id_{i}"]     = row["comment_id"]
        params[f"keyword_search_{i}"] = row["keyword_search"]
        params[f"cleaned_text_{i}"]   = row["cleaned_text"]
        params[f"lex_label_{i}"]      = row["lex_label"]
        params[f"bert_label_{i}"]     = row["bert_label"]
        params[f"bert_conf_{i}"]      = row["bert_conf"]
        params[f"label_manual_{i}"]   = row["label_manual"]
        params[f"annotator_id_{i}"]   = row["annotator_id"]
        params[f"annotated_at_{i}"]   = row["annotated_at"]

    sql = text(f"""
        INSERT INTO dataset
            (comment_id, keyword_search, cleaned_text,
             lex_label, bert_label, bert_conf,
             label_manual, annotator_id, annotated_at)
        VALUES {placeholders}
        ON CONFLICT (comment_id) DO NOTHING
    """)

    result = conn.execute(sql, params)
    return result.rowcount


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import gold_set_manual.csv ke PostgreSQL")
    parser.add_argument(
        "--csv",
        default="../gold_set_manual.csv",
        help="Path ke file CSV (default: ../gold_set_manual.csv)",
    )
    args = parser.parse_args()
    import_csv(args.csv)
