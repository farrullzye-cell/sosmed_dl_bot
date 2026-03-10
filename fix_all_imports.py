from pathlib import Path

MOVE_IMPORTS = [
    "from shop_db import ShopDB",
    "from shop_handlers import register_shop_handlers",
    "from support_db import SupportDB",
    "from support_handlers import register_support_handlers",
    "from shop_support_handlers import register_shop_support_handlers",
    "from loading import Spinner",
]

p = Path("bot.py")
lines = p.read_text(encoding="utf-8").splitlines(True)

# 1) buang baris import tambahan yang nyelip di mana pun
clean = []
for ln in lines:
    if ln.strip() in MOVE_IMPORTS:
        continue
    clean.append(ln)

# 2) cari posisi aman: setelah semua blok import (termasuk import yang pakai tanda kurung) selesai
out = []
paren = 0
i = 0
insert_at = None

while i < len(clean):
    ln = clean[i]
    s = ln.strip()

    if insert_at is None:
        if s.startswith("import ") or s.startswith("from "):
            out.append(ln)
            paren += ln.count("(") - ln.count(")")
            i += 1
            while paren > 0 and i < len(clean):
                ln2 = clean[i]
                out.append(ln2)
                paren += ln2.count("(") - ln2.count(")")
                i += 1
            continue

        if s == "" or s.startswith("#"):
            out.append(ln)
            i += 1
            continue

        insert_at = len(out)
        break

    i += 1

if insert_at is None:
    insert_at = len(out)

out.extend(clean[i:])

# 3) sisipkan import tambahan di tempat aman
ins = "\n".join(MOVE_IMPORTS) + "\n\n"
out.insert(insert_at, ins)

p.write_text("".join(out), encoding="utf-8")
print("OK: import tambahan dipindahkan ke posisi aman.")
