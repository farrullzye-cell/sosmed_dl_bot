from pathlib import Path
import re

p = Path("dev_handlers.py")
lines = p.read_text(encoding="utf-8").splitlines(True)

def insert_import(stmt: str):
    global lines
    if any(l.strip() == stmt for l in lines):
        return
    out = []
    paren = 0
    i = 0
    inserted = False
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not inserted:
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
            out.append(stmt + "\n")
            inserted = True
            continue
        out.append(ln); i += 1
    if not inserted:
        out.append("\n" + stmt + "\n")
    lines = out

# ensure imports
insert_import("import asyncio")
insert_import("from ai_helper import ai_site_recommendations")
insert_import("from html_screenshot import render_html_file_to_png")

# find async def dev_input
start = None
for i, ln in enumerate(lines):
    if re.match(r"^\s*async\s+def\s+dev_input\s*\(", ln):
        start = i
        break
if start is None:
    raise SystemExit("GAGAL: async def dev_input(...) tidak ditemukan.")

# find if tool == "html": inside dev_input
# Determine function body indent from first non-empty line after def
body_indent = None
for j in range(start+1, len(lines)):
    if lines[j].strip() == "":
        continue
    body_indent = re.match(r"^(\s*)", lines[j]).group(1)
    break
if body_indent is None:
    raise SystemExit("GAGAL: body indent tidak ditemukan.")

html_if_idx = None
for k in range(start+1, len(lines)):
    if lines[k].startswith(body_indent) and re.match(r'^\s*if\s+tool\s*==\s*"html"\s*:\s*$', lines[k]):
        html_if_idx = k
        break
    # stop if another def at col 0 appears (safety)
    if re.match(r"^\s*async\s+def\s+|\s*def\s+", lines[k]) and not lines[k].startswith(body_indent):
        pass
if html_if_idx is None:
    raise SystemExit('GAGAL: blok `if tool == "html":` tidak ditemukan di dev_input.')

# Replace block from if tool == "html": until the matching "return INPUT" at same indent level
indent = re.match(r"^(\s*)", lines[html_if_idx]).group(1)
end = None
for m in range(html_if_idx+1, len(lines)):
    if lines[m].startswith(indent) and lines[m].strip() == "return INPUT":
        end = m + 1
        break
if end is None:
    raise SystemExit("GAGAL: tidak ketemu `return INPUT` untuk blok html.")

new_block = f'''{indent}if tool == "html":
{indent}    # AI recommendations (caption max ~1024)
{indent}    tips = await asyncio.to_thread(ai_site_recommendations, text)
{indent}    tips_caption = tips[:900] + ("..." if len(tips) > 900 else "")

{indent}    os.makedirs("downloads", exist_ok=True)
{indent}    html_file = f"downloads/preview_{{uuid.uuid4().hex}}.html"
{indent}    png_file = f"downloads/preview_{{uuid.uuid4().hex}}.png"
{indent}    Path(html_file).write_bytes(T.html_preview_file(text))

{indent}    try:
{indent}        await asyncio.to_thread(render_html_file_to_png, html_file, png_file, 1280, 720)
{indent}        with open(png_file, "rb") as f:
{indent}            await update.message.reply_photo(
{indent}                photo=f,
{indent}                caption="🧾 HTML Preview (Screenshot)\\n\\n" + tips_caption
{indent}            )
{indent}    except Exception as e:
{indent}        await update.message.reply_text(f"⚠️ Screenshot gagal: {{e}}\\nMengirim file HTML saja.")
{indent}        with open(html_file, "rb") as f:
{indent}            await update.message.reply_document(
{indent}                document=f,
{indent}                caption="🧾 HTML Preview (file)\\n\\n" + tips_caption
{indent}            )

{indent}    for fp in (html_file, png_file):
{indent}        try: os.remove(fp)
{indent}        except Exception: pass

{indent}    return INPUT
'''

lines = lines[:html_if_idx] + [new_block] + lines[end:]
p.write_text("".join(lines), encoding="utf-8")
print("OK: HTML Preview block fixed safely.")
