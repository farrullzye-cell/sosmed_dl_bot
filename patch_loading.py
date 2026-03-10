from pathlib import Path
import re

p = Path("bot.py")
src = p.read_text(encoding="utf-8").splitlines(True)

# 1) pastikan import Spinner ada, taruh setelah import yang lain (posisi aman)
has_import = any("from loading import Spinner" in ln for ln in src)
if not has_import:
    insert_at = 0
    for i, ln in enumerate(src):
        if ln.startswith(("import ", "from ")):
            insert_at = i + 1
        elif ln.strip() == "":
            continue
        else:
            break
    src.insert(insert_at, "from loading import Spinner\n")

out = []
for i, ln in enumerate(src):
    out.append(ln)

    # 2) sebelum download_media (yang lama) -> start spinner
    if "asyncio.to_thread(download_media" in ln and "Spinner.start" not in (src[i-1] if i > 0 else ""):
        indent = re.match(r"^(\s*)", ln).group(1)
        out.insert(len(out)-1, f"{indent}spin = await Spinner.start(update, context, 'Sedang download / proses', interval=1.4)\n")

    # 3) setelah download_media -> stop spinner
    if "asyncio.to_thread(download_media" in ln:
        indent = re.match(r"^(\s*)", ln).group(1)
        out.append(f"{indent}await spin.stop('✅ Download selesai, mengirim...')\n")

    # 4) sebelum convert_to_mp3 -> start spinner
    if "asyncio.to_thread(convert_to_mp3" in ln and "Spinner.start" not in (src[i-1] if i > 0 else ""):
        indent = re.match(r"^(\s*)", ln).group(1)
        out.insert(len(out)-1, f"{indent}spin = await Spinner.start(update, context, 'Sedang convert ke MP3', interval=1.4)\n")

    # 5) setelah convert_to_mp3 -> stop spinner
    if "asyncio.to_thread(convert_to_mp3" in ln:
        indent = re.match(r"^(\s*)", ln).group(1)
        out.append(f"{indent}await spin.stop('✅ Convert selesai, mengirim...')\n")

    # 6) kalau ada except Exception as e: -> coba stop spinner (aman walau spin belum ada)
    if re.search(r"^\s*except\s+Exception\s+as\s+e\s*:", ln):
        indent = re.match(r"^(\s*)", ln).group(1) + "    "
        out.append(f"{indent}try:\n")
        out.append(f"{indent}    await spin.stop('❌ Gagal.')\n")
        out.append(f"{indent}except Exception:\n")
        out.append(f"{indent}    pass\n")

p.write_text("".join(out), encoding="utf-8")
print("OK: Spinner loading ditambahkan ke bot.py")
