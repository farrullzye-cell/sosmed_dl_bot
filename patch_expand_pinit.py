from pathlib import Path
import re

p = Path("downloader.py")
s = p.read_text(encoding="utf-8")

# Pastikan ada requests import
if "import requests" not in s:
    # sisipkan dekat import lain
    s = s.replace("from urllib.parse import urlparse\n\n", "from urllib.parse import urlparse\n\nimport requests\n", 1)

# Tambah fungsi expand_short_url kalau belum ada
if "def expand_short_url(" not in s:
    insert_point = s.find("def download_media(")
    if insert_point == -1:
        raise SystemExit("GAGAL: tidak ketemu def download_media di downloader.py")

    helper = r'''
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

'''
    s = s[:insert_point] + helper + s[insert_point:]

# Sisipkan pemanggilan expand_short_url di awal download_media
if "url = expand_short_url(url)" not in s:
    # cari baris Path(download_dir).mkdir(...) lalu sisipkan setelahnya
    s = re.sub(
        r'(Path\(download_dir\)\.mkdir\(parents=True, exist_ok=True\)\n)',
        r'\1    url = expand_short_url(url)\n',
        s,
        count=1
    )

p.write_text(s, encoding="utf-8")
print("OK: pin.it auto-expand enabled in downloader.py")
