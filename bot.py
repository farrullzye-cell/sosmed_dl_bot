import os
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
import uuid

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from utils import load_env, env_int, env_list_int
from db import DB
from downloader import download_media, detect_platform, extract_url as extract_url_dl
from tools import (
    extract_url as extract_url_tools,
    make_qr_png,
    short_tinyurl,
    weather_city,
    translate_mymemory,
    web_search,
    convert_to_mp3,
)


from shop_db import ShopDB
from shop_handlers import register_shop_handlers
from support_db import SupportDB
from support_handlers import register_support_handlers
from shop_support_handlers import register_shop_support_handlers
from loading import Spinner

from dev_handlers import register_dev_handlers

from hub_handlers import register_hub_handlers

from hub_handlers import cmd_hub as hub_cmd_hub

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("sosmed_dl_bot")

STARTED_AT = datetime.now(timezone.utc)

load_env()
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN or BOT_TOKEN.startswith("TEMP") or BOT_TOKEN.startswith("ISI_"):
    raise SystemExit("BOT_TOKEN belum diisi benar di .env.")

ADMIN_IDS = set(env_list_int("ADMIN_IDS"))
DB_PATH = os.environ.get("DB_PATH", "bot.db")
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "downloads")

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
    "menu_banner_file": "menu_banner.jpg",  # optional, taruh di static/
}

db = DB(DB_PATH)
shop = ShopDB(DB_PATH)
support = SupportDB(DB_PATH)

db.seed_settings(ENV_DEFAULTS)

PLATFORM_LABEL = {
    "tiktok": "TikTok",
    "instagram": "Instagram",
    "facebook": "Facebook",
    "youtube": "YouTube",
    "twitter": "Twitter/X",
    "pinterest": "Pinterest",
    "soundcloud": "SoundCloud",
    "reddit": "Reddit",
    "auto": "Auto",
}
PLATFORM_ICON = {
    "tiktok": "🎵",
    "instagram": "📸",
    "facebook": "👥",
    "youtube": "▶️",
    "twitter": "💬",
    "pinterest": "📌",
    "soundcloud": "🎧",
    "reddit": "🧵",
    "auto": "🤖",
}

def fmt_runtime():
    sec = int((datetime.now(timezone.utc) - STARTED_AT).total_seconds())
    d, sec = divmod(sec, 86400)
    h, sec = divmod(sec, 3600)
    m, sec = divmod(sec, 60)
    if d: return f"{d}d {h}h {m}m {sec}s"
    if h: return f"{h}h {m}m {sec}s"
    if m: return f"{m}m {sec}s"
    return f"{sec}s"

def s_int(key: str, fallback: int) -> int:
    v = db.get_setting(key, None)
    try:
        return int(v) if v is not None and str(v).strip() != "" else int(fallback)
    except Exception:
        return int(fallback)

def s_bool(key: str, fallback: int = 1) -> bool:
    return s_int(key, fallback) == 1

def feature_enabled(platform: str) -> bool:
    if platform == "unknown":
        return True
    return s_bool(f"enable_{platform}", 1)

def effective_daily_limit(user_id: int) -> int:
    u = db.get_user(user_id)
    if u and u["daily_limit_override"] is not None:
        return int(u["daily_limit_override"])
    return s_int("PREMIUM_DAILY_LIMIT", ENV_DEFAULTS["PREMIUM_DAILY_LIMIT"]) if db.is_premium(user_id) else s_int("FREE_DAILY_LIMIT", ENV_DEFAULTS["FREE_DAILY_LIMIT"])

def effective_max_mb(user_id: int) -> int:
    u = db.get_user(user_id)
    if u and u["max_mb_override"] is not None:
        return int(u["max_mb_override"])
    return s_int("PREMIUM_MAX_MB", ENV_DEFAULTS["PREMIUM_MAX_MB"]) if db.is_premium(user_id) else s_int("FREE_MAX_MB", ENV_DEFAULTS["FREE_MAX_MB"])

def get_banner_path():
    fname = (db.get_setting("menu_banner_file", "") or "").strip()
    if not fname:
        return None
    p = Path("static") / fname
    return p if p.exists() else None

def kb_main(mode: str, audio_only: bool) -> InlineKeyboardMarkup:
    audio_label = "🎧 Audio: ON" if audio_only else "🎧 Audio: OFF"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵 TikTok", callback_data="dlmode:tiktok"),
            InlineKeyboardButton("📸 IG", callback_data="dlmode:instagram"),
            InlineKeyboardButton("👥 FB", callback_data="dlmode:facebook"),
            InlineKeyboardButton("▶️ YT", callback_data="dlmode:youtube"),
        ],
        [
            InlineKeyboardButton("💬 X", callback_data="dlmode:twitter"),
            InlineKeyboardButton("📌 Pin", callback_data="dlmode:pinterest"),
            InlineKeyboardButton("🎧 SC", callback_data="dlmode:soundcloud"),
            InlineKeyboardButton("🧵 Reddit", callback_data="dlmode:reddit"),
        ],
        [
            InlineKeyboardButton("🤖 Auto", callback_data="dlmode:auto"),
            InlineKeyboardButton(audio_label, callback_data="dlaudio:toggle"),
        ],
        [
            InlineKeyboardButton("🧰 Tools", callback_data="view:tools"),
            InlineKeyboardButton("ℹ️ Status", callback_data="view:status"),
            InlineKeyboardButton("✖️ Tutup", callback_data="view:close"),
        ],
    ])

def kb_tools(tool: str | None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🧾 QR", callback_data="tool:qr"),
            InlineKeyboardButton("🔗 Shortlink", callback_data="tool:short"),
            InlineKeyboardButton("🌦 Weather", callback_data="tool:weather"),
        ],
        [
            InlineKeyboardButton("🌐 Translate", callback_data="tool:tr"),
            InlineKeyboardButton("🔎 Search", callback_data="tool:search"),
            InlineKeyboardButton("🎛 Converter→MP3", callback_data="tool:convmp3"),
        ],
        [
            InlineKeyboardButton("⬅️ Downloader", callback_data="view:downloader"),
            InlineKeyboardButton("ℹ️ Status", callback_data="view:status"),
            InlineKeyboardButton("✖️ Tutup", callback_data="view:close"),
        ],
    ])

def caption_downloader(u, mode: str, audio_only: bool) -> str:
    row = db.get_user(u.id)
    prem = db.is_premium(u.id)
    banned = db.is_banned(u.id)
    used = db.get_daily(u.id)
    limit = effective_daily_limit(u.id)
    maxmb = effective_max_mb(u.id)
    username = f"@{u.username}" if u.username else "-"
    icon = PLATFORM_ICON.get(mode, "📥")
    mode_label = f"{icon} {PLATFORM_LABEL.get(mode, mode)}"

    return (
        "📥 DOWNLOADER SOSMED\n"
        "━━━━━━━━━━━━━━\n"
        f"👤 {u.first_name or '-'} | {username}\n"
        f"🆔 {u.id} | 🛡 {'BANNED' if banned else 'AKTIF'}\n"
        f"⭐ {'PREMIUM' if prem else 'FREE'} | ⏳ {row['premium_until'] if (row and row['premium_until']) else '-'}\n"
        f"📊 Quota: {used}/{limit} | 📦 Max: {maxmb}MB\n"
        f"⚙️ Mode: {mode_label} | 🎧 {'ON' if audio_only else 'OFF'}\n"
        f"⏱ Runtime: {fmt_runtime()}\n"
        "━━━━━━━━━━━━━━\n"
        "✅ Cara pakai:\n"
        "1) Pilih platform/Auto\n"
        "2) Kirim URL\n"
        "3) Tunggu hasil\n"
    )

def caption_tools(u, tool: str | None) -> str:
    username = f"@{u.username}" if u.username else "-"
    tool_name = tool or "-"
    return (
        "🧰 UTILITY / TOOLS\n"
        "━━━━━━━━━━━━━━\n"
        f"👤 {u.first_name or '-'} | {username}\n"
        f"🆔 {u.id}\n"
        f"⚙️ Tool aktif: {tool_name}\n"
        "━━━━━━━━━━━━━━\n"
        "Pilih tool, lalu kirim input:\n"
        "• 🧾 QR: kirim teks/link\n"
        "• 🔗 Shortlink: kirim URL\n"
        "• 🌦 Weather: kirim nama kota\n"
        "• 🌐 Translate: format: to|teks  (contoh: en|halo)\n"
        "• 🔎 Search: kirim kata kunci\n"
        "• 🎛 Converter→MP3: kirim file video/audio\n"
    )

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    db.upsert_user(u.id, u.username or "", u.first_name or "")

    context.user_data.setdefault("view", "downloader")  # downloader/tools
    context.user_data.setdefault("dl_mode", "auto")
    context.user_data.setdefault("dl_audio", False)
    context.user_data.setdefault("tool_mode", None)

    view = context.user_data["view"]
    dl_mode = context.user_data["dl_mode"]
    dl_audio = bool(context.user_data["dl_audio"])
    tool_mode = context.user_data["tool_mode"]

    if view == "tools":
        cap = caption_tools(u, tool_mode)
        kb = kb_tools(tool_mode)
    else:
        cap = caption_downloader(u, dl_mode, dl_audio)
        kb = kb_main(dl_mode, dl_audio)

    # edit pesan yg sama (anti dobel)
    if update.callback_query:
        q = update.callback_query
        msg = q.message
        try:
            if msg and msg.photo:
                await q.edit_message_caption(caption=cap, reply_markup=kb)
            else:
                await q.edit_message_text(text=cap, reply_markup=kb)
        except Exception:
            pass
        return

    # dari command: edit menu terakhir bila ada
    chat_id = context.user_data.get("menu_chat_id")
    msg_id = context.user_data.get("menu_message_id")
    is_photo = bool(context.user_data.get("menu_is_photo", False))
    if chat_id and msg_id:
        try:
            if is_photo:
                await context.bot.edit_message_caption(chat_id=chat_id, message_id=msg_id, caption=cap, reply_markup=kb)
            else:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=cap, reply_markup=kb)
            return
        except Exception:
            pass

    banner = get_banner_path()
    if banner:
        with open(banner, "rb") as f:
            m = await update.message.reply_photo(photo=f, caption=cap, reply_markup=kb)
        context.user_data["menu_is_photo"] = True
    else:
        m = await update.message.reply_text(cap, reply_markup=kb)
        context.user_data["menu_is_photo"] = False

    context.user_data["menu_chat_id"] = m.chat_id
    context.user_data["menu_message_id"] = m.message_id

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Ready.", reply_markup=ReplyKeyboardRemove())
    context.user_data["view"] = "downloader"
    await show_menu(update, context)

async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_menu(update, context)

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = (q.data or "").strip()

    if data == "view:close":
        try:
            await q.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        return

    if data == "view:tools":
        context.user_data["view"] = "tools"
        await show_menu(update, context)
        return

    if data == "view:downloader":
        context.user_data["view"] = "downloader"
        context.user_data["tool_mode"] = None
        await show_menu(update, context)
        return

    if data == "view:status":
        # status = re-render menu
        await show_menu(update, context)
        return

    if data.startswith("dlmode:"):
        context.user_data["view"] = "downloader"
        context.user_data["dl_mode"] = data.split(":", 1)[1]
        await show_menu(update, context)
        return

    if data == "dlaudio:toggle":
        context.user_data["view"] = "downloader"
        context.user_data["dl_audio"] = not bool(context.user_data.get("dl_audio", False))
        await show_menu(update, context)
        return

    if data.startswith("tool:"):
        context.user_data["view"] = "tools"
        context.user_data["tool_mode"] = data.split(":", 1)[1]  # qr/short/weather/tr/search/convmp3
        await show_menu(update, context)
        return

async def handle_downloader(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    u = update.effective_user
    db.upsert_user(u.id, u.username or "", u.first_name or "")

    if db.is_banned(u.id):
        return await update.message.reply_text("🛑 Anda dibanned.")
    if not url or not url.startswith("http"):
        return await update.message.reply_text("❌ URL tidak valid.")

    used = db.get_daily(u.id)
    limit = effective_daily_limit(u.id)
    if used >= limit:
        return await update.message.reply_text(f"⚠️ Limit harian habis ({used}/{limit}).")

    mode = context.user_data.get("dl_mode", "auto")
    audio_only = bool(context.user_data.get("dl_audio", False))

    if audio_only and not s_bool("enable_audio", 1):
        return await update.message.reply_text("⚠️ Fitur audio sedang OFF.")

    platform_hint = None if mode == "auto" else mode
    platform = platform_hint or detect_platform(url)
    if platform != "unknown" and not feature_enabled(platform):
        return await update.message.reply_text(f"⚠️ Fitur {platform} sedang OFF.")

    await update.message.chat.send_action(ChatAction.TYPING)
    await update.message.reply_text(f"⏳ Memproses {PLATFORM_ICON.get(platform,'📥')} {platform} | {'audio' if audio_only else 'video'}")

    try:
        await update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
        spin = await Spinner.start(update, context, 'Sedang download / proses', interval=1.4)
        info = await asyncio.to_thread(download_media, url, DOWNLOAD_DIR, audio_only)
        await spin.stop('✅ Download selesai, mengirim...')
        await spin.stop('✅ Download selesai, mengirim...')
        await spin.stop('✅ Download selesai, mengirim...')

        size_mb = info["file_size"] / (1024 * 1024)
        maxmb = effective_max_mb(u.id)
        if size_mb > maxmb:
            db.log_download(u.id, url, platform, "rejected", error=f"File terlalu besar {size_mb:.1f}MB > {maxmb}MB")
            try: os.remove(info["file_path"])
            except Exception: pass
            return await update.message.reply_text(f"📦 File terlalu besar ({size_mb:.1f} MB). Max Anda: {maxmb} MB.")

        db.inc_daily(u.id)

        cap = f"✅ {info['title']}\n{PLATFORM_ICON.get(platform,'📥')} {platform}\n📦 {size_mb:.1f} MB"
        fp = info["file_path"]
        if audio_only or fp.lower().endswith(".mp3"):
            with open(fp, "rb") as f:
                await update.message.reply_audio(audio=f, caption=cap)
        else:
            with open(fp, "rb") as f:
                await update.message.reply_document(document=f, caption=cap)

        db.log_download(u.id, url, platform, "sent", title=info["title"], file_path=fp, file_size=info["file_size"])
        try: os.remove(fp)
        except Exception: pass

    except Exception as e:
        try:
            await spin.stop('❌ Gagal.')
        except Exception:
            pass
        try:
            await spin.stop('❌ Gagal.')
        except Exception:
            pass
        try:
            await spin.stop('❌ Gagal.')
        except Exception:
            pass
        logger.exception("Download error")
        db.log_download(u.id, url, platform, "error", error=str(e))
        await update.message.reply_text(f"❌ Gagal: {e}")

async def handle_tools_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    tool = context.user_data.get("tool_mode")
    text = (text or "").strip()

    if tool == "qr":
        out = f"downloads/qr_{uuid.uuid4().hex}.png"
        await asyncio.to_thread(make_qr_png, text, out)
        with open(out, "rb") as f:
            await update.message.reply_photo(photo=f, caption="🧾 QR berhasil dibuat")
        try: os.remove(out)
        except Exception: pass
        return

    if tool == "short":
        url = extract_url_tools(text) or text
        short = await asyncio.to_thread(short_tinyurl, url)
        return await update.message.reply_text(f"🔗 Shortlink:\n{short}")

    if tool == "weather":
        info = await asyncio.to_thread(weather_city, text, "id")
        return await update.message.reply_text("🌦 " + info)

    if tool == "tr":
        # format: to|text  (contoh: en|halo)
        if "|" in text:
            to, msg = text.split("|", 1)
            to = to.strip() or "id"
            msg = msg.strip()
        else:
            # default translate ke id
            to, msg = "id", text
        out = await asyncio.to_thread(translate_mymemory, msg, to, "auto")
        return await update.message.reply_text(f"🌐 Translate ({to}):\n{out}")

    if tool == "search":
        await update.message.reply_text("🔎 Searching...")
        results = await asyncio.to_thread(web_search, text, 5)
        if not results:
            return await update.message.reply_text("Tidak ada hasil.")
        lines = ["🔎 Hasil:"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r['title']}\n{r['href']}")
        return await update.message.reply_text("\n\n".join(lines))

    return await update.message.reply_text("Pilih tool dulu dari menu 🧰 Tools.")

async def handle_converter_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # converter mode: convmp3
    tool = context.user_data.get("tool_mode")
    if tool != "convmp3":
        return

    msg = update.message
    if not msg:
        return

    tg_file = None
    file_name = None
    size = None

    if msg.audio:
        tg_file = msg.audio
        file_name = msg.audio.file_name or "audio"
        size = msg.audio.file_size
    elif msg.video:
        tg_file = msg.video
        file_name = "video.mp4"
        size = msg.video.file_size
    elif msg.voice:
        tg_file = msg.voice
        file_name = "voice.ogg"
        size = msg.voice.file_size
    elif msg.document:
        tg_file = msg.document
        file_name = msg.document.file_name or "file"
        size = msg.document.file_size
    else:
        return await msg.reply_text("Kirim file audio/video/document untuk di-convert.")

    u = update.effective_user
    maxmb = effective_max_mb(u.id)
    if size and (size / (1024 * 1024)) > maxmb:
        return await msg.reply_text(f"File terlalu besar untuk diproses. Max Anda: {maxmb} MB")

    await msg.reply_text("🎛 Download file... lalu convert ke MP3")
    await msg.chat.send_action(ChatAction.TYPING)

    os.makedirs("downloads", exist_ok=True)
    in_path = f"downloads/in_{uuid.uuid4().hex}_{file_name}"
    out_path = f"downloads/out_{uuid.uuid4().hex}.mp3"

    try:
        file = await context.bot.get_file(tg_file.file_id)
        await file.download_to_drive(in_path)

        await msg.chat.send_action(ChatAction.TYPING)
        spin = await Spinner.start(update, context, 'Sedang convert ke MP3', interval=1.4)
        await asyncio.to_thread(convert_to_mp3, in_path, out_path)
        await spin.stop('✅ Convert selesai, mengirim...')
        await spin.stop('✅ Convert selesai, mengirim...')
        await spin.stop('✅ Convert selesai, mengirim...')

        with open(out_path, "rb") as f:
            await msg.reply_audio(audio=f, caption="✅ Convert MP3 selesai")

    except Exception as e:
        try:
            await spin.stop('❌ Gagal.')
        except Exception:
            pass
        try:
            await spin.stop('❌ Gagal.')
        except Exception:
            pass
        try:
            await spin.stop('❌ Gagal.')
        except Exception:
            pass
        logger.exception("Converter error")
        await msg.reply_text(f"❌ Convert gagal: {e}")
    finally:
        for p in (in_path, out_path):
            try: os.remove(p)
            except Exception: pass

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    txt = update.message.text.strip()

    # Jika sedang di Tools view & tool aktif => proses tools
    if context.user_data.get("view") == "tools" and context.user_data.get("tool_mode"):
        return await handle_tools_text(update, context, txt)

    # Default: coba downloader jika ada URL
    url = extract_url_dl(txt)
    if url:
        return await handle_downloader(update, context, url)

    return await update.message.reply_text("Ketik /menu untuk buka menu. Atau kirim URL untuk download.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    register_hub_handlers(app, ADMIN_IDS)

    register_dev_handlers(app)

    register_support_handlers(app, support, ADMIN_IDS)

    register_shop_handlers(app, shop, ADMIN_IDS)
    register_shop_support_handlers(app, shop, ADMIN_IDS)
    app.add_handler(CommandHandler("start", lambda u,c: hub_cmd_hub(u,c,ADMIN_IDS)))

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))

    app.add_handler(CallbackQueryHandler(on_button))

    # converter media handler
    app.add_handler(MessageHandler(
        filters.VIDEO | filters.AUDIO | filters.Document.ALL | filters.VOICE,
        handle_converter_media
    ))

    # text handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
