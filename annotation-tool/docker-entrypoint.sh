#!/bin/bash
# docker-entrypoint.sh
# Dijalankan setiap container app start:
#   1. Tunggu PostgreSQL benar-benar siap menerima koneksi
#   2. Buat tabel (idempoten via CREATE TABLE IF NOT EXISTS)
#   3. Import CSV ke database (idempoten via ON CONFLICT DO NOTHING)
#   4. Jalankan Uvicorn

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 Annotation Tool — Starting up"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Tunggu PostgreSQL siap ─────────────────────────────────────────────────
echo ""
echo "⏳ Menunggu database siap..."

# Coba koneksi DB sampai berhasil (max 30 detik)
MAX_WAIT=30
WAITED=0
until python3 -c "
import os, sys
from sqlalchemy import create_engine, text
try:
    engine = create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as c:
        c.execute(text('SELECT 1'))
    print('  ✅ Database siap!')
except Exception as e:
    print(f'  ⏳ Belum siap: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1; do
    WAITED=$((WAITED + 2))
    if [ "$WAITED" -ge "$MAX_WAIT" ]; then
        echo "❌ Timeout: database tidak merespons setelah ${MAX_WAIT}s"
        exit 1
    fi
    sleep 2
done

# ── 2. Buat tabel ─────────────────────────────────────────────────────────────
echo ""
echo "🗄️  Membuat tabel database..."
python3 -c "
import sys
sys.path.insert(0, '/app')
from app.models import create_tables
create_tables()
print('  ✅ Tabel siap (CREATE TABLE IF NOT EXISTS)')
"

# ── 3. Import CSV ─────────────────────────────────────────────────────────────
CSV_PATH="/app/data/gold_set_manual.csv"
if [ -f "$CSV_PATH" ]; then
    echo ""
    echo "📂 Import dataset CSV..."
    python3 /app/scripts/import_csv.py --csv "$CSV_PATH"
else
    echo ""
    echo "⚠️  File CSV tidak ditemukan di $CSV_PATH, import dilewati."
    echo "   Untuk import manual: docker compose exec app python scripts/import_csv.py --csv /app/data/gold_set_manual.csv"
fi

# ── 4. Jalankan server ────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🌐 Menjalankan Uvicorn di port 8000"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --loop uvloop \
    --no-access-log
