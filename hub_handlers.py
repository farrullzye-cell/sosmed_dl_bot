from __future__ import annotations
import os
from typing import Set

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

def _panel_urls():
    base = (os.environ.get("PANEL_URL") or "").strip().rstrip("/")
    if not base:
        return None, None
    return base + "/", base + "/monitor/"

def _kb_home(is_admin: bool) -> InlineKeyboardMarkup:
    panel_url, monitor_url = _panel_urls()

    # Row 4: link panel/monitor kalau ada, kalau tidak jadi tombol info
    if panel_url:
        b_panel = InlineKeyboardButton("🌐 Panel", url=panel_url)
    else:
        b_panel = InlineKeyboardButton("🌐 Panel", callback_data="hub:panel")

    if monitor_url:
        b_mon = InlineKeyboardButton("📊 Monitor", url=monitor_url)
    else:
        b_mon = InlineKeyboardButton("📊 Monitor", callback_data="hub:monitor")

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📥 Downloader", callback_data="hub:downloader"),
            InlineKeyboardButton("🧰 Tools", callback_data="hub:tools"),
            InlineKeyboardButton("👨‍💻 Dev", callback_data="hub:dev"),
        ],
        [
            InlineKeyboardButton("🛒 Shop", callback_data="hub:shop"),
            InlineKeyboardButton("💬 Support", callback_data="hub:support"),
            InlineKeyboardButton("🛟 Shop Support", callback_data="hub:shopsupport"),
        ],
        [
            InlineKeyboardButton("🎫 Claim", callback_data="hub:claim"),
            InlineKeyboardButton("ℹ️ Status", callback_data="hub:status"),
            InlineKeyboardButton("📖 Help", callback_data="hub:help"),
        ],
        [b_panel, b_mon, InlineKeyboardButton("✖️ Tutup", callback_data="hub:close")],
    ])

def _kb_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Kembali", callback_data="hub:home"),
         InlineKeyboardButton("✖️ Tutup", callback_data="hub:close")]
    ])

def _txt_home() -> str:
    return (
        "🧭 HUB MENU\n"
        "━━━━━━━━━━━━━━\n"
        "Pilih fitur di tombol di bawah.\n\n"
        "Tip cepat:\n"
        "• Downloader: kirim URL sosmed\n"
        "• Dev Tools: /dev\n"
        "• Shop: /shop\n"
        "• Support: /support\n"
        "• Shop Support: /shopsupport\n"
        "• Claim: /claim KODE"
    )

def _txt_downloader() -> str:
    return (
        "📥 DOWNLOADER\n"
        "━━━━━━━━━━━━━━\n"
        "Cara pakai:\n"
        "1) Ketik /menu untuk buka menu downloader\n"
        "2) Atau langsung kirim URL sosmed\n\n"
        "Command cepat:\n"
        "• /dl <url>\n"
        "• /audio <url>\n"
    )

def _txt_tools() -> str:
    return (
        "🧰 TOOLS\n"
        "━━━━━━━━━━━━━━\n"
        "Untuk tools umum & developer:\n"
        "• /dev  → JSON/API/Regex/Base64/Hash/SQL dll\n\n"
        "Note: beberapa tools butuh paket tambahan (mis. chromium untuk screenshot HTML)."
    )

def _txt_dev() -> str:
    return (
        "👨‍💻 DEV TOOLS\n"
        "━━━━━━━━━━━━━━\n"
        "Buka dev tools dengan:\n"
        "• /dev\n\n"
        "Tersedia: JSON Formatter, HTML Preview, API Tester, Regex, Base64, Hash, Minify/Beautify, Dummy Data, SQL Tester."
    )

def _txt_support() -> str:
    return (
        "💬 LIVE CHAT SUPPORT (Downloader)\n"
        "━━━━━━━━━━━━━━\n"
        "Mulai chat admin:\n"
        "• /support\n\n"
        "Selesai:\n"
        "• /done"
    )

def _txt_shopsupport() -> str:
    return (
        "🛟 LIVE CHAT SUPPORT (Shop)\n"
        "━━━━━━━━━━━━━━\n"
        "Mulai chat admin untuk urusan shop:\n"
        "• /shopsupport\n\n"
        "Selesai:\n"
        "• /done"
    )

def _txt_claim() -> str:
    return (
        "🎫 CLAIM\n"
        "━━━━━━━━━━━━━━\n"
        "Gunakan setelah admin approve order:\n"
        "• /claim CLM-XXXX-XXXX-XXXX"
    )

def _txt_status() -> str:
    return (
        "ℹ️ STATUS\n"
        "━━━━━━━━━━━━━━\n"
        "Cek status akun/limit:\n"
        "• /status (jika tersedia)\n"
        "• /menu untuk info menu downloader\n"
        "• /hub untuk kembali ke HUB"
    )

def _txt_help() -> str:
    return (
        "📖 HELP\n"
        "━━━━━━━━━━━━━━\n"
        "Menu utama:\n"
        "• /hub\n\n"
        "Downloader:\n"
        "• /menu, /dl, /audio\n\n"
        "Dev Tools:\n"
        "• /dev\n\n"
        "Shop:\n"
        "• /shop, /claim\n\n"
        "Support:\n"
        "• /support, /shopsupport, /done"
    )

async def _render(update: Update, context: ContextTypes.DEFAULT_TYPE, view: str, admin_ids: Set[int]):
    u = update.effective_user
    is_admin = u.id in admin_ids

    if view == "home":
        text = _txt_home()
        kb = _kb_home(is_admin)
    elif view == "downloader":
        text = _txt_downloader()
        kb = _kb_back()
    elif view == "tools":
        text = _txt_tools()
        kb = _kb_back()
    elif view == "dev":
        text = _txt_dev()
        kb = _kb_back()
    elif view == "support":
        text = _txt_support()
        kb = _kb_back()
    elif view == "shopsupport":
        text = _txt_shopsupport()
        kb = _kb_back()
    elif view == "claim":
        text = _txt_claim()
        kb = _kb_back()
    elif view == "status":
        text = _txt_status()
        kb = _kb_back()
    elif view == "help":
        text = _txt_help()
        kb = _kb_back()
    elif view == "panel":
        text = "🌐 PANEL\nSet PANEL_URL di .env agar tombol Panel/Monitor bisa dibuka."
        kb = _kb_back()
    elif view == "monitor":
        text = "📊 MONITOR\nSet PANEL_URL di .env agar tombol Monitor bisa dibuka."
        kb = _kb_back()
    else:
        text = _txt_home()
        kb = _kb_home(is_admin)

    if update.callback_query:
        q = update.callback_query
        await q.answer()
        try:
            await q.edit_message_text(text, reply_markup=kb)
        except Exception:
            await q.message.reply_text(text, reply_markup=kb)
    else:
        await update.effective_message.reply_text(text, reply_markup=kb)

async def cmd_hub(update: Update, context: ContextTypes.DEFAULT_TYPE, admin_ids: Set[int]):
    await _render(update, context, "home", admin_ids)

async def on_hub_button(update: Update, context: ContextTypes.DEFAULT_TYPE, admin_ids: Set[int]):
    q = update.callback_query
    data = (q.data or "").strip()

    if data == "hub:close":
        await q.answer()
        try:
            await q.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        return

    if data == "hub:home":
        return await _render(update, context, "home", admin_ids)

    mapping = {
        "hub:downloader": "downloader",
        "hub:tools": "tools",
        "hub:dev": "dev",
        "hub:support": "support",
        "hub:shopsupport": "shopsupport",
        "hub:claim": "claim",
        "hub:status": "status",
        "hub:help": "help",
        "hub:panel": "panel",
        "hub:monitor": "monitor",
        "hub:shop": "shop",
    }

    if data == "hub:shop":
        # shop submenu langsung pakai tombol shop:* (ditangani shop_handlers)
        await q.answer()
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🕹 Katalog", callback_data="shop:katalog"),
                InlineKeyboardButton("🧾 Order Saya", callback_data="shop:myorders"),
            ],
            [
                InlineKeyboardButton("ℹ️ Cara Bayar", callback_data="shop:payinfo"),
                InlineKeyboardButton("💬 Support", callback_data="shop:support"),
            ],
            [
                InlineKeyboardButton("⬅️ Kembali", callback_data="hub:home"),
                InlineKeyboardButton("✖️ Tutup", callback_data="hub:close"),
            ]
        ])
        try:
            await q.edit_message_text(
                "🛒 SHOP MENU\n━━━━━━━━━━━━━━\nPilih tombol di bawah:",
                reply_markup=kb
            )
        except Exception:
            await q.message.reply_text("🛒 SHOP MENU\nPilih tombol di bawah:", reply_markup=kb)
        return

    view = mapping.get(data)
    if view:
        return await _render(update, context, view, admin_ids)

    await q.answer()
    await q.message.reply_text("Perintah tidak dikenal. Ketik /hub.")

def register_hub_handlers(app: Application, admin_ids: Set[int]):
    app.add_handler(CommandHandler("hub", lambda u, c: cmd_hub(u, c, admin_ids)))
    app.add_handler(CallbackQueryHandler(lambda u, c: on_hub_button(u, c, admin_ids), pattern=r"^hub:"))
