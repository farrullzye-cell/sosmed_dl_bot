import os
from pathlib import Path
from functools import wraps

import requests
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.utils import secure_filename

from utils import load_env
from shop_db import ShopDB

load_env()

DB_PATH = os.environ.get("DB_PATH", "bot.db")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
SHOP_STORAGE_DIR = os.environ.get("SHOP_STORAGE_DIR", "shop_storage")

shop = ShopDB(DB_PATH)

shop_bp = Blueprint("shop", __name__, url_prefix="/shop")

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if not session.get("auth"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrap

def tg_api(method: str, *, data=None):
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN kosong di .env")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    r = requests.post(url, data=data or {}, timeout=60)
    j = r.json()
    if not j.get("ok"):
        raise RuntimeError(str(j))
    return j["result"]

def money_idr(x: int) -> str:
    try:
        x = int(x)
    except Exception:
        x = 0
    return f"Rp{x:,}".replace(",", ".")

@shop_bp.get("/")
@login_required
def home():
    waiting = len(shop.list_orders(status="WAITING_PROOF", limit=2000))
    verifying = len(shop.list_orders(status="VERIFYING", limit=2000))
    paid = len(shop.list_orders(status="PAID", limit=2000))
    delivered = len(shop.list_orders(status="DELIVERED", limit=2000))
    listings = len(shop.list_listings(active_only=False))
    return render_template("shop_home.html",
                           waiting=waiting, verifying=verifying, paid=paid, delivered=delivered, listings=listings)

@shop_bp.get("/settings")
@login_required
def settings():
    pay = shop.get_setting("payment_instructions", "")
    return render_template("shop_settings.html", payment_instructions=pay)

@shop_bp.post("/settings")
@login_required
def settings_post():
    pay = request.form.get("payment_instructions", "") or ""
    shop.set_setting("payment_instructions", pay)
    flash("Shop settings tersimpan.")
    return redirect(url_for("shop.settings"))

@shop_bp.get("/listings")
@login_required
def listings():
    rows = shop.list_listings(active_only=False)
    return render_template("shop_listings.html", rows=rows)

@shop_bp.post("/listings/create")
@login_required
def listings_create():
    game = (request.form.get("game","") or "").strip()
    title = (request.form.get("title","") or "").strip()
    region = (request.form.get("region","") or "").strip()
    rank = (request.form.get("rank","") or "").strip()
    description = (request.form.get("description","") or "").strip()
    price_int = int(request.form.get("price_int","0") or 0)
    preview_type = request.form.get("preview_type","text")

    if not game or not title:
        flash("Game & Title wajib.")
        return redirect(url_for("shop.listings"))

    shop.create_listing(game, title, region, rank, description, price_int, preview_type)
    flash("Listing dibuat.")
    return redirect(url_for("shop.listings"))

@shop_bp.get("/listings/<int:lid>")
@login_required
def listing_edit(lid):
    l = shop.get_listing(lid)
    if not l:
        flash("Listing tidak ditemukan.")
        return redirect(url_for("shop.listings"))
    a, r, s = shop.stock_counts(lid)
    stocks = shop.list_stocks(lid, limit=300)
    return render_template("shop_listing_edit.html", l=l, a=a, r=r, s=s, stocks=stocks)

@shop_bp.post("/listings/<int:lid>/update")
@login_required
def listing_update(lid):
    game = (request.form.get("game","") or "").strip()
    title = (request.form.get("title","") or "").strip()
    region = (request.form.get("region","") or "").strip()
    rank = (request.form.get("rank","") or "").strip()
    description = (request.form.get("description","") or "").strip()
    price_int = int(request.form.get("price_int","0") or 0)
    preview_type = request.form.get("preview_type","text")
    is_active = 1 if request.form.get("is_active") == "on" else 0

    shop.update_listing(lid, game, title, region, rank, description, price_int, preview_type, is_active)
    flash("Listing diupdate.")
    return redirect(url_for("shop.listing_edit", lid=lid))

@shop_bp.post("/listings/<int:lid>/upload_preview")
@login_required
def listing_upload_preview(lid):
    f = request.files.get("preview")
    if not f or not f.filename:
        flash("Pilih file preview.")
        return redirect(url_for("shop.listing_edit", lid=lid))

    os.makedirs(Path(SHOP_STORAGE_DIR) / "previews", exist_ok=True)
    fn = secure_filename(f.filename)
    path = Path(SHOP_STORAGE_DIR) / "previews" / f"listing{lid}_{fn}"
    f.save(str(path))

    shop.update_listing_preview(lid, str(path))
    flash("Preview diupload.")
    return redirect(url_for("shop.listing_edit", lid=lid))

@shop_bp.post("/listings/<int:lid>/add_stock")
@login_required
def listing_add_stock(lid):
    raw = (request.form.get("stocks","") or "").strip()
    creds = [line.strip() for line in raw.splitlines() if line.strip()]
    shop.add_stock_bulk(lid, creds)
    flash(f"Stock ditambahkan: {len(creds)}")
    return redirect(url_for("shop.listing_edit", lid=lid))

@shop_bp.post("/listings/<int:lid>/delete")
@login_required
def listing_delete(lid):
    shop.delete_listing(lid)
    flash("Listing dihapus.")
    return redirect(url_for("shop.listings"))

@shop_bp.get("/orders")
@login_required
def orders():
    status = request.args.get("status","").strip() or None
    rows = shop.list_orders(status=status, limit=300)
    return render_template("shop_orders.html", rows=rows, status=status or "")

@shop_bp.get("/orders/<order_code>")
@login_required
def order_detail(order_code):
    o = shop.get_order(order_code)
    if not o:
        flash("Order tidak ditemukan.")
        return redirect(url_for("shop.orders"))
    return render_template("shop_order_detail.html", o=o, money_idr=money_idr)

@shop_bp.get("/orders/<order_code>/proof")
@login_required
def order_proof(order_code):
    o = shop.get_order(order_code)
    if not o or not o["proof_file_id"]:
        flash("Proof tidak ada.")
        return redirect(url_for("shop.order_detail", order_code=order_code))

    try:
        f = tg_api("getFile", data={"file_id": o["proof_file_id"]})
        file_path = f["file_path"]
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        r = requests.get(file_url, timeout=60)
        r.raise_for_status()

        tmp = Path("tmp_shop_proof")
        tmp.mkdir(exist_ok=True)
        out = tmp / (file_path.split("/")[-1])
        out.write_bytes(r.content)
        return send_file(str(out), as_attachment=False)
    except Exception as e:
        flash(f"Gagal ambil proof: {e}")
        return redirect(url_for("shop.order_detail", order_code=order_code))

@shop_bp.post("/orders/<order_code>/approve")
@login_required
def order_approve(order_code):
    o = shop.get_order(order_code)
    if not o:
        flash("Order tidak ditemukan.")
        return redirect(url_for("shop.orders"))

    # PAID
    shop.mark_paid(int(o["id"]))

    # reserve stock
    stock_id = shop.reserve_one_stock(int(o["listing_id"]), int(o["id"]))
    if not stock_id:
        flash("Order PAID, tapi stok habis. Tambah stock dulu.")
        return redirect(url_for("shop.order_detail", order_code=order_code))

    claim = shop.create_claim(int(o["id"]), int(o["user_id"]), int(o["listing_id"]), int(stock_id))

    # kirim claim ke user
    try:
        tg_api("sendMessage", data={
            "chat_id": str(o["user_id"]),
            "text": (
                "✅ PEMBAYARAN DITERIMA\n"
                f"Order: {o['order_code']}\n"
                f"Listing: {o['listing_game']} - {o['listing_title']}\n"
                f"Harga: {money_idr(o['amount_int'])}\n\n"
                f"🎫 Kode Claim: {claim}\n"
                "Ambil akun dengan:\n"
                f"/claim {claim}\n\n"
                "⚠️ Setelah login, segera ganti password."
            )
        })
        shop.log_msg(int(o["user_id"]), "out", f"[SYSTEM] approve {o['order_code']} claim={claim}", None)
        flash(f"Approved. Claim: {claim} (stock {stock_id})")
    except Exception as e:
        flash(f"Approve OK, tapi gagal kirim pesan: {e}")

    return redirect(url_for("shop.order_detail", order_code=order_code))

@shop_bp.post("/orders/<order_code>/reject")
@login_required
def order_reject(order_code):
    o = shop.get_order(order_code)
    if not o:
        flash("Order tidak ditemukan.")
        return redirect(url_for("shop.orders"))

    reason = (request.form.get("reason","") or "").strip()
    shop.reject_order(int(o["id"]))

    try:
        tg_api("sendMessage", data={
            "chat_id": str(o["user_id"]),
            "text": f"❌ Order {order_code} ditolak.\nAlasan: {reason or '-'}"
        })
        shop.log_msg(int(o["user_id"]), "out", f"[SYSTEM] reject {order_code} reason={reason}", None)
    except Exception:
        pass

    flash("Order rejected.")
    return redirect(url_for("shop.order_detail", order_code=order_code))

@shop_bp.get("/claims")
@login_required
def claims():
    rows = shop.list_claims(limit=300)
    return render_template("shop_claims.html", rows=rows)

@shop_bp.post("/claims/<code>/revoke")
@login_required
def claim_revoke(code):
    shop.revoke_claim(code.upper(), True)
    flash("Claim revoked.")
    return redirect(url_for("shop.claims"))

@shop_bp.post("/claims/<code>/unrevoke")
@login_required
def claim_unrevoke(code):
    shop.revoke_claim(code.upper(), False)
    flash("Claim unrevoked.")
    return redirect(url_for("shop.claims"))

@shop_bp.get("/deliveries")
@login_required
def deliveries():
    user_id = request.args.get("user_id","").strip() or None
    rows = shop.list_deliveries(user_id=user_id, limit=300)
    return render_template("shop_deliveries.html", rows=rows, user_id=user_id or "")

@shop_bp.get("/chat/<int:user_id>")
@login_required
def chat(user_id):
    msgs = list(reversed(shop.list_msgs(user_id, limit=200)))
    return render_template("shop_chat.html", user_id=user_id, msgs=msgs)

@shop_bp.post("/chat/<int:user_id>/send")
@login_required
def chat_send(user_id):
    text = (request.form.get("text","") or "").strip()
    if not text:
        return redirect(url_for("shop.chat", user_id=user_id))

    try:
        tg_api("sendMessage", data={"chat_id": str(user_id), "text": "👨‍💻 Admin:\n" + text})
        shop.log_msg(user_id, "out", text, None)
        flash("Terkirim.")
    except Exception as e:
        flash(f"Gagal kirim: {e}")

    return redirect(url_for("shop.chat", user_id=user_id))
