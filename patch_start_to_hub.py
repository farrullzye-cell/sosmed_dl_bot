from pathlib import Path
import re

p = Path("bot.py")
s = p.read_text(encoding="utf-8")

# 1) Pastikan import cmd_hub ada di posisi aman (setelah blok import)
IMPORT = "from hub_handlers import cmd_hub as hub_cmd_hub"
if IMPORT not in s:
    lines = s.splitlines(True)
    out = []
    paren = 0
    i = 0
    inserted = False
    while i < len(lines):
        ln = lines[i]
        st = ln.strip()
        if not inserted:
            if st.startswith("import ") or st.startswith("from "):
                out.append(ln)
                paren += ln.count("(") - ln.count(")")
                i += 1
                while paren > 0 and i < len(lines):
                    out.append(lines[i])
                    paren += lines[i].count("(") - lines[i].count(")")
                    i += 1
                continue
            if st == "" or st.startswith("#"):
                out.append(ln); i += 1; continue
            out.append(IMPORT + "\n\n")
            inserted = True
            continue
        out.append(ln); i += 1
    if not inserted:
        out.append("\n" + IMPORT + "\n")
    s = "".join(out)

# 2) Sisipkan handler /start yang memanggil HUB sebelum handler /start lama
# Cari baris pertama app.add_handler(CommandHandler("start", ...))
m = re.search(r'^\s*app\.add_handler\(CommandHandler\("start",.*\)\)\s*$', s, re.M)
if m and "hub_cmd_hub" not in s[m.start()-200:m.end()+200]:
    insert_line = '    app.add_handler(CommandHandler("start", lambda u,c: hub_cmd_hub(u,c,ADMIN_IDS)))\n'
    s = s[:m.start()] + insert_line + s[m.start():]
else:
    # fallback: kalau tidak ketemu, sisip setelah app = ApplicationBuilder...build()
    m2 = re.search(r'^(\s*)app\s*=\s*ApplicationBuilder\(\)\.token\([^)]+\)\.build\(\)\s*$', s, re.M)
    if not m2:
        raise SystemExit("GAGAL: tidak ketemu app = ApplicationBuilder().token(...).build()")
    pos = m2.end()
    s = s[:pos] + '\n' + f'{m2.group(1)}app.add_handler(CommandHandler("start", lambda u,c: hub_cmd_hub(u,c,ADMIN_IDS)))\n' + s[pos:]

p.write_text(s, encoding="utf-8")
print("OK: /start sekarang membuka HUB (menu simetris).")
