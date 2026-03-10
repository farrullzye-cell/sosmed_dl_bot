import re
from pathlib import Path

p = Path("web.py")
src = p.read_text(encoding="utf-8")

# 1) import shop_bp
if "from shop_panel import shop_bp" not in src:
    # sisipkan setelah import DB atau setelah import utils/db
    m = re.search(r"from\s+db\s+import\s+DB\s*\n", src)
    if not m:
        raise SystemExit("GAGAL: tidak ketemu 'from db import DB' di web.py")
    pos = m.end()
    src = src[:pos] + "from shop_panel import shop_bp\n" + src[pos:]

# 2) register blueprint setelah app = Flask(...)
if "app.register_blueprint(shop_bp)" not in src:
    m = re.search(r"app\s*=\s*Flask\([^\n]*\)\s*\n", src)
    if not m:
        raise SystemExit("GAGAL: tidak ketemu 'app = Flask(...)' di web.py")
    pos = m.end()
    src = src[:pos] + "app.register_blueprint(shop_bp)\n" + src[pos:]

p.write_text(src, encoding="utf-8")
print("OK: web.py dipatch (Shop blueprint registered).")
