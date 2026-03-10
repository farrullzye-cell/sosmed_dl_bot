from __future__ import annotations
import re
from pathlib import Path
from typing import Set

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from shop_db import ShopDB

INV_RE = re.compile(r"(INV-\d{8}-[A-Z0-9]{6})")

def money_idr(x: int) -> str:
    try:
        x = int(x)
    except Exception:
        x = 0
    return f"Rp{x:,}".replace(",", ".")

def kb_shop_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🕹 Katalog Akun", callback_data="shop:katalog")],
        [InlineKeyboardButton("🧾 Order Saya", callback_data="shop:myorders")],
        [InlineKeyboardButton("ℹ️ Cara Bayar", callback_data="shop:payinfo"),
         InlineKeyboardButton("🎫 Cara Claim", callback_data="shop:claimhelp")],
        [InlineKeyboardButton("💬 Support", callback_data="shop:support")],
    ])

def kb_back_shop() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data="shop:menu")]])

def shop_menu_text() -> str:
    return (
        "🛒 SHOP AKUN GAME\n"
        "━━━━━━━━━━━━━━\n"
        "Flow pembelian:\n"
        "1) Katalog → Buy\n"
        "2) Bayar → kirim bukti (foto/pdf)\n"
        "3) Admin approve\n"
        "4) Anda dapat kode claim\n"
        "5) /claim KODE untuk menerima akun\n\n"
        "Catatan: segera ganti password setelah login."
    )

async def cmd_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(shop_menu_text(), reply_markup=kb_shop_menu())

async def cmd_claim(update: Update, context: ContextTypes.DEFAULT_TYPE, shop: ShopDB):
    u = update.effective_user
    if not context.args:
        return await update.message.reply_text("Usage: /claim CLM-XXXX-XXXX-XXXX")
    code = context.args[0].strip().upper()

    c = shop.get_claim(code)
    if not c:
        return await update.message.reply_text("Kode claim tidak ditemukan.")
    if int(c["user_id"]) != u.id:
        return await update.message.reply_text("Kode ini bukan untuk akun Anda.")
    if c["status"] == "REVOKED":
        return await update.message.reply_text("Kode claim sudah direvoke.")
    if c["status"] == "USED":
        return await update.message.reply_text("Kode claim sudah digunakan.")
    if c["order_status"] not in ("PAID", "DELIVERED"):
        return await update.message.reply_text("Order belum PAID. Tunggu admin approve.")

    stock_id = c["stock_id"]
    if not stock_id:
        return await update.message.reply_text("Stock belum dialokasikan. Hubungi admin.")

    s = shop.get_stock(int(stock_id))
    if not s:
        return await update.message.reply_text("Stock tidak ditemukan. Hubungi admin.")

    try:
        text = (
            "✅ DELIVERY AKUN\n"
            f"Order: {c['order_code']}\n"
            f"Listing: {c['listing_game']} - {c['listing_title']}\n"
            f"Claim: {code}\n\n"
            "🔐 Detail akun:\n"
            f"{s['creds_text']}\n\n"
            "⚠️ Segera ganti password/email recovery setelah login."
        )
        await update.message.reply_text(text)

        shop.mark_claim_used(code)
        shop.mark_stock_sold(int(stock_id), int(c["order_id"]))
        shop.mark_delivered(int(c["order_id"]))
        shop.log_delivery(int(c["order_id"]), u.id, int(c["listing_id"]), code, int(stock_id), "sent", None)

    except Exception as e:
        shop.log_delivery(int(c["order_id"]), u.id, int(c["listing_id"]), code, int(stock_id), "error", str(e))
        await update.message.reply_text(f"Gagal delivery: {e}")

async def on_shop_button(update: Update, context: ContextTypes.DEFAULT_TYPE, shop: ShopDB):
    q = update.callback_query
    data = (q.data or "").strip()
    await q.answer()

    if data == "shop:menu":
        return await q.edit_message_text(shop_menu_text(), reply_markup=kb_shop_menu())

    if data == "shop:payinfo":
        pay = shop.get_setting("payment_instructions", "")
        return await q.message.reply_text("ℹ️ CARA BAYAR\n\n" + pay, reply_markup=kb_back_shop())

    if data == "shop:claimhelp":
        return await q.message.reply_text(
            "🎫 CARA CLAIM\n"
            "Setelah admin approve, Anda akan mendapat kode claim.\n"
            "Gunakan:\n"
            "/claim CLM-XXXX-XXXX-XXXX",
            reply_markup=kb_back_shop()
        )

    if data == "shop:support":
        # tidak mengambil alih semua chat user (biar tidak bentrok dengan downloader),
        # jadi ini hanya info + user bisa tulis pesan manual. Log user chat bisa ditambah belakangan.
        return await q.message.reply_text(
            "💬 SUPPORT\n"
            "Silakan tulis pesan Anda di chat ini.\n"
            "Sertakan kode invoice INV-... bila terkait pembayaran.\n"
            "Admin akan balas via panel web.",
            reply_markup=kb_back_shop()
        )

    if data == "shop:myorders":
        u = update.effective_user
        rows = shop.list_orders(status=None, limit=100)
        mine = [r for r in rows if int(r["user_id"]) == u.id][:10]
        if not mine:
            return await q.message.reply_text("Belum ada order.", reply_markup=kb_back_shop())
        lines = ["🧾 ORDER SAYA (10 terakhir):"]
        for r in mine:
            lines.append("• %s | %s - %s | %s" % (r["order_code"], r["listing_game"], r["listing_title"], r["status"]))
        return await q.message.reply_text("\n".join(lines), reply_markup=kb_back_shop())

    if data == "shop:katalog":
        rows = shop.list_listings(active_only=True)
        if not rows:
            return await q.message.reply_text("Katalog akun kosong.", reply_markup=kb_back_shop())

        lines = ["🕹 KATALOG AKUN:"]
        kb = []
        for l in rows[:15]:
            a, r, s = shop.stock_counts(l["id"])
            lines.append(
                f"\n• [{l['id']}] {l['game']} - {l['title']}\n"
                f"  Region: {l['region'] or '-'} | Rank: {l['rank'] or '-'}\n"
                f"  Harga: {money_idr(l['price_int'])} | Stok: {a}"
            )
            kb.append([
                InlineKeyboardButton(f"👁 Preview {l['id']}", callback_data=f"shop:preview:{l['id']}"),
                InlineKeyboardButton(f"🛒 Buy {l['id']}", callback_data=f"shop:buy:{l['id']}"),
            ])
        kb.append([InlineKeyboardButton("⬅️ Menu Shop", callback_data="shop:menu")])
        return await q.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))

    if data.startswith("shop:preview:"):
        lid = int(data.split(":")[-1])
        l = shop.get_listing(lid)
        if not l:
            return await q.message.reply_text("Listing tidak ditemukan.", reply_markup=kb_back_shop())

        a, r, s = shop.stock_counts(lid)
        desc = (l["description"] or "").strip()
        cap = (
            f"👁 PREVIEW\n{l['game']} - {l['title']}\n"
            f"Region: {l['region'] or '-'} | Rank: {l['rank'] or '-'}\n"
            f"Harga: {money_idr(l['price_int'])}\n"
            f"Stok tersedia: {a}\n\n"
            f"{desc[:900]}"
        )
        if l["preview_type"] == "image" and l["preview_path"] and Path(l["preview_path"]).exists():
            with open(l["preview_path"], "rb") as f:
                await q.message.reply_photo(photo=f, caption=cap)
        else:
            await q.message.reply_text(cap)
        return

    if data.startswith("shop:buy:"):
        u = update.effective_user
        lid = int(data.split(":")[-1])
        l = shop.get_listing(lid)
        if not l or l["is_active"] != 1:
            return await q.message.reply_text("Listing tidak tersedia.", reply_markup=kb_back_shop())

        a, r, s = shop.stock_counts(lid)
        if a <= 0:
            return await q.message.reply_text("⚠️ Stok habis.", reply_markup=kb_back_shop())

        oid, inv = shop.create_order(u.id, u.username or "", u.first_name or "", lid, int(l["price_int"]))
        context.user_data["shop_wait_proof"] = inv

        pay = shop.get_setting("payment_instructions", "")
        text = (
            f"🧾 INVOICE\n"
            f"Order: {inv}\n"
            f"Listing: {l['game']} - {l['title']}\n"
            f"Harga: {money_idr(l['price_int'])}\n"
            f"Status: MENUNGGU BUKTI BAYAR\n\n"
            f"{pay}\n\n"
            "Setelah bayar, kirim bukti (foto/pdf) ke chat ini.\n"
            f"Wajib sertakan order code di caption: {inv}\n"
        )
        return await q.message.reply_text(text, reply_markup=kb_back_shop())

async def on_shop_proof_media(update: Update, context: ContextTypes.DEFAULT_TYPE, shop: ShopDB, admin_ids: Set[int]):
    """
    Tangkap bukti bayar (foto/pdf/image) TANPA mengganggu fitur converter.
    Filter dibuat khusus PHOTO / PDF / IMAGE.
    """
    msg = update.effective_message
    u = update.effective_user

    # ambil order code dari user_data atau caption
    order_code = context.user_data.get("shop_wait_proof")
    cap = (msg.caption or "").strip()

    if not order_code:
        m = INV_RE.search(cap)
        order_code = m.group(1) if m else None

    if not order_code:
        # bukan bukti shop → jangan balas (biar tidak spam)
        return

    o = shop.get_order(order_code)
    if not o or int(o["user_id"]) != u.id:
        return await msg.reply_text("Order code tidak valid untuk akun ini.")

    file_id = None
    kind = None
    if msg.photo:
        file_id = msg.photo[-1].file_id
        kind = "photo"
    elif msg.document:
        file_id = msg.document.file_id
        kind = "document"
    else:
        return

    shop.set_order_proof(int(o["id"]), file_id, kind, msg.message_id)
    context.user_data.pop("shop_wait_proof", None)

    await msg.reply_text(f"✅ Bukti diterima.\nOrder: {order_code}\nStatus: VERIFYING\nTunggu admin approve.")

    # notify admin + forward
    for admin_id in admin_ids:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    "🧾 BUKTI BAYAR SHOP MASUK\n"
                    f"Order: {order_code}\n"
                    f"User: {u.id} @{u.username or '-'}\n"
                    f"Listing: {o['listing_game']} - {o['listing_title']}\n"
                    f"Amount: {money_idr(o['amount_int'])}\n"
                    "Cek via Panel Web → Shop → Orders"
                )
            )
            await context.bot.forward_message(chat_id=admin_id, from_chat_id=msg.chat_id, message_id=msg.message_id)
        except Exception:
            pass

def register_shop_handlers(app: Application, shop: ShopDB, admin_ids: Set[int]):
    # /shop menu
    app.add_handler(CommandHandler("shop", cmd_shop))

    # /claim
    app.add_handler(CommandHandler("claim", lambda u, c: cmd_claim(u, c, shop)))

    # callback shop:* (dipisah biar tidak bentrok dengan callback lain)
    app.add_handler(CallbackQueryHandler(lambda u, c: on_shop_button(u, c, shop), pattern=r"^shop:"))

    # bukti bayar: hanya PHOTO / PDF / IMAGE agar tidak bentrok converter (mp3/mp4)
    proof_filter = filters.PHOTO | filters.Document.PDF | filters.Document.IMAGE
    app.add_handler(MessageHandler(proof_filter, lambda u, c: on_shop_proof_media(u, c, shop, admin_ids)))
