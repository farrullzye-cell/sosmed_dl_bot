from __future__ import annotations
import os
from pathlib import Path
import uuid

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import dev_tools as T

import asyncio
from ai_helper import ai_site_recommendations
from html_screenshot import render_html_file_to_png
CHOOSE, INPUT = 1, 2

TOOLS = [
    ("🧩 JSON Formatter", "jsonfmt"),
    ("🧾 HTML Preview", "html"),
    ("🧪 API Tester", "api"),
    ("🧷 Regex Tester", "regex"),
    ("🧬 Base64 Enc/Dec", "b64"),
    ("#️⃣ Hash Generator", "hash"),
    ("🗜 Minifier", "min"),
    ("🧼 Beautifier", "beauty"),
    ("🎲 Dummy Data", "dummy"),
    ("🗃 SQL Tester", "sql"),
]

def kb_dev_menu():
    rows = []
    for i in range(0, len(TOOLS), 2):
        left = TOOLS[i]
        right = TOOLS[i+1] if i+1 < len(TOOLS) else None
        row = [InlineKeyboardButton(left[0], callback_data=f"dev:tool:{left[1]}")]
        if right:
            row.append(InlineKeyboardButton(right[0], callback_data=f"dev:tool:{right[1]}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("✖️ Tutup Dev Tools", callback_data="dev:close")])
    return InlineKeyboardMarkup(rows)

def help_for(tool: str) -> str:
    if tool == "jsonfmt":
        return "Kirim JSON mentah. Bot balas JSON rapi (indent)."
    if tool == "html":
        return "Kirim HTML (atau potongan). Bot akan kirim file preview.html."
    if tool == "api":
        return "Format:\nGET https://example.com\natau\nPOST https://example.com\n{ \"a\": 1 }"
    if tool == "regex":
        return "Format:\npattern || text\natau 2 baris: baris1 pattern, baris2 text."
    if tool == "b64":
        return "Format:\nenc teks\natau\ndec BASE64"
    if tool == "hash":
        return "Format:\nsha256 teks\nAlgo: md5/sha1/sha256/sha512"
    if tool == "min":
        return "Kirim kode/teks. Jika JSON valid → minify JSON, kalau tidak → minify basic."
    if tool == "beauty":
        return "Kirim kode/teks. Jika JSON valid → beautify JSON, kalau tidak → beautify basic."
    if tool == "dummy":
        return "Kirim angka N (1-50). Bot kirim JSON dummy data."
    if tool == "sql":
        return "Kirim query SELECT untuk sandbox table people(id,name,email,age).\nContoh:\nSELECT * FROM people LIMIT 5"
    return "Kirim input."

async def dev_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["dev_tool"] = None
    await update.message.reply_text(
        "👨‍💻 Developer Tools\nPilih tool di bawah:",
        reply_markup=kb_dev_menu()
    )
    return CHOOSE

async def dev_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = (q.data or "")
    if data == "dev:close":
        try:
            await q.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        context.user_data.pop("dev_tool", None)
        return ConversationHandler.END

    tool = data.split(":")[-1]
    context.user_data["dev_tool"] = tool
    await q.message.reply_text(f"✅ Tool aktif: {tool}\n\n{help_for(tool)}\n\nKirim input sekarang. (/dev untuk menu)")
    return INPUT

async def dev_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tool = context.user_data.get("dev_tool")
    text = (update.message.text or "").strip()

    if not tool:
        await update.message.reply_text("Ketik /dev untuk pilih tool.")
        return ConversationHandler.END

    try:
        if tool == "jsonfmt":
            out = T.json_format(text)
            if len(out) > 3500:
                fn = f"downloads/json_{uuid.uuid4().hex}.json"
                os.makedirs("downloads", exist_ok=True)
                Path(fn).write_text(out, encoding="utf-8")
                await update.message.reply_document(document=open(fn, "rb"), caption="✅ JSON formatted")
                try: os.remove(fn)
                except Exception: pass
            else:
                await update.message.reply_text("```json\n" + out + "\n```", parse_mode="Markdown")
            return INPUT

        if tool == "html":
            # AI recommendations (caption max ~1024)
            tips = await asyncio.to_thread(ai_site_recommendations, text)
            tips_caption = tips[:900] + ("..." if len(tips) > 900 else "")

            os.makedirs("downloads", exist_ok=True)
            html_file = f"downloads/preview_{uuid.uuid4().hex}.html"
            png_file = f"downloads/preview_{uuid.uuid4().hex}.png"
            Path(html_file).write_bytes(T.html_preview_file(text))

            try:
                await asyncio.to_thread(render_html_file_to_png, html_file, png_file, 1280, 720)
                with open(png_file, "rb") as f:
                    await update.message.reply_photo(
                        photo=f,
                        caption="🧾 HTML Preview (Screenshot)\n\n" + tips_caption
                    )
            except Exception as e:
                await update.message.reply_text(f"⚠️ Screenshot gagal: {e}\nMengirim file HTML saja.")
                with open(html_file, "rb") as f:
                    await update.message.reply_document(
                        document=f,
                        caption="🧾 HTML Preview (file)\n\n" + tips_caption
                    )

            for fp in (html_file, png_file):
                try: os.remove(fp)
                except Exception: pass

            return INPUT

        if tool == "api":
            out = T.api_test(text)
            await update.message.reply_text(_safe_code(out))
            return INPUT

        if tool == "regex":
            out = T.regex_test(text)
            await update.message.reply_text(_safe_code(out))
            return INPUT

        if tool == "b64":
            if text.lower().startswith("enc "):
                out = T.base64_encode(text[4:])
            elif text.lower().startswith("dec "):
                out = T.base64_decode(text[4:])
            else:
                return await update.message.reply_text("Format: enc teks  /  dec BASE64")
            await update.message.reply_text(_safe_code(out))
            return INPUT

        if tool == "hash":
            out = T.hash_generate(text)
            await update.message.reply_text(_safe_code(out))
            return INPUT

        if tool == "min":
            out = T.code_minify(text)
            await update.message.reply_text(_safe_code(out))
            return INPUT

        if tool == "beauty":
            out = T.code_beautify(text)
            if len(out) > 3500:
                fn = f"downloads/beautify_{uuid.uuid4().hex}.txt"
                os.makedirs("downloads", exist_ok=True)
                Path(fn).write_text(out, encoding="utf-8")
                await update.message.reply_document(document=open(fn, "rb"), caption="🧼 Beautified (file)")
                try: os.remove(fn)
                except Exception: pass
            else:
                await update.message.reply_text(_safe_code(out))
            return INPUT

        if tool == "dummy":
            n = int(text.strip())
            out = T.dummy_data(n)
            await update.message.reply_text("```json\n" + out + "\n```", parse_mode="Markdown")
            return INPUT

        if tool == "sql":
            out = T.sql_test_select(text)
            await update.message.reply_text(_safe_code(out))
            return INPUT

        await update.message.reply_text("Tool tidak dikenal. Ketik /dev.")
        return CHOOSE

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
        return INPUT

def _safe_code(s: str) -> str:
    s = (s or "").replace("```", "'''")
    return "```\n" + s[:3500] + "\n```"

def register_dev_handlers(app: Application):
    conv = ConversationHandler(
        entry_points=[CommandHandler("dev", dev_start)],
        states={
            CHOOSE: [CallbackQueryHandler(dev_choose, pattern=r"^dev:")],
            INPUT: [
                CallbackQueryHandler(dev_choose, pattern=r"^dev:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, dev_input),
            ],
        },
        fallbacks=[CommandHandler("dev", dev_start)],
        name="dev_tools",
        persistent=False,
    )
    app.add_handler(conv)
