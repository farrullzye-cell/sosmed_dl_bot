from __future__ import annotations
import re
import shutil
import subprocess
from pathlib import Path

def _extract_title_h1_h2(html: str):
    h = html or ""
    def pick(pat):
        m = re.search(pat, h, re.IGNORECASE | re.DOTALL)
        if not m:
            return ""
        t = re.sub(r"<[^>]+>", " ", m.group(1))
        t = re.sub(r"\s+", " ", t).strip()
        return t[:120]
    title = pick(r"<title[^>]*>(.*?)</title>")
    h1 = pick(r"<h1[^>]*>(.*?)</h1>")
    h2 = pick(r"<h2[^>]*>(.*?)</h2>")
    return title, h1, h2

def _strip_text(html: str, maxlen: int = 400):
    t = re.sub(r"<script[^>]*>.*?</script>", " ", html or "", flags=re.I | re.S)
    t = re.sub(r"<style[^>]*>.*?</style>", " ", t, flags=re.I | re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return (t[:maxlen] + ("..." if len(t) > maxlen else ""))

def _render_card_with_imagemagick(html: str, out_png: str, width=1280, height=720) -> str:
    conv = shutil.which("convert")
    if not conv:
        raise RuntimeError("ImageMagick tidak ada. Install: pkg install imagemagick")

    title, h1, h2 = _extract_title_h1_h2(html)
    snippet = _strip_text(html, 420)

    # Susun teks card
    lines = []
    lines.append("HTML PREVIEW (CARD)")
    if title: lines.append(f"Title: {title}")
    if h1: lines.append(f"H1: {h1}")
    if h2: lines.append(f"H2: {h2}")
    lines.append("")
    lines.append("Snippet:")
    lines.append(snippet)

    text = "\\n".join(lines)

    out_path = Path(out_png).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Render ke PNG (simple modern card)
    cmd = [
        conv,
        "-size", f"{width}x{height}",
        "xc:#0f172a",
        "-fill", "#e5e7eb",
        "-font", "DejaVu-Sans",
        "-pointsize", "28",
        "-gravity", "NorthWest",
        "-annotate", "+48+48", text,
        "-fill", "#64748b",
        "-pointsize", "18",
        "-gravity", "SouthWest",
        "-annotate", "+48+32", "Tip: Install chromium untuk screenshot asli (real render).",
        str(out_path),
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0 or not out_path.exists():
        raise RuntimeError("convert gagal: " + (p.stderr[-300:] if p.stderr else "unknown"))
    return str(out_path)

def render_html_file_to_png(html_file: str, out_png: str, width: int = 1280, height: int = 720) -> str:
    """
    1) Jika chromium ada: screenshot real.
    2) Jika tidak ada: buat preview card image via ImageMagick.
    """
    html_path = Path(html_file).resolve()
    out_path = Path(out_png).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    html = html_path.read_text(encoding="utf-8", errors="ignore")

    chrome = (
        shutil.which("chromium") or
        shutil.which("chromium-browser") or
        shutil.which("google-chrome") or
        shutil.which("chrome")
    )
    if chrome:
        url = "file://" + str(html_path)
        cmd = [
            chrome,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--hide-scrollbars",
            f"--window-size={width},{height}",
            f"--screenshot={str(out_path)}",
            url,
        ]
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if p.returncode == 0 and out_path.exists():
            return str(out_path)
        # kalau chromium ada tapi gagal, fallback ke card
        return _render_card_with_imagemagick(html, str(out_path), width, height)

    # fallback card
    return _render_card_with_imagemagick(html, str(out_path), width, height)
