import re
from pathlib import Path

p = Path("bot.py")
src = p.read_text(encoding="utf-8")

IMPORT = "from hub_handlers import register_hub_handlers"

# hapus duplikat
src = "\n".join([ln for ln in src.splitlines() if ln.strip() != IMPORT]) + "\n"

# sisipkan import di posisi aman (setelah blok import)
lines = src.splitlines(True)
out = []
paren = 0
i = 0
insert_at = None
while i < len(lines):
    ln = lines[i]
    s = ln.strip()
    if insert_at is None:
        if s.startswith("import ") or s.startswith("from "):
            out.append(ln)
            paren += ln.count("(") - ln.count(")")
            i += 1
            while paren > 0 and i < len(lines):
                out.append(lines[i])
                paren += lines[i].count("(") - lines[i].count(")")
                i += 1
            continue
        if s == "" or s.startswith("#"):
            out.append(ln); i += 1; continue
        insert_at = len(out)
        break
    i += 1
if insert_at is None:
    insert_at = len(out)
out.extend(lines[i:])
out.insert(insert_at, IMPORT + "\n\n")
src2 = "".join(out)

# register call setelah app build
if "register_hub_handlers(app, ADMIN_IDS)" not in src2:
    m = re.search(r"^(\s*)app\s*=\s*ApplicationBuilder\(\)\.token\([^)]+\)\.build\(\)\s*$", src2, re.M)
    if not m:
        raise SystemExit("GAGAL: tidak ketemu app = ApplicationBuilder().token(...).build()")
    pos = m.end()
    src2 = src2[:pos] + "\n" + f"{m.group(1)}register_hub_handlers(app, ADMIN_IDS)\n" + src2[pos:]

p.write_text(src2, encoding="utf-8")
print("OK: /hub & hub buttons registered.")
