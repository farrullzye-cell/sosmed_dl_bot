import base64
import hashlib
import json
import random
import re
import sqlite3
import string
from urllib.parse import urlparse

import requests


# ---------- helpers ----------
def _clip(s: str, n: int = 3500) -> str:
    s = s or ""
    return s if len(s) <= n else s[:n] + "\n...(truncated)"

def _is_safe_url(url: str) -> bool:
    try:
        p = urlparse(url.strip())
        if p.scheme not in ("http", "https"):
            return False
        host = (p.hostname or "").lower()
        if host in ("localhost",):
            return False
        # block common local patterns without DNS resolving
        if host.startswith("127.") or host.startswith("10.") or host.startswith("192.168.") or host.startswith("169.254."):
            return False
        if host.startswith("172."):
            # block 172.16.0.0 - 172.31.255.255
            try:
                sec = int(host.split(".")[1])
                if 16 <= sec <= 31:
                    return False
            except Exception:
                pass
        return True
    except Exception:
        return False

def _mk_dummy_people(n=20):
    first = ["Adi","Budi","Citra","Dewi","Eka","Fajar","Gita","Hana","Indra","Joko","Kiki","Lia","Mira","Niko","Oki","Putri","Raka","Sari","Tono","Wulan"]
    last = ["Saputra","Wijaya","Pratama","Santoso","Siregar","Wibowo","Hidayat","Permata","Utami","Lestari","Nugroho","Maulana","Yusuf","Sari","Ananda"]
    rows = []
    for i in range(1, n+1):
        fn = random.choice(first)
        ln = random.choice(last)
        name = f"{fn} {ln}"
        email = (fn + "." + ln + str(random.randint(10,99)) + "@example.com").lower()
        age = random.randint(15, 45)
        rows.append((i, name, email, age))
    return rows

def _rows_to_table(cols, rows, max_rows=20):
    rows = rows[:max_rows]
    # simple monospaced table
    colw = [len(c) for c in cols]
    for r in rows:
        for i, v in enumerate(r):
            colw[i] = max(colw[i], len(str(v)))
    def fmt_row(r):
        return " | ".join(str(r[i]).ljust(colw[i]) for i in range(len(cols)))
    sep = "-+-".join("-"*w for w in colw)
    out = [fmt_row(cols), sep]
    for r in rows:
        out.append(fmt_row(r))
    return "\n".join(out)


# ---------- tools ----------
def json_format(text: str) -> str:
    obj = json.loads(text)
    return json.dumps(obj, indent=2, ensure_ascii=False)

def json_minify(text: str) -> str:
    obj = json.loads(text)
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)

def html_preview_file(html: str) -> bytes:
    # return bytes to be saved as .html
    if "<html" not in html.lower():
        html = "<!doctype html><html><head><meta charset='utf-8'><title>Preview</title></head><body>\n" + html + "\n</body></html>"
    return html.encode("utf-8", errors="ignore")

def api_test(raw: str) -> str:
    """
    Format:
    GET https://example.com
    POST https://example.com
    {"json":"body"}   (optional line/body after first line)
    """
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Input kosong.")
    lines = raw.splitlines()
    first = lines[0].strip()
    parts = first.split()
    if len(parts) < 2:
        raise ValueError("Format salah. Contoh: GET https://example.com")
    method = parts[0].upper()
    url = parts[1].strip()

    if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        raise ValueError("Method harus GET/POST/PUT/PATCH/DELETE.")
    if not _is_safe_url(url):
        raise ValueError("URL tidak diizinkan (blok localhost/private).")

    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    json_body = None
    data_body = None
    headers = {"User-Agent": "DevToolsBot/1.0"}

    if body:
        # coba parse json
        try:
            json_body = json.loads(body)
        except Exception:
            data_body = body.encode("utf-8", errors="ignore")

    r = requests.request(method, url, json=json_body, data=data_body, headers=headers, timeout=25)
    text = r.text
    return (
        f"Status: {r.status_code}\n"
        f"URL: {r.url}\n"
        f"Content-Type: {r.headers.get('content-type','-')}\n"
        f"Size: {len(text)} chars\n\n"
        f"Body:\n{_clip(text, 3500)}"
    )

def regex_test(raw: str) -> str:
    """
    Format:
    pattern
    text
    Atau: pattern || text
    """
    raw = (raw or "")
    if "||" in raw:
        pat, txt = raw.split("||", 1)
    else:
        lines = raw.splitlines()
        if len(lines) < 2:
            raise ValueError("Format salah. Kirim 2 baris: pattern lalu text. Atau pattern || text")
        pat, txt = lines[0], "\n".join(lines[1:])
    pat = pat.strip()
    if not pat:
        raise ValueError("Pattern kosong.")
    rx = re.compile(pat)
    matches = list(rx.finditer(txt))
    out = [f"Total match: {len(matches)}"]
    for i, m in enumerate(matches[:10], 1):
        out.append(f"\n#{i} span={m.span()} match={m.group(0)!r}")
        if m.groups():
            out.append(f"  groups={m.groups()!r}")
    if len(matches) > 10:
        out.append("\n...(lebih dari 10 match, dipotong)")
    return "\n".join(out)

def base64_encode(text: str) -> str:
    b = (text or "").encode("utf-8", errors="ignore")
    return base64.b64encode(b).decode("ascii")

def base64_decode(text: str) -> str:
    t = (text or "").strip()
    b = base64.b64decode(t, validate=False)
    return b.decode("utf-8", errors="replace")

def hash_generate(raw: str) -> str:
    """
    format:
    sha256|md5|sha1|sha512 <text>
    """
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Input kosong.")
    parts = raw.split(maxsplit=1)
    if len(parts) < 2:
        raise ValueError("Format: sha256 teksnya")
    algo = parts[0].lower()
    text = parts[1]
    b = text.encode("utf-8", errors="ignore")
    hmap = {
        "md5": hashlib.md5,
        "sha1": hashlib.sha1,
        "sha256": hashlib.sha256,
        "sha512": hashlib.sha512,
    }
    if algo not in hmap:
        raise ValueError("Algo: md5/sha1/sha256/sha512")
    return hmap[algo](b).hexdigest()

def code_minify(raw: str) -> str:
    raw = raw or ""
    # try json minify if valid json
    try:
        return json_minify(raw)
    except Exception:
        pass
    # basic minify: strip lines, remove empty, collapse spaces
    out_lines = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        out_lines.append(re.sub(r"\s+", " ", ln))
    return "".join(out_lines)[:20000]

def code_beautify(raw: str) -> str:
    raw = raw or ""
    # json pretty if valid
    try:
        return json_format(raw)
    except Exception:
        pass
    # basic beautifier: newline after ; { } and indent by braces
    s = raw.replace("\r\n", "\n")
    s = s.replace("{", "{\n").replace("}", "\n}\n").replace(";", ";\n")
    lines = [ln.rstrip() for ln in s.splitlines() if ln.strip() != ""]
    indent = 0
    out = []
    for ln in lines:
        if ln.strip().startswith("}"):
            indent = max(0, indent - 1)
        out.append(("  " * indent) + ln.strip())
        if ln.strip().endswith("{"):
            indent += 1
    return "\n".join(out)[:20000]

def dummy_data(n: int = 10) -> str:
    n = max(1, min(int(n), 50))
    items = []
    domains = ["gmail.com", "yahoo.com", "example.com"]
    cities = ["Jakarta","Bandung","Surabaya","Medan","Makassar","Semarang","Yogyakarta"]
    for i in range(n):
        name = "User" + str(random.randint(1000,9999))
        email = f"{name.lower()}@{random.choice(domains)}"
        phone = "08" + "".join(random.choice(string.digits) for _ in range(10))
        items.append({
            "id": i+1,
            "name": name,
            "email": email,
            "phone": phone,
            "city": random.choice(cities),
        })
    return json.dumps(items, indent=2, ensure_ascii=False)

def sql_test_select(query: str) -> str:
    q = (query or "").strip()
    if not q:
        raise ValueError("Query kosong.")
    if len(q) > 2000:
        raise ValueError("Query terlalu panjang.")
    if ";" in q:
        raise ValueError("Tidak boleh multi-statement (;).")
    if not q.lower().lstrip().startswith("select"):
        raise ValueError("Hanya SELECT yang diizinkan (sandbox).")

    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE people(id INTEGER, name TEXT, email TEXT, age INTEGER);")
    con.executemany("INSERT INTO people(id,name,email,age) VALUES(?,?,?,?)", _mk_dummy_people(20))

    cur = con.execute(q)
    rows = cur.fetchmany(50)
    cols = [d[0] for d in cur.description] if cur.description else []
    con.close()

    if not cols:
        return "Tidak ada kolom hasil."
    if not rows:
        return "Query OK, hasil kosong."

    # turn to tuples
    tup_rows = [tuple(r[c] for c in cols) for r in rows]
    return _rows_to_table(cols, tup_rows, max_rows=20)
