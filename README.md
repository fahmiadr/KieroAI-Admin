# KIERO OPS Center

> **Dashboard monitoring & manajemen service** untuk lingkungan development dan production.  
> Dibangun dengan Flask.

---

## Daftar Isi

- [Arsitektur Sistem](#arsitektur-sistem)
- [Struktur Direktori](#struktur-direktori)
- [Konfigurasi](#konfigurasi)
- [Alur Kerja Aplikasi](#alur-kerja-aplikasi)
- [Fitur Utama](#fitur-utama)
- [API Routes](#api-routes)
- [Cara Menjalankan](#cara-menjalankan)
- [Tech Stack](#tech-stack)

---

## Arsitektur Sistem

```
┌──────────────────────────────────────────────────────────────────────┐
│                          KIERO OPS CENTER                           │
│                                                                      │
│  ┌──────────┐    ┌─────────────┐    ┌───────────────────────────┐   │
│  │  Browser  │───▶│  Flask App  │───▶│  Service Registry (JSON)  │   │
│  │  (UI)     │◀───│   app.py    │    │  registry_dev.json        │   │
│  └──────────┘    │             │    │  registry_prod.json       │   │
│                   │             │    └───────────────────────────┘   │
│                   │             │                                     │
│                   │             │    ┌───────────────────────────┐   │
│                   │             │───▶│  App Config (JSON)        │   │
│                   │             │    │  config_app.json          │   │
│                   │             │    └───────────────────────────┘   │
│                   │             │                                     │
│                   │             │    ┌───────────────────────────┐   │
│                   │             │───▶│  System (psutil)          │   │
│                   └─────────────┘    │  CPU / Memory / Disk      │   │
│                                      │  Process Management       │   │
│                                      └───────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Struktur Direktori

```
kieroOPS/
├── app.py                 # Aplikasi utama Flask (semua route)

├── config_app.json        # Konfigurasi aplikasi (admin, theme, dll)
├── .env                   # Environment variables
│
├── configs/
│   ├── registry_dev.json  # Daftar service untuk development
│   └── registry_prod.json # Daftar service untuk production
│
├── static/
│   └── style.css          # Stylesheet utama (dark theme, glassmorphism)
│
├── templates/
│   ├── layout.html        # Base template (sidebar, topbar)
│   ├── login.html         # Halaman login
│   ├── dashboard.html     # Dashboard utama (stats + service cards)
│   ├── services.html      # Service Manager (CRUD service)
│   ├── settings.html      # Pengaturan (env, admin, registry editor)
│   ├── logs.html          # Log Viewer (IDE-like interface)
│   └── editor.html        # Config file editor
│
└── logs/                  # Direktori log (auto-generated)
```

---

## Konfigurasi

### 1. Environment Variables (`.env`)

| Variable | Deskripsi | Contoh |
|----------|-----------|--------|
| `APP_ENV` | Environment aktif (`development` / `production`) | `development` |
| `APP_PORT` | Port Flask server | `5006` |
| `SECRET_KEY` | Secret key untuk session Flask | `kunci_rahasia_123` |
| `KAWALO_BACKEND_PATH` | Path ke backend project | `C:/laragon/www/kawalo-web-admin/backend` |
| `KAWALO_FRONTEND_PATH` | Path ke frontend project | `C:/laragon/www/kawalo-web-admin/frontend` |


### 2. App Config (`config_app.json`)

File ini menyimpan konfigurasi yang bisa diubah lewat UI Settings:

```json
{
    "admin_username": "admin",
    "admin_password": "password_aman_ops",
    "dashboard_title": "KIERO Ops Center",
    "theme_mode": "dark",
    "refresh_rate_seconds": 10,
    "enable_notifications": true,
    "max_log_lines": 100,
    "maintenance_mode": false
}
```

| Field | Deskripsi |
|-------|-----------|
| `admin_username` | Username untuk login |
| `admin_password` | Password untuk login (plain text) |
| `dashboard_title` | Judul yang tampil di dashboard |
| `theme_mode` | Mode tema (`dark`) |
| `refresh_rate_seconds` | Interval refresh data |
| `max_log_lines` | Jumlah baris log yang ditampilkan |
| `maintenance_mode` | Flag mode maintenance |

### 3. Service Registry (`configs/registry_*.json`)

Setiap service didaftarkan dengan struktur berikut:

```json
{
    "id": "kawalo_backend",
    "name": "Kawalo Backend API",
    "type": "node",
    "category": "backend",
    "group": "Kawalo Core",
    "icon": "bi-server",
    "url": "http://localhost:3000",
    "command_start": "cd C:/path/to/backend && npm start",
    "command_stop": "taskkill /F /IM node.exe",
    "check_keyword": "node",
    "log_file": "C:/path/to/logs/backend.log",
    "config_file": "C:/path/to/backend/.env",
    "web_directory": "C:/path/to/backend",
    "status": "Stopped"
}
```

| Field | Deskripsi |
|-------|-----------|
| `id` | Identifier unik service |
| `name` | Nama tampilan service |
| `type` | Tipe service (`node`, `python`, `laragon`, `docker`, `dummy`) |
| `category` | Kategori (`backend` / `frontend`) |
| `group` | Pengelompokan di UI (e.g., "Kawalo Core", "Infrastructure") |
| `icon` | Bootstrap Icons class untuk ikon dashboard |
| `url` | URL akses service |
| `command_start` | Perintah shell untuk menjalankan service |
| `command_stop` | Perintah shell untuk menghentikan service |
| `check_keyword` | Keyword untuk cek status proses via `psutil` |
| `log_file` | Path ke file log utama service |
| `config_file` | Path ke file konfigurasi service (e.g., `.env`) |
| `web_directory` | Path ke direktori root project |
| `status` | Status terakhir (`Running` / `Stopped`) |

---

## Alur Kerja Aplikasi

### Alur Autentikasi

```
┌─────────┐     GET /login      ┌──────────┐
│  User   │────────────────────▶│  Login   │
│         │                     │  Page    │
│         │  POST /login        │          │
│         │  username + password│          │
│         │────────────────────▶│          │
│         │                     └────┬─────┘
│         │                          │
│         │              ┌───────────▼───────────┐
│         │              │  Cek config_app.json  │
│         │              │  admin_username ==?    │
│         │              │  admin_password ==?    │
│         │              └───────────┬───────────┘
│         │                    ┌─────┴─────┐
│         │                  Valid?      Invalid?
│         │                    │            │
│         │          session['logged_in']   │
│         │◀───── redirect / ──┘    flash('error')
│         │                         │
│         │◀── render login.html ───┘
└─────────┘
```

**Middleware (`require_login`):** Setiap request (kecuali `/login` dan `/static`) dicek apakah `session['logged_in']` ada. Jika tidak, user di-redirect ke halaman login.

---

### Alur Dashboard

```
GET /
  │
  ├── load_registry()          ← Baca registry_dev.json atau registry_prod.json
  │     │                        (tergantung current_env)
  │     ▼
  ├── get_system_stats()       ← psutil: CPU%, Memory, Disk usage
  │     │
  │     ▼
  └── render dashboard.html    ← Tampilkan stats + daftar service cards
        │
        │  Setiap service card menampilkan:
        │  ✦ Nama + ikon + tipe
        │  ✦ Status (Running/Stopped)
        │  ✦ Tombol: Start | Stop | Logs | Config | Open URL
        │
        ▼
      [User klik Start/Stop]
        │
        GET /action/<service_id>/start  atau  /action/<service_id>/stop
        │
        ├── Ambil command_start atau command_stop dari registry
        ├── Jalankan via subprocess.Popen(command, shell=True)
        ├── Update status di registry JSON
        ├── Simpan ke file
        └── Redirect kembali ke dashboard
```

---

### Alur Log Viewer

```
GET /logs/<service_id>
  │
  ├── Load service dari registry
  ├── Baca 50 baris terakhir dari log_file
  ├── Hitung web_directory (fallback: config_file dir → command_start)
  └── Render logs.html
        │
        │  ┌────────────────────────────────────────────┐
        │  │              LOG VIEWER (IDE-like)           │
        │  │                                              │
        │  │  ┌──────────────┐  ┌───────────────────┐   │
        │  │  │ File Explorer │  │ Log Content Viewer │   │
        │  │  │              │  │                     │   │
        │  │  │ 📁 Log Dir   │  │ [content area]      │   │
        │  │  │ 📁 Web Dir   │  │                     │   │
        │  │  │  📄 file.log │  │ ────────────────── │   │
        │  │  │  📄 app.js   │  │                     │   │
        │  │  └──────────────┘  └───────────────────┘   │
        │  └────────────────────────────────────────────┘
        │
        │  File Explorer memuat data via AJAX:
        │
        ├── GET /logs/<id>/directories     ← Daftar file di log directory
        ├── GET /logs/<id>/web-directories  ← Daftar file di web directory
        ├── GET /logs/<id>/file             ← Isi file log (dalam log dir)
        └── GET /logs/<id>/web-file         ← Isi file web (source code)
```

**Keamanan File Access:**
- File hanya bisa diakses jika berada di dalam `log_dir` atau `web_dir` dari service
- Path dinormalisasi lalu dipastikan `abs_file_path.startswith(abs_allowed_dir)`
- Hidden files (`.`) dan `node_modules` disembunyikan dari file explorer

---



---

### Alur Service Manager

```
GET /services
  │
  ├── Load registry_dev.json → dev_services
  ├── Load registry_prod.json → prod_services
  └── Render services.html
        │
        │  Tampilkan 2 kolom:
        │  ┌─────────────────┐  ┌──────────────────┐
        │  │  Development     │  │  Production       │
        │  │  + Add Service   │  │  + Add Service    │
        │  │                  │  │                   │
        │  │  [service cards] │  │  [service cards]  │
        │  │  Edit | Delete   │  │  Edit | Delete    │
        │  └─────────────────┘  └──────────────────┘
        │
        │  [Klik Add/Edit] → Modal Form
        │
        POST /services/save
        │
        ├── Baca form data (id, name, type, commands, paths, dll)
        ├── Jika original_id ada → Update service lama
        │   Jika tidak → Append service baru
        ├── Simpan ke registry JSON yang sesuai
        └── Redirect ke /services
        │
        GET /services/delete/<env>/<service_id>
        │
        ├── Filter service dari array
        ├── Simpan registry tanpa service tersebut
        └── Redirect ke /services
```

---

### Alur Settings

```
GET /settings
  │
  ├── Load config_app.json → tampilkan di JSON editor
  ├── Load registry_dev.json → tampilkan di textarea
  ├── Load registry_prod.json → tampilkan di textarea
  └── Render settings.html
        │
        │  ┌───────────────────────────────────────┐
        │  │  Settings Page                         │
        │  │                                        │
        │  │  🔀 Environment Switcher               │
        │  │     [Development] [Production]         │
        │  │                                        │
        │  │  ⚙️  Global Config (JSON Editor)       │
        │  │     { admin_username, password, ... }  │
        │  │     [Save Config]                      │
        │  │                                        │
        │  │  📝 Dev Registry (JSON Editor)         │
        │  │     [Save Dev Registry]                │
        │  │                                        │
        │  │  📝 Prod Registry (JSON Editor)        │
        │  │     [Save Prod Registry]               │
        │  └───────────────────────────────────────┘
        │
        POST /settings          ← Save config_app.json
        POST /settings/save-registry/dev   ← Save registry_dev.json
        POST /settings/save-registry/prod  ← Save registry_prod.json
```

---

### Alur Config Editor

```
GET /config/<service_id>
  │
  ├── Load service dari registry
  ├── Baca isi config_file (misal: .env)
  └── Render editor.html
        │
        │  ┌───────────────────────────┐
        │  │  Config Editor             │
        │  │  📄 kawalo_backend.json    │
        │  │                            │
        │  │  [textarea with content]   │
        │  │                            │
        │  │  [Save] [Cancel]           │
        │  └───────────────────────────┘
        │
        POST /config/<service_id>
        │
        ├── Tulis content baru ke config_file
        └── Redirect ke dashboard
```

---

### Alur Environment Switching

```
GET /switch-env/<env_type>
  │
  ├── Validasi env_type ("development" / "production")
  ├── Set global current_env
  └── Redirect ke dashboard
        │
        │  Setelah switch, semua halaman menggunakan
        │  registry yang sesuai (dev/prod)
```

---

## Fitur Utama

| Fitur | Deskripsi |
|-------|-----------|
| **Dashboard** | Monitoring CPU, Memory, Disk secara real-time + daftar service cards |
| **Service Control** | Start/Stop service via shell command dari UI |
| **Service Manager** | CRUD service di registry dev & prod melalui modal form |
| **Log Viewer** | Interface IDE-like dengan file explorer dan syntax highlighting |

| **Config Editor** | Edit file konfigurasi service (`.env`, `.json`) langsung dari browser |
| **Environment Switch** | Toggle antara development dan production |
| **Settings** | Edit admin credentials, app config, dan registry via JSON editor |
| **Static Auth** | Login statis dengan credentials dari `config_app.json` (editable via UI) |

---

## API Routes

### Pages (HTML)

| Method | Route | Fungsi | Auth |
|--------|-------|--------|------|
| `GET/POST` | `/login` | Halaman login | ❌ |
| `GET` | `/logout` | Logout & clear session | ❌ |
| `GET` | `/` | Dashboard utama | ✅ |
| `GET` | `/services` | Service Manager | ✅ |
| `GET/POST` | `/settings` | Halaman pengaturan | ✅ |
| `GET/POST` | `/config/<service_id>` | Editor konfigurasi | ✅ |
| `GET` | `/logs/<service_id>` | Log viewer | ✅ |

### Actions (Redirect)

| Method | Route | Fungsi | Auth |
|--------|-------|--------|------|
| `GET` | `/action/<service_id>/<action>` | Start/Stop service | ✅ |
| `GET` | `/switch-env/<env_type>` | Switch dev/prod | ✅ |
| `POST` | `/services/save` | Simpan/tambah service | ✅ |
| `GET` | `/services/delete/<env>/<id>` | Hapus service | ✅ |
| `POST` | `/settings/save-registry/<type>` | Simpan registry JSON | ✅ |

### API (JSON)

| Method | Route | Fungsi | Auth |
|--------|-------|--------|------|
| `GET` | `/logs/<id>/directories` | List file di log directory | ✅ |
| `GET` | `/logs/<id>/file?path=...` | Baca isi file log | ✅ |
| `GET` | `/logs/<id>/web-directories` | List file di web directory | ✅ |
| `GET` | `/logs/<id>/web-file?path=...` | Baca isi file web | ✅ |


---

## Cara Menjalankan

### Prasyarat

- Python 3.7+
- pip packages: `flask`, `python-dotenv`, `psutil`

### Instalasi

```bash
# 1. Clone / masuk ke direktori
cd kieroOPS

# 2. Install dependencies
pip install flask python-dotenv psutil

# 3. Konfigurasi .env
# Edit .env sesuai kebutuhan (API key, path, dll)

# 4. Jalankan
python app.py
```

Aplikasi akan berjalan di `http://localhost:5006` (atau port sesuai `APP_PORT`).

### Login Default

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `password_aman_ops` |

> Credentials bisa diubah di halaman **Settings** → Global Config, atau langsung edit `config_app.json`.

---

## Tech Stack

| Layer | Teknologi |
|-------|-----------|
| **Backend** | Python 3 + Flask |
| **Frontend** | HTML5 + CSS3 + Vanilla JavaScript |
| **UI Framework** | Bootstrap 5 + Bootstrap Icons |
| **Styling** | Custom CSS (glassmorphism dark theme) |
| **System Monitor** | psutil |

| **Data Storage** | JSON files (no database) |
| **Process Control** | subprocess + psutil |
