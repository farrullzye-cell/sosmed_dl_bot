import re
from pathlib import Path

p = Path("bot.py")
src = p.read_text(encoding="utf-8")

def ensure_import(line: str):
    global src
    if line.strip() in src:
        return
    # sisip setelah blok import paling atas
    lines = src.splitlines(True)
    insert_at = 0
    for i, ln in enumerate(lines):
        if ln.startswith(("import ", "from ")):
            insert_at = i + 1
        elif ln.strip() == "":
            continue
        else:
            break
    lines.insert(insert_at, line)
    src = "".join(lines)

ensure_import("from support_db import SupportDB\n")
ensure_import("from support_handlers import register_support_handlers\n")
ensure_import("from shop_support_handlers import register_shop_support_handlers\n")

# buat instance support = SupportDB(DB_PATH)
if "support = SupportDB(DB_PATH)" not in src:
    # taruh setelah shop = ShopDB(DB_PATH) kalau ada, kalau tidak taruh setelah db = DB(DB_PATH)
    m = re.search(r"^(\s*)shop\s*=\s*ShopDB\(DB_PATH\)\s*$", src, re.M)
    if m:
        pos = m.end()
        src = src[:pos] + "\n" + f"{m.group(1)}support = SupportDB(DB_PATH)\n" + src[pos:]
    else:
        m2 = re.search(r"^(\s*)db\s*=\s*DB\(DB_PATH\)\s*$", src, re.M)
        if not m2:
            raise SystemExit("GAGAL: tidak ketemu db = DB(DB_PATH)")
        pos = m2.end()
        src = src[:pos] + "\n" + f"{m2.group(1)}support = SupportDB(DB_PATH)\n" + src[pos:]

# register handlers setelah app build
if "register_support_handlers(app, support, ADMIN_IDS)" not in src:
    m = re.search(r"^(\s*)app\s*=\s*ApplicationBuilder\(\)\.token\([^)]+\)\.build\(\)\s*$", src, re.M)
    if not m:
        raise SystemExit("GAGAL: tidak ketemu app = ApplicationBuilder().token(...).build()")
    pos = m.end()
    src = src[:pos] + "\n" + f"{m.group(1)}register_support_handlers(app, support, ADMIN_IDS)\n" + src[pos:]

if "register_shop_support_handlers(app, shop, ADMIN_IDS)" not in src:
    m = re.search(r"register_shop_handlers\(app,\s*shop,\s*ADMIN_IDS\)", src)
    if m:
        # taruh tepat setelah register_shop_handlers
        pos = m.end()
        src = src[:pos] + "\n    register_shop_support_handlers(app, shop, ADMIN_IDS)" + src[pos:]
    else:
        # fallback taruh setelah register_support_handlers
        m2 = re.search(r"register_support_handlers\(app,\s*support,\s*ADMIN_IDS\)", src)
        if not m2:
            raise SystemExit("GAGAL: tidak ketemu register_support_handlers")
        pos = m2.end()
        src = src[:pos] + "\n    register_shop_support_handlers(app, shop, ADMIN_IDS)" + src[pos:]

p.write_text(src, encoding="utf-8")
print("OK: bot.py patched for support chat (downloader + shop).")
