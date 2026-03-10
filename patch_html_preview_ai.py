from pathlib import Path

p = Path("dev_handlers.py")
src = p.read_text(encoding="utf-8")

# add imports safely
if "import asyncio" not in src:
    src = src.replace("import os\n", "import os\nimport asyncio\n", 1)

if "from html_screenshot import render_html_to_png" not in src:
    src = src.replace("import dev_tools as T\n", "import dev_tools as T\nfrom html_screenshot import render_html_to_png\n", 1)

if "from ai_helper import ai_site_recommendations" not in src:
    src = src.replace("from html_screenshot import render_html_to_png\n", "from html_screenshot import render_html_to_png\nfrom ai_helper import ai_site_recommendations\n", 1)

old = """        if tool == "html":
            b = T.html_preview_file(text)
            os.makedirs("downloads", exist_ok=True)
            fn = f"downloads/preview_{uuid.uuid4().hex}.html"
            Path(fn).write_bytes(b)
            await update.message.reply_document(document=open(fn, "rb"), caption="🧾 HTML Preview (download file)")
            try: os.remove(fn)
            except Exception: pass
            return INPUT
"""

new = """        if tool == "html":
            # 1) buat rekomendasi AI (non-blocking)
            tips = await asyncio.to_thread(ai_site_recommendations, text)
            # caption Telegram max ~1024 chars (amanin)
            tips_caption = tips[:900] + ("..." if len(tips) > 900 else "")

            # 2) render screenshot -> kirim gambar
            os.makedirs("downloads", exist_ok=True)
            png = f"downloads/html_{uuid.uuid4().hex}.png"
            html_file = f"downloads/html_{uuid.uuid4().hex}.html"

            # simpan html juga (opsional, untuk download)
            Path(html_file).write_bytes(T.html_preview_file(text))

            try:
                await asyncio.to_thread(render_html_to_png, text, png, 1280, 720)
                with open(png, "rb") as f:
                    await update.message.reply_photo(photo=f, caption="🧾 HTML Preview (Screenshot)\\n\\n" + tips_caption)
            except Exception as e:
                # fallback: jika playwright/chromium tidak ada, kirim file html
                await update.message.reply_text(f"⚠️ Screenshot gagal ({e}). Mengirim file HTML saja.")
                await update.message.reply_document(document=open(html_file, "rb"), caption="🧾 HTML Preview (file)\\n\\n" + tips_caption)

            # bersih-bersih
            for fp in (png, html_file):
                try: os.remove(fp)
                except Exception: pass

            return INPUT
"""

if old not in src:
    raise SystemExit("GAGAL: blok html preview lama tidak ditemukan. dev_handlers.py Anda mungkin berbeda.")

src = src.replace(old, new)
p.write_text(src, encoding="utf-8")
print("OK: HTML Preview sekarang kirim screenshot + caption rekomendasi AI (dengan fallback).")
