from pathlib import Path

TARGET_IMPORTS = [
    "from support_db import SupportDB",
    "from support_handlers import register_support_handlers",
    "from shop_support_handlers import register_shop_support_handlers",
]

p = Path("bot.py")
lines = p.read_text(encoding="utf-8").splitlines(True)

# 1) Hapus semua baris import support yang nyelip di mana pun
clean = []
for ln in lines:
    if any(ln.strip() == t for t in TARGET_IMPORTS):
        continue
    clean.append(ln)

# 2) Tentukan posisi aman untuk menyisipkan import: setelah semua blok import selesai
out = []
paren = 0
i = 0
insert_at = None
while i < len(clean):
    ln = clean[i]
    stripped = ln.strip()

    if insert_at is None:
        # masih di area import / header
        if stripped.startswith("import ") or stripped.startswith("from "):
            out.append(ln)
            paren += ln.count("(") - ln.count(")")
            i += 1
            # lanjutkan sampai kurung import tertutup
            while paren > 0 and i < len(clean):
                ln2 = clean[i]
                out.append(ln2)
                paren += ln2.count("(") - ln2.count(")")
                i += 1
            continue

        # lewati baris kosong / komentar sebelum kode mulai
        if stripped == "" or stripped.startswith("#"):
            out.append(ln)
            i += 1
            continue

        # ketemu baris kode pertama non-import -> di sinilah sisipkan import
        insert_at = len(out)
        break

    i += 1

if insert_at is None:
    insert_at = len(out)

# sisa file
out.extend(clean[i:])

# sisipkan import di insert_at (pastikan tidak ada duplikat)
ins = "\n".join(TARGET_IMPORTS) + "\n\n"
out.insert(insert_at, ins)

p.write_text("".join(out), encoding="utf-8")
print("OK: import support dipindahkan ke posisi aman.")
