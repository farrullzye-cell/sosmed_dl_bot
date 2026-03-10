from pathlib import Path
import re

p = Path("shop_handlers.py")
s = p.read_text(encoding="utf-8")

# tambah tombol di kb_shop_menu
if "shop:myorders" not in s:
    s = s.replace(
        '[InlineKeyboardButton("🕹 Katalog Akun", callback_data="shop:katalog")],',
        '[InlineKeyboardButton("🕹 Katalog Akun", callback_data="shop:katalog")],\n'
        '        [InlineKeyboardButton("🧾 Order Saya", callback_data="shop:myorders")],'
    )

marker = 'if data == "shop:katalog":'
idx = s.find(marker)
if idx == -1:
    raise SystemExit('GAGAL: tidak menemukan marker if data == "shop:katalog":')

# ambil indent marker
line_start = s.rfind("\n", 0, idx) + 1
indent = re.match(r"[ \t]*", s[line_start:idx]).group(0)
indent2 = indent + "    "

if 'if data == "shop:myorders":' not in s:
    insert_block = (
        indent + 'if data == "shop:myorders":\n'
        + indent2 + 'u = update.effective_user\n'
        + indent2 + "rows = shop.list_orders(status=None, limit=100)\n"
        + indent2 + 'mine = [r for r in rows if int(r["user_id"]) == u.id][:10]\n'
        + indent2 + "if not mine:\n"
        + indent2 + '    return await q.message.reply_text("Belum ada order.", reply_markup=kb_back_shop())\n'
        + indent2 + 'lines = ["🧾 ORDER SAYA (10 terakhir):"]\n'
        + indent2 + "for r in mine:\n"
        + indent2 + '    lines.append("• %s | %s - %s | %s" % (r["order_code"], r["listing_game"], r["listing_title"], r["status"]))\n'
        + indent2 + 'return await q.message.reply_text("\\n".join(lines), reply_markup=kb_back_shop())\n\n'
    )
    s = s[:line_start] + insert_block + s[line_start:]

p.write_text(s, encoding="utf-8")
print("OK: patched Order Saya button + handler.")
