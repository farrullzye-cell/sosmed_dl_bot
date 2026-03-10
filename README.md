
# Sosmed Downloader Bot + Web Panel (Termux)

Bot Telegram + Web Panel Admin yang berjalan di Termux (Android).

Fokus utama:
- Downloader sosmed (yt-dlp)
- Tools & Developer Tools
- Shop akun game (invoice → bukti bayar → approve → claim)
- Support live chat (admin balas lewat panel)
- Monitor sistem (CPU/RAM/disk/network)
- (Opsional) Public panel via Cloudflare Tunnel

> Jangan pernah upload `.env`, database `.db`, cookies, atau file credential Cloudflare ke GitHub.

---

## 1) Fitur Utama

### A. Downloader Sosmed
- Kirim URL → bot download & kirim file ke Telegram
- Auto detect / mode platform (tergantung menu bot Anda)
- Audio MP3 (jika tersedia)
- Limit harian & limit ukuran file kirim

Catatan:
- Keberhasilan tiap platform tergantung perubahan situs & versi `yt-dlp`.
- Pinterest kadang berupa gambar (bukan video). Bot bisa fallback.

### B. Tools (Utility)
- QR Generator
- Shortlink
- Weather
- Translate
- Search (fallback)
- Converter ke MP3 (butuh ffmpeg)

### C. Developer Tools (`/dev`)
- JSON formatter/minify
- HTML preview (screenshot jika `chromium` ada; fallback jika tidak)
- API tester
- Regex tester
- Base64 encode/decode
- Hash generator
- Minify/beautify basic
- Dummy data
- SQL tester (SELECT-only, sandbox)

### D. Shop Akun Game
- Admin buat listing + stok akun
- User beli → dapat invoice (INV-...)
- User kirim bukti bayar (foto/pdf)
- Admin approve di panel → bot kirim kode claim (CLM-...)
- User `/claim KODE` → bot kirim credential akun
- Log claim/delivery tersimpan

### E. Live Chat Support
- Downloader Support: user `/support` → admin balas di panel `/support`
- Shop Support: user `/shopsupport` → admin balas di panel Shop chat

### F. Monitor Panel
- CPU%, RAM, disk usage, network rate, uptime, top process
- URL: `/monitor/`

---

## 2) Instalasi di Termux

### 2.1 Update & install paket Termux
```bash
pkg update -y && pkg upgrade -y
pkg install -y python git ffmpeg sqlite curl
Opsional:

Bash

pkg install -y tmux
pkg install -y chromium      # untuk screenshot HTML preview (real)
pkg install -y imagemagick   # fallback preview card image
pkg install -y cloudflared termux-services  # untuk public panel 24/7
2.2 Install Python requirements
Di folder project:

Bash

cd ~/sosmed_dl_bot
pip install -r requirements.txt
3) Konfigurasi .env
Buat/edit file .env:

env

# Telegram
BOT_TOKEN=ISI_TOKEN_BOT
ADMIN_IDS=123456789

# Web Panel Login
WEB_USER=admin
WEB_PASS=password_yang_kuat
SECRET_KEY=random_string_panjang

# Paths
DB_PATH=bot.db
DOWNLOAD_DIR=downloads
SHOP_STORAGE_DIR=shop_storage

# Limit
FREE_DAILY_LIMIT=5
PREMIUM_DAILY_LIMIT=50
FREE_MAX_MB=45
PREMIUM_MAX_MB=400

# (Opsional) Cookies untuk IG/FB/Pinterest/YT jika butuh login
# COOKIE_FILE=cookies.txt

# (Opsional) Link panel untuk tombol /hub
# PANEL_URL=https://panel.domainkamu.com

# (Opsional) OpenAI untuk rekomendasi HTML preview
# OPENAI_API_KEY=...
# OPENAI_MODEL=gpt-4.1-mini
Token bot wajib dirahasiakan. Jika token sudah pernah dibagikan, revoke di @BotFather.

4) Menjalankan Bot & Web Panel
4.1 Jalankan Bot
Bash

cd ~/sosmed_dl_bot
python -u bot.py
4.2 Jalankan Web Panel
Buka Termux tab lain:

Bash

cd ~/sosmed_dl_bot
python -u web.py
Buka browser HP:

http://127.0.0.1:8080/login
5) Cara Pakai (User) – Telegram
5.1 Menu utama
/hub → menu tombol (paling rapi)
/menu → menu downloader (jika ada)
/dev → dev tools
/shop → menu shop akun
/support → live chat support downloader
/shopsupport → live chat support shop
/claim KODE → ambil akun setelah approve
5.2 Downloader
Pilih platform/Auto (tombol) atau langsung kirim URL
Tunggu bot kirim file
Jika gagal:

update yt-dlp:
Bash

python -m pip install -U yt-dlp
5.3 Developer Tools
ketik /dev
pilih tool via tombol
kirim input sesuai petunjuk
5.4 Shop Akun (Flow)
/shop → Katalog → Buy
bot kirim invoice INV-...
user bayar, kirim bukti (foto/pdf) dengan caption INV-...
admin approve di panel
user dapat kode CLM-...
user: /claim CLM-... → bot kirim credential akun
6) Cara Pakai (Admin) – Web Panel
6.1 Login
http://127.0.0.1:8080/login
pakai WEB_USER & WEB_PASS dari .env
6.2 Shop Admin
/shop/ → dashboard shop
/shop/listings → buat listing
Edit listing → upload preview + add stock bulk
/shop/orders → approve/reject order
/shop/claims → revoke/unrevoke claim
/shop/deliveries → log delivery
/shop/chat/<user_id> → balas user
6.3 Support Admin (Downloader)
/support/ → daftar user yang chat via /support
/support/chat/<user_id> → balas user
6.4 Monitor
/monitor/ → CPU/RAM/Disk/Net/Top process
7) Public Panel 24/7 (Opsional) – Cloudflare Tunnel
7.1 Syarat
Domain DNS sudah pindah ke Cloudflare (nameserver Cloudflare aktif)
7.2 Setup tunnel (ringkas)
Bash

pkg install -y cloudflared
cloudflared tunnel login
cloudflared tunnel create termuxpanel
cloudflared tunnel route dns termuxpanel panel.domainkamu.com
cloudflared tunnel route dns termuxpanel monitor.domainkamu.com
Buat config:

Bash

cred="$(ls -t ~/.cloudflared/*.json | head -n 1)"
cat > ~/.cloudflared/config.yml <<EOF
tunnel: termuxpanel
credentials-file: $cred
ingress:
  - hostname: panel.domainkamu.com
    service: http://127.0.0.1:8080
  - hostname: monitor.domainkamu.com
    service: http://127.0.0.1:8080
  - service: http_status:404
EOF
Run:

Bash

cloudflared tunnel run termuxpanel
Disarankan tambah proteksi Cloudflare Access agar panel tidak bisa dibuka sembarang orang.

8) Troubleshooting
8.1 Bot conflict getUpdates (bot jalan dobel)
Error: Conflict: terminated by other getUpdates request
Solusi:

Bash

pkill -f "python.*bot.py"
python -u bot.py
8.2 Pinterest error (403 / no formats)
Update yt-dlp:
Bash

python -m pip install -U yt-dlp
Jika perlu cookies: set COOKIE_FILE=cookies.txt
8.3 HTML preview screenshot
Install chromium agar screenshot real.
Jika belum, bot fallback (file/card).
9) Keamanan
Wajib .gitignore berisi:

.env
*.db
cookies.txt
folder downloads/, logs/, shop_storage/
~/.cloudflared/ atau file credential tunnel
10) Lisensi & Tanggung Jawab
Gunakan untuk kebutuhan sendiri dan sesuai aturan platform/hukum. Anda bertanggung jawab atas konten yang diunduh dan penggunaan fitur shop.
