# Annotation Tool

Website anotasi dataset sentimen berbasis **FastAPI + PostgreSQL**, dideploy dengan **Docker Compose**.

> 🍓 Dioptimalkan untuk **Raspberry Pi** (ARM64) dengan container super ringan (`python:3.11-slim` + `postgres:16-alpine`).  
> 📱 Desain **Mobile-First** & **Eye-Friendly** (soft warm palette, nyaman dibaca lama di layar HP maupun laptop).

---

## 📱 Fitur & Tampilan

- **Mobile-Friendly:** Input mencegah auto-zoom di iOS/Android, tombol label besar (touch-friendly min 52px), tabel dengan horizontal scrolling, sticky navigation bar.
- **Eye-Friendly Palette:** Warna background krem hangat (`#f4f1eb`), teks warna cokelat gelap (`#38342c`), tombol warna muted soft (bukan neon), mendukung dark mode otomatis.
- **Fokus Anotasi:** Menghilangkan noise (label otomatis LEX/BERT & ID item disembunyikan agar anotasi murni objektif).
- **Akun Admin & Export:**
  - Hanya akun admin yang dapat mendownload hasil anotasi dalam bentuk CSV (`/export`).
  - Anotator biasa fokus pada pengisian dan monitoring progres pribadi.
- **Idempoten:** Satu data hanya bisa dianotasi oleh 1 anotator, tidak akan terjadi double annotation.

---

## 🔐 Kredensial Default

### Akun Admin
- **Email:** `admin@kgs.id`
- **Password:** `admin123`
- **Akses:** Halaman Anotasi, Monitoring Progress, Download CSV (`/export`)

### Pendaftaran Anotator Baru
Anotator dapat mendaftar langsung di halaman `/register` dengan mengisi:
- Nama Lengkap
- Pekerjaan
- Umur
- Email
- Password (dihash dengan bcrypt)

---

## 🚀 Akses Website

- Dari jaringan lokal: **http://192.168.1.111:3005**
- Dari localhost (jika dijalankan lokal): **http://localhost:3005**

---

## 🛠️ Perintah Docker Compose (di Raspberry Pi)

```bash
# Masuk ke folder
cd ~/annotation-tool

# Cek status container
docker compose ps

# Lihat logs aplikasi secara realtime
docker compose logs -f app

# Restart aplikasi
docker compose restart app

# Stop aplikasi
docker compose down

# Rebuild jika ada update kode
docker compose up -d --build
```
