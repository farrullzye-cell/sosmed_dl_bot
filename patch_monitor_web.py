import re
from pathlib import Path

p = Path("web.py")
src = p.read_text(encoding="utf-8")

if "from monitor_panel import monitor_bp" not in src:
    m = re.search(r"from\s+db\s+import\s+DB\s*\n", src)
    if not m:
        raise SystemExit("GAGAL: tidak ketemu 'from db import DB' di web.py")
    pos = m.end()
    src = src[:pos] + "from monitor_panel import monitor_bp\n" + src[pos:]

if "app.register_blueprint(monitor_bp)" not in src:
    m = re.search(r"app\s*=\s*Flask\([^\n]*\)\s*\n", src)
    if not m:
        raise SystemExit("GAGAL: tidak ketemu 'app = Flask(...)' di web.py")
    pos = m.end()
    src = src[:pos] + "app.register_blueprint(monitor_bp)\n" + src[pos:]

p.write_text(src, encoding="utf-8")
print("OK: monitor blueprint registered.")
