import os
import tempfile
from functools import wraps
from datetime import datetime, timezone

import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from waitress import serve

from utils import load_env, env_int
from db import DB

from monitor_panel import monitor_bp
from control_panel import control_bp
from support_panel import support_bp
from shop_panel import shop_bp
load_env()

STARTED_AT = datetime.now(timezone.utc)

DB_PATH = os.environ.get("DB_PATH", "bot.db")
WEB_USER = os.environ.get("WEB_USER", "admin")
WEB_PASS = os.environ.get("WEB_PASS", "admin")
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me")
HOST = os.environ.get("WEB_HOST", "127.0.0.1")
PORT = int(os.environ.get("WEB_PORT", "8080"))

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

ENV_DEFAULTS = {
    "FREE_DAILY_LIMIT": env_int("FREE_DAILY_LIMIT", 5),
    "PREMIUM_DAILY_LIMIT": env_int("PREMIUM_DAILY_LIMIT", 50),
    "FREE_MAX_MB": env_int("FREE_MAX_MB", 45),
    "PREMIUM_MAX_MB": env_int("PREMIUM_MAX_MB", 45),
    "enable_tiktok": 1,
    "enable_instagram": 1,
    "enable_facebook": 1,
    "enable_youtube": 1,
    "enable_twitter": 1,
    "enable_pinterest": 1,
    "enable_soundcloud": 1,
    "enable_reddit": 1,
    "enable_audio": 1,
}

db = DB(DB_PATH)
db.seed_settings(ENV_DEFAULTS)

app = Flask(__name__)
app.register_blueprint(monitor_bp)
app.register_blueprint(control_bp)
app.register_blueprint(support_bp)
app.register_blueprint(shop_bp)
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB

def detect_image_type(data: bytes):
    # JPEG: FF D8 FF
    if len(data) >= 3 and data[0:3] == b"\xFF\xD8\xFF":
        return ("jpeg", "image/jpeg", "bot.jpg")
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if len(data) >= 8 and data[0:8] == b"\x89PNG\r\n\x1a\n":
        return ("png", "image/png", "bot.png")
    return (None, None, None)

def fmt_runtime():
    sec = int((datetime.now(timezone.utc) - STARTED_AT).total_seconds())
    d, sec = divmod(sec, 86400)
    h, sec = divmod(sec, 3600)
    m, sec = divmod(sec, 60)
    if d: return f"{d}d {h}h {m}m {sec}s"
    if h: return f"{h}h {m}m {sec}s"
    if m: return f"{m}m {sec}s"
    return f"{sec}s"

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if not session.get("auth"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrap

def tg_api(method: str, *, data=None, files=None, json_body=None):
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN kosong di .env, tidak bisa call Bot API.")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    if json_body is not None:
        r = requests.post(url, json=json_body, timeout=30)
    else:
        r = requests.post(url, data=data or {}, files=files, timeout=60)

    try:
        j = r.json()
    except Exception:
        raise RuntimeError(f"Bot API error (non-json): {r.text[:300]}")
    if not j.get("ok"):
        raise RuntimeError(j)
    return j["result"]

@app.get("/login")
def login():
    return render_template("login.html")

@app.post("/login")
def login_post():
    u = request.form.get("username", "")
    p = request.form.get("password", "")
    if u == WEB_USER and p == WEB_PASS:
        session["auth"] = True
        return redirect(url_for("dashboard"))
    flash("Login gagal")
    return redirect(url_for("login"))

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.get("/")
@login_required
def dashboard():
    s = db.stats()
    return render_template("dashboard.html", stats=s, runtime=fmt_runtime(), now_utc=datetime.now(timezone.utc).isoformat())

@app.get("/users")
@login_required
def users():
    q = request.args.get("q", "").strip() or None
    rows = db.list_users(limit=500, q=q)
    return render_template("users.html", users=rows, q=q or "")

@app.post("/users/<int:user_id>/ban")
@login_required
def user_ban(user_id):
    db.set_ban(user_id, True)
    db.log_admin(0, "web_ban", user_id, "")
    flash(f"User {user_id} diban")
    return redirect(url_for("users"))

@app.post("/users/<int:user_id>/unban")
@login_required
def user_unban(user_id):
    db.set_ban(user_id, False)
    db.log_admin(0, "web_unban", user_id, "")
    flash(f"User {user_id} di-unban")
    return redirect(url_for("users"))

@app.post("/users/<int:user_id>/premium")
@login_required
def user_premium(user_id):
    days = int(request.form.get("days", "0") or 0)
    if days <= 0:
        flash("Days harus > 0")
        return redirect(url_for("users"))
    db.set_premium_days(user_id, days)
    db.log_admin(0, "web_addpremium", user_id, f"days={days}")
    flash(f"Premium {user_id} ditambah {days} hari")
    return redirect(url_for("users"))

@app.post("/users/<int:user_id>/delpremium")
@login_required
def user_delpremium(user_id):
    db.clear_premium(user_id)
    db.log_admin(0, "web_delpremium", user_id, "")
    flash(f"Premium {user_id} dihapus")
    return redirect(url_for("users"))

@app.post("/users/<int:user_id>/limits")
@login_required
def user_limits(user_id):
    daily = request.form.get("daily_limit_override", "").strip()
    maxmb = request.form.get("max_mb_override", "").strip()
    daily_val = int(daily) if daily else None
    maxmb_val = int(maxmb) if maxmb else None
    db.set_limits(user_id, daily_limit_override=daily_val, max_mb_override=maxmb_val)
    db.log_admin(0, "web_limits", user_id, f"daily={daily_val},maxmb={maxmb_val}")
    flash(f"Limit user {user_id} diupdate")
    return redirect(url_for("users"))

@app.post("/users/<int:user_id>/clearlimits")
@login_required
def user_clear_limits(user_id):
    db.clear_limits(user_id)
    db.log_admin(0, "web_clearlimits", user_id, "")
    flash(f"Override limit user {user_id} dihapus")
    return redirect(url_for("users"))

@app.post("/users/<int:user_id>/resetdaily")
@login_required
def user_resetdaily(user_id):
    db.reset_daily_today(user_id)
    db.log_admin(0, "web_resetdaily", user_id, "today")
    flash(f"Pemakaian harian {user_id} direset (hari ini)")
    return redirect(url_for("users"))

@app.post("/users/<int:user_id>/note")
@login_required
def user_note(user_id):
    note = (request.form.get("note", "") or "").strip()
    db.set_note(user_id, note)
    db.log_admin(0, "web_note", user_id, note[:200])
    flash(f"Note user {user_id} diupdate")
    return redirect(url_for("users"))

@app.post("/users/<int:user_id>/delete")
@login_required
def user_delete(user_id):
    db.delete_user(user_id)
    db.log_admin(0, "web_delete_user", user_id, "")
    flash(f"User {user_id} dihapus")
    return redirect(url_for("users"))

@app.get("/downloads")
@login_required
def downloads():
    user_id = request.args.get("user_id", "").strip() or None
    status = request.args.get("status", "").strip() or None
    platform = request.args.get("platform", "").strip() or None
    rows = db.list_downloads(limit=300, user_id=user_id, status=status, platform=platform)
    return render_template("downloads.html", downloads=rows, user_id=user_id or "", status=status or "", platform=platform or "")

@app.get("/actions")
@login_required
def actions():
    rows = db.list_admin_actions(limit=300)
    return render_template("actions.html", actions=rows)

@app.get("/settings")
@login_required
def settings():
    s = db.all_settings()
    bot_info = None
    bot_err = None
    try:
        bot_info = tg_api("getMe")
    except Exception as e:
        bot_err = str(e)
    return render_template("settings.html", s=s, bot_info=bot_info, bot_err=bot_err)

@app.post("/settings/defaults")
@login_required
def settings_defaults():
    keys = ["FREE_DAILY_LIMIT", "PREMIUM_DAILY_LIMIT", "FREE_MAX_MB", "PREMIUM_MAX_MB"]
    for k in keys:
        v = (request.form.get(k, "") or "").strip()
        if not v.isdigit():
            flash(f"{k} harus angka")
            return redirect(url_for("settings"))
        db.set_setting(k, v)

    toggles = ["tiktok","instagram","facebook","youtube","twitter","pinterest","soundcloud","reddit","audio"]
    for t in toggles:
        db.set_setting(f"enable_{t}", 1 if request.form.get(f"enable_{t}") == "on" else 0)

    db.log_admin(0, "web_settings_defaults", None, "updated")
    flash("Settings tersimpan.")
    return redirect(url_for("settings"))

@app.post("/settings/botprofile")
@login_required
def settings_botprofile():
    name = (request.form.get("name","") or "").strip()
    desc = (request.form.get("description","") or "").strip()
    short_desc = (request.form.get("short_description","") or "").strip()

    try:
        if name:
            tg_api("setMyName", data={"name": name})
        if desc:
            tg_api("setMyDescription", data={"description": desc})
        if short_desc:
            tg_api("setMyShortDescription", data={"short_description": short_desc})
        db.log_admin(0, "web_bot_profile", None, "updated")
        flash("Bot profile updated.")
    except Exception as e:
        flash(f"Gagal update bot profile: {e}")
    return redirect(url_for("settings"))

@app.post("/settings/botcommands")
@login_required
def settings_botcommands():
    raw = (request.form.get("commands","") or "").strip()
    commands = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if " - " in line:
            cmd, desc = line.split(" - ", 1)
        elif "-" in line:
            cmd, desc = line.split("-", 1)
        else:
            flash("Format commands salah. Pakai: command - deskripsi")
            return redirect(url_for("settings"))

        cmd = cmd.strip().lstrip("/").replace(" ", "")
        desc = desc.strip()
        if cmd and desc:
            commands.append({"command": cmd, "description": desc})

    try:
        tg_api("setMyCommands", json_body={"commands": commands})
        db.log_admin(0, "web_bot_commands", None, f"{len(commands)} cmds")
        flash("Bot commands updated.")
    except Exception as e:
        flash(f"Gagal set commands: {e}")
    return redirect(url_for("settings"))

@app.post("/settings/photo")
@login_required
def settings_photo():
    f = request.files.get("photo")
    if not f or not f.filename:
        flash("Pilih file foto dulu.")
        return redirect(url_for("settings"))

    try:
        content = f.read()
        if not content:
            flash("File kosong.")
            return redirect(url_for("settings"))

        kind, mime, filename = detect_image_type(content)
        if not kind:
            flash("Format harus JPG/JPEG atau PNG.")
            return redirect(url_for("settings"))

        tg_api("setMyProfilePhoto", files={
            "photo": (filename, content, mime)
        })

        db.log_admin(0, "web_bot_photo", None, f"set:{kind}")
        flash("Foto profil bot berhasil diupdate.")
    except Exception as e:
        flash(f"Gagal upload foto profil bot: {e}")

    return redirect(url_for("settings"))

@app.post("/settings/photo/delete")
@login_required
def settings_photo_delete():
    try:
        tg_api("deleteMyProfilePhoto")
        db.log_admin(0, "web_bot_photo", None, "deleted")
        flash("Foto profil bot dihapus.")
    except Exception as e:
        flash(f"Gagal hapus foto profil bot: {e}")
    return redirect(url_for("settings"))

def main():
    print(f"Web panel: http://{HOST}:{PORT}")
    serve(app, host=HOST, port=PORT)

if __name__ == "__main__":
    main()
