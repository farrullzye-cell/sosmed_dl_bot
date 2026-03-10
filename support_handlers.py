from __future__ import annotations
from typing import Set

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from support_db import SupportDB

CHATTING = 1

async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💬 Admin Live Chat (Downloader)\n"
        "Ketik pesan Anda, admin akan balas via panel.\n"
        "Ketik /done untuk selesai."
    )
    return CHATTING

async def support_on_text(update: Update, context: ContextTypes.DEFAULT_TYPE, sdb: SupportDB, admin_ids: Set[int]):
    u = update.effective_user
    text = (update.message.text or "").strip()
    if not text:
        return CHATTING

    sdb.log_msg(u.id, "in", text, update.message.message_id)

    # notif admin
    for aid in admin_ids:
        try:
            await context.bot.send_message(
                chat_id=aid,
                text=(
                    "💬 SUPPORT DOWNLOADER (NEW)\n"
                    f"User: {u.id} @{u.username or '-'}\n"
                    f"Pesan: {text[:300]}\n"
                    "Balas via panel: /support"
                )
            )
        except Exception:
            pass

    await update.message.reply_text("✅ Terkirim. Ketik lagi atau /done.")
    return CHATTING

async def support_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Support chat selesai. Kembali ke /menu.")
    return ConversationHandler.END

def register_support_handlers(app: Application, sdb: SupportDB, admin_ids: Set[int]):
    conv = ConversationHandler(
        entry_points=[CommandHandler("support", support_start)],
        states={
            CHATTING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: support_on_text(u, c, sdb, admin_ids)),
                CommandHandler("done", support_done),
            ]
        },
        fallbacks=[CommandHandler("done", support_done)],
        name="support_downloader",
        persistent=False,
    )
    app.add_handler(conv)
