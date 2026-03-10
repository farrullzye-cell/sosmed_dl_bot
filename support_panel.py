import os
from functools import wraps

import requests
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from utils import load_env
from support_db import SupportDB

load_env()
DB_PATH = os.environ.get("DB_PATH", "bot.db")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

supportdb = SupportDB(DB_PATH)
support_bp = Blueprint("support", __name__, url_prefix="/support")

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if not session.get("auth"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrap

def tg_send_message(chat_id: int, text: str):
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN kosong di .env")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, data={"chat_id": str(chat_id), "text": text}, timeout=60)
    j = r.json()
    if not j.get("ok"):
        raise RuntimeError(str(j))
    return j["result"]

@support_bp.get("/")
@login_required
def threads():
    rows = supportdb.list_threads(limit=300)
    return render_template("support_threads.html", rows=rows)

@support_bp.get("/chat/<int:user_id>")
@login_required
def chat(user_id):
    msgs = supportdb.list_msgs(user_id, limit=400)
    return render_template("support_chat.html", user_id=user_id, msgs=msgs)

@support_bp.post("/chat/<int:user_id>/send")
@login_required
def chat_send(user_id):
    text = (request.form.get("text","") or "").strip()
    if not text:
        return redirect(url_for("support.chat", user_id=user_id))
    try:
        tg_send_message(user_id, "👨‍💻 Admin:\n" + text)
        supportdb.log_msg(user_id, "out", text, None)
        flash("Terkirim.")
    except Exception as e:
        flash(f"Gagal kirim: {e}")
    return redirect(url_for("support.chat", user_id=user_id))
