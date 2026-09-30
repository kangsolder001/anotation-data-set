#!/bin/bash
# setup_db.sh — Script setup database PostgreSQL untuk Annotation Tool
# Jalankan sekali sebagai user dengan akses sudo

set -e

echo "🐘 Setup PostgreSQL untuk Annotation Tool"
echo "========================================="

# 1. Pastikan PostgreSQL berjalan
echo ""
echo "1️⃣  Menjalankan PostgreSQL..."
sudo service postgresql start
sleep 2
echo "   ✅ PostgreSQL aktif"

# 2. Buat user dan database
echo ""
echo "2️⃣  Membuat user dan database..."

sudo -u postgres psql <<'SQL'
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'annotation_user') THEN
        CREATE USER annotation_user WITH PASSWORD 'annotation_pass_2024';
        RAISE NOTICE 'User annotation_user dibuat.';
    ELSE
        RAISE NOTICE 'User annotation_user sudah ada.';
    END IF;
END
$$;

SELECT 'Database check' as status;
SQL

sudo -u postgres psql -c "
SELECT pg_database.datname FROM pg_database WHERE datname = 'annotation_db'
" | grep -q annotation_db && echo "Database sudah ada" || \
sudo -u postgres createdb annotation_db -O annotation_user

echo "   ✅ Database 'annotation_db' siap"

# 3. Aktifkan venv dan jalankan import CSV
echo ""
echo "3️⃣  Membuat .env dari template..."
if [ ! -f .env ]; then
    cp .env.example .env
    # Generate random secret key
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/ganti_dengan_string_random_panjang_minimal_32_karakter/$SECRET/" .env
    sed -i "s/annotation_user:password/annotation_user:annotation_pass_2024/" .env
    echo "   ✅ File .env dibuat dengan SECRET_KEY random"
else
    echo "   ℹ️  File .env sudah ada, dilewati"
fi

# 4. Import CSV
echo ""
echo "4️⃣  Import dataset CSV ke database..."
source venv/bin/activate
python scripts/import_csv.py --csv ../gold_set_manual.csv

echo ""
echo "✅ Setup selesai!"
echo ""
echo "Jalankan server dengan:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "Buka browser: http://localhost:8000"
