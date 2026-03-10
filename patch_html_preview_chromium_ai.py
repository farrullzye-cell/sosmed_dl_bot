from pathlib import Path
import re

p = Path("dev_handlers.py")
lines = p.read_text(encoding="utf-8").splitlines(True)

# ensure imports exist (safe append near top)
def ensure_import(stmt: str):
    global lines
    if any(l.strip() == stmt for l in lines):
        return
    # insert after imports block
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
            # insert here
            out.append(stmt + "\n")
            out.append("\n")
            inserted = True
            continue
        out.append(ln)
        i += 1
    if not inserted:
        out.append("\n" + stmt + "\n")
    lines = out

# add needed imports
ensure_import("import asyncio")
ensure_import("from ai_helper import ai_site_recommendations")
ensure_import("from html_screenshot import render_html_file_to_png")

# replace block if tool == "html":
out = []
i = 0
replaced = False
while i < len(lines):
    ln = lines[i]
    if re.match(r'^\s*if tool == "html"\s*:\s*$', ln):
        indent = re.match(r"^(\s*)", ln).group(1)
        # skip old block until we hit a line that equals indent + "return INPUT"
        j = i + 1
        while j < len(lines):
            if lines[j].startswith(indent + "return INPUT"):
                j += 1
                break
            j += 1

        new_block = f'''{indent}if tool == "html":
{indent}    # rekomendasi AI (caption max 1024)
{indent}    tips = await asyncio.to_thread(ai_site_recommendations, text)
{indent}    tips_caption = tips[:900] + ("..." if len(tips) > 900 else "")

{indent}    os.makedirs("downloads", exist_ok=True)
{indent}    html_file = f"downloads/preview_{{uuid.uuid4().hex}}.html"
{indent}    png_file = f"downloads/preview_{{uuid.uuid4().hex}}.png"
{indent}    Path(html_file).write_bytes(T.html_preview_file(text))

{indent}    try:
{indent}        await asyncio.to_thread(render_html_file_to_png, html_file, png_file, 1280, 720)
{indent}        with open(png_file, "rb") as f:
{indent}            await update.message.reply_photo(photo=f, caption="🧾 HTML Preview (Screenshot)\\n\\n" + tips_caption)
{indent}    except Exception as e:
{indent}        await update.message.reply_text(f"⚠️ Screenshot gagal: {{e}}\\nMengirim file HTML saja.")
{indent}        await update.message.reply_document(document=open(html_file, "rb"), caption="🧾 HTML Preview (file)\\n\\n" + tips_caption)

{indent}    for fp in (html_file, png_file):
{indent}        try: os.remove(fp)
{indent}        except Exception: pass

{indent}    return INPUT
'''
        out.append(new_block)
        out.extend(lines[j:])
        replaced = True
        break
    else:
        out.append(ln)
        i += 1

if not replaced:
    raise SystemExit("GAGAL: tidak menemukan blok `if tool == \"html\":` di dev_handlers.py")

p.write_text("".join(out), encoding="utf-8")
print("OK: HTML Preview patched to screenshot (chromium) + AI caption, with fallback.")
