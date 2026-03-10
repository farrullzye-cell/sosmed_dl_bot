from flask import Blueprint, render_template, jsonify
from functools import wraps
from flask import session, redirect, url_for

from monitor_utils import stats

monitor_bp = Blueprint("monitor", __name__, url_prefix="/monitor")

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if not session.get("auth"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrap

@monitor_bp.get("/")
@login_required
def page():
    return render_template("monitor.html")

@monitor_bp.get("/json")
@login_required
def json_stats():
    return jsonify(stats())
