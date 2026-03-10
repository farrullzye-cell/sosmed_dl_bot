from pathlib import Path

p = Path("shop_handlers.py")
s = p.read_text(encoding="utf-8")

old = """def kb_shop_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🕹 Katalog Akun", callback_data="shop:katalog")],
        [InlineKeyboardButton("ℹ️ Cara Bayar", callback_data="shop:payinfo"),
         InlineKeyboardButton("🎫 Cara Claim", callback_data="shop:claimhelp")],
        [InlineKeyboardButton("💬 Support", callback_data="shop:support")],
    ])
"""

new = """def kb_shop_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🕹 Katalog Akun", callback_data="shop:katalog")],
        [InlineKeyboardButton("🧾 Order Saya", callback_data="shop:myorders")],
        [InlineKeyboardButton("ℹ️ Cara Bayar", callback_data="shop:payinfo"),
         InlineKeyboardButton("🎫 Cara Claim", callback_data="shop:claimhelp")],
        [InlineKeyboardButton("💬 Support", callback_data="shop:support")],
    ])
"""

if old not in s:
    raise SystemExit("GAGAL: pola kb_shop_menu tidak cocok (file berbeda).")

s = s.replace(old, new)

marker = 'if data == "shop:katalog":'
if marker in s and 'if data == "shop:myorders":' not in s:
    insert = """
    if data == "shop:myorders":
        u = update.effective_user
        rows = shop.list_orders(status=None, limit=100)
        mine = [r for r in rows if int(r["user_id"]) == u.id][:10]
        if not mine:
            return await q.message.reply_text("Belum ada order.", reply_markup=kb_back_shop())
        lines = ["🧾 ORDER SAYA (10 terakhir):"]
        for r in mine:
            lines.append(f"• {r['order_code']} | {r['listing_game']} - {r['listing_title']} | {r['status']}")
        return await q.message.reply_text("\\n".join(lines), reply_markup=kb_back_shop())
"""
    s = s.replace(marker, insert + "\n" + marker, 1)

p.write_text(s, encoding="utf-8")
print("OK: Shop menu now has 'Order Saya' button.")
