import re
from pathlib import Path

p = Path("web.py")
src = p.read_text(encoding="utf-8")

# import
if "from control_panel import control_bp" not in src:
    m = re.search(r"from\s+db\s+import\s+DB\s*\n", src)
    if not m:
        raise SystemExit("GAGAL: tidak ketemu 'from db import DB'")
    pos = m.end()
    src = src[:pos] + "from control_panel import control_bp\n" + src[pos:]

# register blueprint
if "app.register_blueprint(control_bp)" not in src:
    m = re.search(r"app\s*=\s*Flask\([^\n]*\)\s*\n", src)
    if not m:
        raise SystemExit("GAGAL: tidak ketemu 'app = Flask(...)'")
    pos = m.end()
    src = src[:pos] + "app.register_blueprint(control_bp)\n" + src[pos:]

p.write_text(src, encoding="utf-8")
print("OK: control blueprint registered.")
