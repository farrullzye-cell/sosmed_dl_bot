import os
import signal
import subprocess
from pathlib import Path
from datetime import datetime
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
TASK_DIR = LOG_DIR / "tasks"
RUN_DIR = BASE_DIR / "run"
BOT_LOG = LOG_DIR / "bot.log"
BOT_PID = RUN_DIR / "bot.pid"

LOG_DIR.mkdir(exist_ok=True)
TASK_DIR.mkdir(parents=True, exist_ok=True)
RUN_DIR.mkdir(exist_ok=True)

control_bp = Blueprint("control", __name__, url_prefix="/control")

# Paket yang boleh di-install dari panel (EDIT sesuai kebutuhan)
ALLOWED_PKG_INSTALL = {
    "ffmpeg", "git", "sqlite", "openssh", "openssl", "python", "curl", "wget", "chromium"
}

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if not session.get("auth"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrap

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def read_pid(pidfile: Path):
    try:
        return int(pidfile.read_text().strip())
    except Exception:
        return None

def pid_running(pid: int) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False

def write_pid(pidfile: Path, pid: int):
    pidfile.write_text(str(pid), encoding="utf-8")

def remove_pid(pidfile: Path):
    try:
        pidfile.unlink()
    except Exception:
        pass

def tail(path: Path, n=120):
    if not path.exists():
        return ""
    try:
        data = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return "\n".join(data[-n:])
    except Exception:
        return ""

def start_bot():
    pid = read_pid(BOT_PID)
    if pid and pid_running(pid):
        return f"[{now()}] Bot sudah jalan. PID={pid}"

    # start bot detached
    with open(BOT_LOG, "a", encoding="utf-8") as logf:
        p = subprocess.Popen(
            ["python", "-u", "bot.py"],
            cwd=str(BASE_DIR),
            stdout=logf,
            stderr=logf,
            start_new_session=True,
        )
    write_pid(BOT_PID, p.pid)
    return f"[{now()}] Bot start OK. PID={p.pid}"

def stop_bot():
    pid = read_pid(BOT_PID)
    if not pid:
        # fallback: coba pkill by pattern
        subprocess.run(["pkill", "-f", "python.*bot.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"[{now()}] Stop bot (fallback pkill)."

    if not pid_running(pid):
        remove_pid(BOT_PID)
        return f"[{now()}] PID file ada tapi proses sudah mati. Dibersihkan."

    try:
        os.kill(pid, signal.SIGTERM)
    except Exception:
        pass

    remove_pid(BOT_PID)
    return f"[{now()}] Stop bot OK (SIGTERM). PID={pid}"

def bot_status():
    pid = read_pid(BOT_PID)
    if pid and pid_running(pid):
        return f"RUNNING (PID {pid})"
    return "STOPPED"

def run_task(name: str, cmd: list[str]):
    task_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + name
    log_path = TASK_DIR / f"{task_id}.log"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"[{now()}] START {task_id}\nCMD: {' '.join(cmd)}\n\n")

    # Jalankan task di background, output ke log file
    with open(log_path, "a", encoding="utf-8") as f:
        subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            stdout=f,
            stderr=f,
            start_new_session=True,
        )
    return task_id

def list_task_logs(limit=30):
    files = sorted(TASK_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]

@control_bp.get("/")
@login_required
def home():
    info = {
        "bot_status": bot_status(),
        "bot_pid": read_pid(BOT_PID),
        "bot_log_tail": tail(BOT_LOG, 120),
        "tasks": [p.name for p in list_task_logs(25)],
    }
    return render_template("control.html", info=info, allowed=sorted(ALLOWED_PKG_INSTALL))

@control_bp.post("/bot/start")
@login_required
def bot_start_route():
    msg = start_bot()
    flash(msg)
    return redirect(url_for("control.home"))

@control_bp.post("/bot/stop")
@login_required
def bot_stop_route():
    msg = stop_bot()
    flash(msg)
    return redirect(url_for("control.home"))

@control_bp.post("/bot/restart")
@login_required
def bot_restart_route():
    stop_bot()
    msg = start_bot()
    flash(f"[{now()}] Restart bot OK. {msg}")
    return redirect(url_for("control.home"))

@control_bp.post("/task/git_pull")
@login_required
def task_git_pull():
    tid = run_task("gitpull", ["sh", "-lc", "git pull"])
    flash(f"Task started: {tid}")
    return redirect(url_for("control.home"))

@control_bp.post("/task/pip_requirements")
@login_required
def task_pip_req():
    tid = run_task("pipreq", ["sh", "-lc", "python -m pip install -r requirements.txt"])
    flash(f"Task started: {tid}")
    return redirect(url_for("control.home"))

@control_bp.post("/task/update_ytdlp")
@login_required
def task_ytdlp():
    tid = run_task("ytdlp", ["sh", "-lc", "python -m pip install -U yt-dlp"])
    flash(f"Task started: {tid}")
    return redirect(url_for("control.home"))

@control_bp.post("/task/pkg_update_upgrade")
@login_required
def task_pkg_update():
    tid = run_task("pkgup", ["sh", "-lc", "pkg update -y && pkg upgrade -y"])
    flash(f"Task started: {tid}")
    return redirect(url_for("control.home"))

@control_bp.post("/task/pkg_install")
@login_required
def task_pkg_install():
    pkgname = (request.form.get("pkg") or "").strip()
    if pkgname not in ALLOWED_PKG_INSTALL:
        flash("Paket tidak diizinkan (allowlist).")
        return redirect(url_for("control.home"))
    tid = run_task("pkginst", ["sh", "-lc", f"pkg install -y {pkgname}"])
    flash(f"Task started: {tid}")
    return redirect(url_for("control.home"))

@control_bp.get("/task/<name>")
@login_required
def task_view(name):
    p = (TASK_DIR / name)
    if not p.exists():
        flash("Task log tidak ditemukan.")
        return redirect(url_for("control.home"))
    content = tail(p, 220)
    return render_template("control_task.html", name=name, content=content)
