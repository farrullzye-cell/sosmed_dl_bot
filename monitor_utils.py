from __future__ import annotations
import os
import time
import json
import shutil
import subprocess
from pathlib import Path

_prev = {
    "cpu_total": None,
    "cpu_idle": None,
    "net_rx": None,
    "net_tx": None,
    "ts": None,
}

def _read_first(path: str) -> str | None:
    try:
        return Path(path).read_text().strip()
    except Exception:
        return None

def _read_meminfo() -> dict:
    mem = {}
    try:
        for ln in Path("/proc/meminfo").read_text().splitlines():
            if ":" not in ln:
                continue
            k, v = ln.split(":", 1)
            v = v.strip().split()
            # usually kB
            mem[k] = int(v[0]) * 1024 if v and v[0].isdigit() else 0
    except Exception:
        pass

    total = mem.get("MemTotal", 0)
    avail = mem.get("MemAvailable", 0)
    free = mem.get("MemFree", 0)
    cached = mem.get("Cached", 0)
    buffers = mem.get("Buffers", 0)

    used = max(0, total - avail) if avail else max(0, total - free)
    pct = (used / total * 100.0) if total else 0.0

    return {
        "total": total,
        "available": avail,
        "used": used,
        "percent": pct,
        "free": free,
        "cached": cached,
        "buffers": buffers,
    }

def _read_cpu_times() -> tuple[int,int] | tuple[None,None]:
    try:
        # first line: cpu user nice system idle iowait irq softirq steal guest guest_nice
        ln = Path("/proc/stat").read_text().splitlines()[0]
        parts = ln.split()
        nums = list(map(int, parts[1:]))
        total = sum(nums)
        idle = nums[3] + (nums[4] if len(nums) > 4 else 0)  # idle + iowait
        return total, idle
    except Exception:
        return None, None

def cpu_percent() -> float:
    total, idle = _read_cpu_times()
    if total is None:
        return 0.0

    pt = _prev["cpu_total"]
    pi = _prev["cpu_idle"]
    _prev["cpu_total"] = total
    _prev["cpu_idle"] = idle

    if pt is None or pi is None:
        return 0.0

    dt = total - pt
    di = idle - pi
    if dt <= 0:
        return 0.0
    usage = 100.0 * (1.0 - (di / dt))
    if usage < 0: usage = 0.0
    if usage > 100: usage = 100.0
    return usage

def load_avg():
    try:
        one, five, fifteen = os.getloadavg()
        return {"1m": one, "5m": five, "15m": fifteen}
    except Exception:
        return {"1m": 0.0, "5m": 0.0, "15m": 0.0}

def uptime_seconds() -> int:
    try:
        s = Path("/proc/uptime").read_text().split()[0]
        return int(float(s))
    except Exception:
        return 0

def fmt_bytes(n: int) -> str:
    n = int(n or 0)
    units = ["B","KB","MB","GB","TB"]
    u = 0
    x = float(n)
    while x >= 1024 and u < len(units)-1:
        x /= 1024
        u += 1
    return f"{x:.1f} {units[u]}"

def disk_info(paths: list[str]) -> list[dict]:
    out = []
    for p in paths:
        try:
            du = shutil.disk_usage(p)
            used = du.used
            total = du.total
            pct = (used / total * 100.0) if total else 0.0
            out.append({
                "path": p,
                "total": total,
                "used": used,
                "free": du.free,
                "percent": pct
            })
        except Exception:
            continue
    return out

def net_totals() -> tuple[int,int]:
    rx = 0
    tx = 0
    try:
        lines = Path("/proc/net/dev").read_text().splitlines()
        for ln in lines[2:]:
            if ":" not in ln:
                continue
            iface, data = ln.split(":", 1)
            iface = iface.strip()
            if iface == "lo":
                continue
            cols = data.split()
            if len(cols) >= 16:
                rx += int(cols[0])
                tx += int(cols[8])
    except Exception:
        pass
    return rx, tx

def net_rates() -> dict:
    rx, tx = net_totals()
    now = time.time()

    prx = _prev["net_rx"]
    ptx = _prev["net_tx"]
    pts = _prev["ts"]

    _prev["net_rx"] = rx
    _prev["net_tx"] = tx
    _prev["ts"] = now

    if prx is None or ptx is None or pts is None:
        return {"rx_total": rx, "tx_total": tx, "rx_s": 0.0, "tx_s": 0.0}

    dt = max(0.001, now - pts)
    return {
        "rx_total": rx,
        "tx_total": tx,
        "rx_s": (rx - prx) / dt,
        "tx_s": (tx - ptx) / dt,
    }

def temperature_c() -> float | None:
    # common Android thermal path
    cand = [
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/class/thermal/thermal_zone1/temp",
    ]
    for p in cand:
        t = _read_first(p)
        if not t:
            continue
        try:
            v = float(t)
            # usually millidegree
            if v > 1000:
                v = v / 1000.0
            if -20 <= v <= 120:
                return v
        except Exception:
            pass
    return None

def top_processes(limit=8) -> list[dict]:
    """
    Safe read-only. Uses `ps` output if available.
    """
    try:
        # -A supported by procps in termux
        cmd = ["sh", "-lc", f"ps -A -o pid,pcpu,pmem,comm,args --sort=-pcpu | head -n {limit+1}"]
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if p.returncode != 0:
            return []
        lines = p.stdout.splitlines()
        if len(lines) <= 1:
            return []
        out = []
        for ln in lines[1:]:
            ln = ln.strip()
            if not ln:
                continue
            # split first 4 cols, rest args
            parts = ln.split(None, 4)
            if len(parts) < 4:
                continue
            pid = parts[0]
            pcpu = parts[1]
            pmem = parts[2]
            comm = parts[3]
            args = parts[4] if len(parts) > 4 else ""
            out.append({
                "pid": pid,
                "cpu": pcpu,
                "mem": pmem,
                "comm": comm,
                "args": args[:160],
            })
        return out
    except Exception:
        return []

def stats() -> dict:
    mem = _read_meminfo()
    cpu = cpu_percent()
    la = load_avg()
    up = uptime_seconds()
    net = net_rates()
    temp = temperature_c()

    base_paths = []
    # project dir
    base_paths.append(str(Path(".").resolve()))
    # termux home
    base_paths.append(str(Path.home()))
    # shared storage if mounted
    if Path("/storage/emulated/0").exists():
        base_paths.append("/storage/emulated/0")

    disks = disk_info(base_paths)

    return {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "uptime_s": up,
        "cpu_percent": cpu,
        "loadavg": la,
        "mem": mem,
        "disks": disks,
        "net": net,
        "temperature_c": temp,
        "top": top_processes(8),
        "python": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
    }
