import os
import re
import subprocess
from urllib.parse import quote_plus

import requests
import segno

URL_RE = re.compile(r'https?://\S+', re.IGNORECASE)

def extract_url(text: str):
    m = URL_RE.search(text or "")
    return m.group(0) if m else None

# ===== QR Generator =====
def make_qr_png(text: str, out_path: str):
    qr = segno.make(text)
    qr.save(out_path, scale=10, border=2)  # butuh pypng agar output PNG
    return out_path

# ===== Shortlink (TinyURL) =====
def short_tinyurl(url: str) -> str:
    api = "https://tinyurl.com/api-create.php?url=" + quote_plus(url)
    r = requests.get(api, timeout=20)
    r.raise_for_status()
    return r.text.strip()

# ===== Weather (Open-Meteo) =====
WEATHER_CODE_ID = {
    0: "Cerah", 1: "Sebagian cerah", 2: "Berawan", 3: "Mendung",
    45: "Berkabut", 48: "Kabut (rime)",
    51: "Gerimis ringan", 53: "Gerimis sedang", 55: "Gerimis lebat",
    61: "Hujan ringan", 63: "Hujan sedang", 65: "Hujan lebat",
    71: "Salju ringan", 73: "Salju sedang", 75: "Salju lebat",
    80: "Hujan lokal ringan", 81: "Hujan lokal sedang", 82: "Hujan lokal lebat",
    95: "Badai petir", 96: "Badai petir + hujan es", 99: "Badai petir hebat",
}

def weather_city(city: str, language: str = "id") -> str:
    city = (city or "").strip()
    if not city:
        raise ValueError("Nama kota kosong.")

    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "language": language, "format": "json"},
        timeout=20
    )
    geo.raise_for_status()
    g = geo.json()
    if not g.get("results"):
        return f"Tidak ditemukan lokasi untuk: {city}"

    loc = g["results"][0]
    lat = loc["latitude"]; lon = loc["longitude"]
    name = loc.get("name", city)
    admin1 = loc.get("admin1", "")
    country = loc.get("country", "")

    w = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,wind_speed_10m,weather_code",
            "timezone": "auto",
        },
        timeout=20
    )
    w.raise_for_status()
    data = w.json()
    cur = data.get("current", {})
    temp = cur.get("temperature_2m")
    wind = cur.get("wind_speed_10m")
    code = cur.get("weather_code")
    desc = WEATHER_CODE_ID.get(code, f"Kode cuaca: {code}")

    place = f"{name}"
    if admin1: place += f", {admin1}"
    if country: place += f", {country}"

    return (
        f"{place}\n"
        f"- Suhu: {temp}°C\n"
        f"- Angin: {wind} km/h\n"
        f"- Kondisi: {desc}\n"
    )

# ===== Translate (MyMemory) =====
def translate_mymemory(text: str, to_lang: str = "id", from_lang: str = "auto") -> str:
    text = (text or "").strip()
    if not text:
        raise ValueError("Teks kosong.")

    pair = f"{from_lang}|{to_lang}"
    r = requests.get(
        "https://api.mymemory.translated.net/get",
        params={"q": text, "langpair": pair},
        timeout=25
    )
    r.raise_for_status()
    j = r.json()
    out = j.get("responseData", {}).get("translatedText")
    if not out:
        return "Gagal translate."
    return out

# ===== Search Engine (SearxNG -> fallback Wikipedia) =====
SEARX_INSTANCES = [
    "https://searx.be",
    "https://search.bus-hit.me",
    "https://searx.fmac.xyz",
]

def searx_search(query: str, limit: int = 5):
    query = (query or "").strip()
    if not query:
        raise ValueError("Query kosong.")
    for base in SEARX_INSTANCES:
        try:
            r = requests.get(
                base + "/search",
                params={
                    "q": query,
                    "format": "json",
                    "language": "id-ID",
                    "categories": "general",
                    "safesearch": 0,
                },
                timeout=20
            )
            r.raise_for_status()
            j = r.json()
            res = j.get("results", [])[:limit]
            out = []
            for it in res:
                out.append({
                    "title": it.get("title") or "",
                    "href": it.get("url") or "",
                    "body": (it.get("content") or "").strip(),
                    "source": "searxng"
                })
            if out:
                return out
        except Exception:
            continue
    return []

def wikipedia_search(query: str, limit: int = 5, lang: str = "id"):
    query = (query or "").strip()
    if not query:
        raise ValueError("Query kosong.")

    r = requests.get(
        f"https://{lang}.wikipedia.org/w/api.php",
        params={
            "action": "opensearch",
            "search": query,
            "limit": limit,
            "namespace": 0,
            "format": "json",
        },
        timeout=20
    )
    r.raise_for_status()
    j = r.json()
    titles = j[1] if len(j) > 1 else []
    descs = j[2] if len(j) > 2 else []
    urls = j[3] if len(j) > 3 else []
    out = []
    for i in range(min(len(titles), len(urls))):
        out.append({
            "title": titles[i],
            "href": urls[i],
            "body": descs[i] if i < len(descs) else "",
            "source": "wikipedia"
        })
    return out

def web_search(query: str, limit: int = 5):
    # coba searxng dulu (web search), kalau kosong fallback wikipedia
    res = searx_search(query, limit)
    if res:
        return res
    return wikipedia_search(query, limit, "id")

# ===== Converter (ffmpeg -> mp3) =====
def convert_to_mp3(in_path: str, out_path: str):
    cmd = ["ffmpeg", "-y", "-i", in_path, "-vn", "-acodec", "libmp3lame", "-b:a", "192k", out_path]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg error: " + (p.stderr[-800:] if p.stderr else "unknown"))
    return out_path
