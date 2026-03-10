import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

import requests
from yt_dlp import YoutubeDL

URL_RE = re.compile(r'https?://\S+', re.IGNORECASE)

def extract_url(text: str):
    m = URL_RE.search(text or "")
    return m.group(0) if m else None

def detect_platform(url: str) -> str:
    u = (url or "").lower()
    if "tiktok.com" in u: return "tiktok"
    if "instagram.com" in u: return "instagram"
    if "facebook.com" in u or "fb.watch" in u: return "facebook"
    if "youtube.com" in u or "youtu.be" in u: return "youtube"
    if "twitter.com" in u or "x.com" in u: return "twitter"
    if "pinterest." in u: return "pinterest"
    if "soundcloud.com" in u: return "soundcloud"
    if "reddit.com" in u or "redd.it" in u: return "reddit"
    return "unknown"

def _meta(html: str, prop: str):
    # meta property="og:..."
    m = re.search(
        r'<meta[^>]+property=["\']%s["\'][^>]+content=["\']([^"\']+)["\']' % re.escape(prop),
        html, re.IGNORECASE
    )
    return m.group(1).strip() if m else None

def _download_direct(url: str, out_path: str, headers: dict):
    with requests.get(url, headers=headers, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=256 * 1024):
                if chunk:
                    f.write(chunk)
    return out_path, os.path.getsize(out_path)

def _pinterest_fallback(url: str, download_dir: str, headers: dict):
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    html = r.text

    title = _meta(html, "og:title") or "Pinterest"
    v = _meta(html, "og:video:secure_url") or _meta(html, "og:video")
    img = _meta(html, "og:image:secure_url") or _meta(html, "og:image")

    media_url = v or img
    if not media_url:
        raise RuntimeError("Pinterest fallback gagal: og:video/og:image tidak ditemukan.")

    # tentukan ext
    path = urlparse(media_url).path.lower()
    ext = "mp4" if v else "jpg"
    if "." in path:
        guess = path.rsplit(".", 1)[-1]
        if len(guess) <= 5:
            ext = guess

    Path(download_dir).mkdir(parents=True, exist_ok=True)
    url = expand_short_url(url)
    fp = str(Path(download_dir) / f"pin_{uuid.uuid4().hex}.{ext}")

    # penting: referer untuk pinterest
    h2 = dict(headers)
    h2["Referer"] = "https://www.pinterest.com/"
    file_path, size = _download_direct(media_url, fp, h2)

    return {"title": title, "file_path": file_path, "file_size": size}


def expand_short_url(url: str) -> str:
    """Expand shortlinks seperti pin.it -> pinterest.com/pin/..."""
    u = (url or "").strip()
    if not u:
        return u
    if "pin.it/" not in u:
        return u
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Mobile Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
    }
    try:
        r = requests.get(u, headers=headers, allow_redirects=True, timeout=25)
        return (r.url or u)
    except Exception:
        return u

def download_media(url: str, download_dir: str, audio_only: bool = False):
    Path(download_dir).mkdir(parents=True, exist_ok=True)
    job_id = uuid.uuid4().hex
    outtmpl = str(Path(download_dir) / f"{job_id}.%(ext)s")

    platform = detect_platform(url)

    cookie_file = (os.environ.get("COOKIE_FILE") or "").strip()
    if cookie_file and not os.path.isabs(cookie_file):
        cookie_file = str(Path(cookie_file).resolve())

    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Mobile Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
    }
    if platform == "pinterest":
        headers.update({"Referer": "https://www.pinterest.com/", "Origin": "https://www.pinterest.com"})

    ydl_opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "retries": 3,
        "fragment_retries": 3,
        "concurrent_fragment_downloads": 4,
        "http_headers": headers,
        "geo_bypass": True,
    }
    if cookie_file and os.path.exists(cookie_file):
        ydl_opts["cookiefile"] = cookie_file

    if audio_only:
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
            ]
        })
    else:
        ydl_opts.update({"format": "bv*+ba/best"})

    # ---- try yt-dlp first ----
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title") or "download"
            file_path = info.get("_filename")

            if not file_path or not os.path.exists(file_path):
                cand = list(Path(download_dir).glob(f"{job_id}.*"))
                file_path = str(cand[0]) if cand else None

        if not file_path or not os.path.exists(file_path):
            raise RuntimeError("Gagal menemukan file hasil download.")

        size = os.path.getsize(file_path)
        return {"title": title, "file_path": file_path, "file_size": size}

    except Exception as e:
        # ---- Pinterest fallback (image/video from OG tags) ----
        if platform == "pinterest":
            return _pinterest_fallback(url, download_dir, headers)
        raise
