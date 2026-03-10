
# Sosmed Downloader Bot + Web Panel (Termux)

Project ini adalah **Bot Telegram** berbasis **Termux (Android)** dengan **Web Panel Admin** untuk:
- Download media dari beberapa platform sosmed (via `yt-dlp`)
- Utility/Tools + Developer Tools (JSON/API/Regex/Base64/Hash/SQL, dll)
- Shop akun game (katalog → invoice → bukti bayar → approve admin → claim → delivery)
- Live chat support (Downloader & Shop) via web panel
- Monitoring sistem Termux (CPU/RAM/Disk/Net/Uptime/Top process)
- Integrasi domain publik via **Cloudflare Tunnel** (opsional)

> Penting: gunakan sesuai aturan platform & hukum. Jangan upload token/kredensial ke publik.

---

## Daftar Fitur

### 1) Downloader Sosmed
- Auto detect / pilih platform (tombol)
- Download video (atau audio MP3 bila mode audio aktif)
- Limit harian (free/premium) + max size kirim Telegram
- Logging download ke DB

Platform umum (tergantung extractor `yt-dlp` & perubahan situs):
- TikTok, Instagram, Facebook, YouTube, Twitter/X, Pinterest, SoundCloud, Reddit

Catatan:
- Beberapa situs sering berubah, perlu update `yt-dlp`.
- Pinterest kadang berupa image (bukan video) → fallback OG tags.

### 2) Tools (Utility)
- QR generator (PNG)
- Shortlink (TinyURL)
- Weather (Open-Meteo)
- Translate (MyMemory)
- Search engine (SearxNG / Wikipedia fallback)
- Converter → MP3 (ffmpeg)

### 3) Developer Tools (21–30)
Akses via `/dev` lalu pilih tombol:
- JSON Formatter / JSON Minify (basic)
- HTML Preview (screenshot jika `chromium` tersedia; fallback file/card)
- API Tester (GET/POST/PUT/PATCH/DELETE, blok URL private/localhost)
- Regex Tester
- Base64 Encode/Decode
- Hash Generator (md5/sha1/sha256/sha512)
- Code Minifier (basic)
- Code Beautifier (basic)
- Dummy Data Generator (JSON)
- SQL Query Tester (SELECT-only, sandbox in-memory)

### 4) Shop Akun Game
- Listing (game/title/region/rank/harga)
- Stok akun (1 akun per baris)
- Order/invoice otomatis (INV-xxxx)
- User kirim bukti bayar (foto/pdf)
- Admin approve di panel → reserve 1 stok + kirim **kode claim** (CLM-xxxx)
- User `/claim KODE` → bot kirim credential akun
- Log claim/delivery

> Catatan keamanan: penyimpanan “credential akun” adalah data sensitif. Gunakan dengan bijak.

### 5) Live Chat Admin (Support)
- **Downloader Support**: user `/support` → admin balas dari panel `/support`
- **Shop Support**: user `/shopsupport` → admin balas dari panel Shop chat

### 6) Web Panel Admin (HTML)
- Login admin (WEB_USER/WEB_PASS)
- Dashboard & logs (downloads, actions)
- Shop management: listings, upload preview, add stock, orders, approve/reject, claims, deliveries, chat
- Support threads/chat
- System monitor: CPU/RAM/disk/net/top process
- CSS modern + dark mode

### 7) Public Access (Opsional)
- Cloudflare Tunnel 24/7: `panel.domain.com`, `monitor.domain.com`

---

## Struktur File (inti)
Contoh file penting:
- `bot.py` — bot utama
- `web.py` — web panel utama (Flask)
- `db.py` — DB utama (users/premium/log download/admin actions/settings)
- `downloader.py` — downloader via yt-dlp + fallback Pinterest
- `tools.py` — utility tools (QR, shortlink, weather, translate, search, convert)
- `dev_tools.py`, `dev_handlers.py` — developer tools
- `shop_db.py`, `shop_handlers.py`, `shop_panel.py` — shop akun
- `support_db.py`, `support_handlers.py`, `support_panel.py` — live chat support downloader
- `shop_support_handlers.py` — live chat shop
- `hub_handlers.py` — menu HUB (tombol rapi)
- `monitor_utils.py`, `monitor_panel.py` — monitoring panel
- `loading.py` — spinner/loading saat proses
- `static/` + `templates/` — aset panel

---

## Kebutuhan

### Termux packages
```bash
pkg update -y
pkg install -y python git ffmpeg sqlite openssl curl wget
