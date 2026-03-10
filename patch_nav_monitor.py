from pathlib import Path

p = Path("templates/base.html")
s = p.read_text(encoding="utf-8")

if "/monitor/" in s:
    print("Navbar sudah ada Monitor.")
    raise SystemExit(0)

needle = '<a class="navbar-item" href="/downloads"'
if needle in s:
    s = s.replace(
        needle,
        '<a class="navbar-item" href="/monitor/"><i class="fa-solid fa-microchip mr-2"></i>Monitor</a>\n          ' + needle
    )
    p.write_text(s, encoding="utf-8")
    print("OK: Monitor link ditambahkan ke navbar.")
else:
    print("Tidak menemukan pola navbar untuk dipatch. Tambahkan manual link /monitor/.")
