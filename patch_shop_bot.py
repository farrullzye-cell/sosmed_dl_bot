import re
from pathlib import Path

p = Path("bot.py")
src = p.read_text(encoding="utf-8")

def already_has(line):
    return line in src

changed = False
lines = src.splitlines(True)

# ---- 1) Insert imports ----
need_imports = [
    "from shop_db import ShopDB\n",
    "from shop_handlers import register_shop_handlers\n",
]
if not (already_has("from shop_db import ShopDB") and already_has("from shop_handlers import register_shop_handlers")):
    # cari posisi setelah blok import paling atas
    insert_at = 0
    for i, ln in enumerate(lines):
        if ln.startswith(("import ", "from ")):
            insert_at = i + 1
        elif ln.strip() == "":
            continue
        else:
            break

    # jangan duplikat
    to_add = []
    for imp in need_imports:
        if imp.strip() not in src:
            to_add.append(imp)
    if to_add:
        lines.insert(insert_at, "".join(to_add))
        changed = True

# reload src for next checks
src2 = "".join(lines)

# ---- 2) Insert shop = ShopDB(DB_PATH) after db = DB(DB_PATH) ----
if "shop = ShopDB(DB_PATH)" not in src2:
    m = re.search(r"^(\s*)db\s*=\s*DB\(DB_PATH\)\s*$", src2, re.M)
    if not m:
        raise SystemExit("GAGAL: Tidak ketemu baris: db = DB(DB_PATH)")
    indent = m.group(1)
    pos = m.end()
    src2 = src2[:pos] + "\n" + f"{indent}shop = ShopDB(DB_PATH)\n" + src2[pos:]
    changed = True

# ---- 3) Insert register_shop_handlers(app, shop, ADMIN_IDS) after app build ----
if "register_shop_handlers(app, shop, ADMIN_IDS)" not in src2:
    # cari baris app = ApplicationBuilder().token(...).build()
    m = re.search(r"^(\s*)app\s*=\s*ApplicationBuilder\(\)\.token\(BOT_TOKEN\)\.build\(\)\s*$", src2, re.M)
    if not m:
        # fallback cari ApplicationBuilder token apapun
        m = re.search(r"^(\s*)app\s*=\s*ApplicationBuilder\(\)\.token\([^)]+\)\.build\(\)\s*$", src2, re.M)
    if not m:
        raise SystemExit("GAGAL: Tidak ketemu baris app = ApplicationBuilder().token(...).build()")
    indent = m.group(1)
    pos = m.end()
    src2 = src2[:pos] + "\n" + f"{indent}register_shop_handlers(app, shop, ADMIN_IDS)\n" + src2[pos:]
    changed = True

if not changed:
    print("Tidak ada perubahan (mungkin sudah terpasang).")
else:
    p.write_text(src2, encoding="utf-8")
    print("OK: bot.py berhasil dipatch untuk Shop.")
