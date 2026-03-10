import re
from pathlib import Path

p = Path("web.py")
src = p.read_text(encoding="utf-8")

# import support_bp
if "from support_panel import support_bp" not in src:
    m = re.search(r"from\s+db\s+import\s+DB\s*\n", src)
    if not m:
        raise SystemExit("GAGAL: tidak ketemu 'from db import DB' di web.py")
    pos = m.end()
    src = src[:pos] + "from support_panel import support_bp\n" + src[pos:]

# register blueprint
if "app.register_blueprint(support_bp)" not in src:
    m = re.search(r"app\s*=\s*Flask\([^\n]*\)\s*\n", src)
    if not m:
        raise SystemExit("GAGAL: tidak ketemu 'app = Flask(...)' di web.py")
    pos = m.end()
    src = src[:pos] + "app.register_blueprint(support_bp)\n" + src[pos:]

p.write_text(src, encoding="utf-8")
print("OK: support blueprint registered.")
