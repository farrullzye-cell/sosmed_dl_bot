import os
import requests

def _clip(s: str, n: int = 6000) -> str:
    s = s or ""
    return s if len(s) <= n else s[:n] + "\n...(truncated)"

def default_tips():
    return (
        "Rekomendasi (default):\n"
        "• Tambahkan <title> dan meta description.\n"
        "• Struktur heading H1 → H2 → H3 rapi.\n"
        "• CTA jelas (tombol utama/aksi).\n"
        "• Perbaiki kontras warna & ukuran font.\n"
        "• Optimasi gambar (ukuran kecil, lazy-load).\n"
        "• Tambah navigasi & footer.\n"
        "• Pastikan responsive (mobile first).\n"
        "• Tambahkan alt text pada gambar (aksesibilitas/SEO)."
    )

def ai_site_recommendations(html: str) -> str:
    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    model = (os.environ.get("OPENAI_MODEL") or "gpt-4.1-mini").strip()
    if not key:
        return default_tips()

    html_snip = _clip(html, 6000)
    prompt = (
        "Beri rekomendasi UI/UX + SEO + aksesibilitas berdasarkan HTML berikut.\n"
        "Output bahasa Indonesia, maksimal 10 poin bullet, ringkas tapi jelas.\n"
        "Tambahkan juga: Skor UX 1-10 dan Skor SEO 1-10.\n\n"
        "HTML:\n" + html_snip
    )

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": 0.4,
                "messages": [
                    {"role": "system", "content": "Jawab singkat, praktis, dan terstruktur."},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=45
        )
        j = r.json()
        if not j.get("choices"):
            return "Rekomendasi AI gagal.\n\n" + default_tips()
        return (j["choices"][0]["message"]["content"] or "").strip() or default_tips()
    except Exception:
        return "Rekomendasi AI gagal (timeout/error).\n\n" + default_tips()
