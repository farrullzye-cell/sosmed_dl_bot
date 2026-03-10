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

from shop_db import ShopDB

CHATTING = 1

async def start_shop_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💬 Admin Live Chat (SHOP)\n"
        "Ketik pesan Anda terkait pembelian akun.\n"
        "Sertakan kode invoice INV-... jika ada.\n"
        "Ketik /done untuk selesai."
    )
    return CHATTING

async def on_shop_support_text(update: Update, context: ContextTypes.DEFAULT_TYPE, shop: ShopDB, admin_ids: Set[int]):
    u = update.effective_user
    text = (update.message.text or "").strip()
    if not text:
        return CHATTING

    shop.log_msg(u.id, "in", text, update.message.message_id)

    for aid in admin_ids:
        try:
            await context.bot.send_message(
                chat_id=aid,
                text=(
                    "💬 SUPPORT SHOP (NEW)\n"
                    f"User: {u.id} @{u.username or '-'}\n"
                    f"Pesan: {text[:300]}\n"
                    "Balas via panel: /shop/chat/<user_id>"
                )
            )
        except Exception:
            pass

    await update.message.reply_text("✅ Terkirim. Ketik lagi atau /done.")
    return CHATTING

async def done_shop_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Support shop selesai. Kembali ke /shop.")
    return ConversationHandler.END

def register_shop_support_handlers(app: Application, shop: ShopDB, admin_ids: Set[int]):
    conv = ConversationHandler(
        entry_points=[CommandHandler("shopsupport", start_shop_support)],
        states={
            CHATTING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: on_shop_support_text(u, c, shop, admin_ids)),
                CommandHandler("done", done_shop_support),
            ]
        },
        fallbacks=[CommandHandler("done", done_shop_support)],
        name="support_shop",
        persistent=False,
    )
    app.add_handler(conv)
