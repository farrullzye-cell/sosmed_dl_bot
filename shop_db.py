import sqlite3
from datetime import datetime, timezone

def utcnow_iso():
    return datetime.now(timezone.utc).isoformat()

def gen_order_code():
    import secrets, string
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    rnd = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"INV-{stamp}-{rnd}"

def gen_claim_code():
    import secrets, string
    rnd = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))
    chunks = [rnd[i:i+4] for i in range(0, len(rnd), 4)]
    return "CLM-" + "-".join(chunks)

class ShopDB:
    """
    Shop akun game (listing + stock + order + claim + chat) di SQLite yang sama.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init()

    def conn(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA synchronous=NORMAL;")
        return con

    def _init(self):
        with self.conn() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS shop_settings(
              key TEXT PRIMARY KEY,
              value TEXT
            );

            CREATE TABLE IF NOT EXISTS shop_listings(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              game TEXT NOT NULL,
              title TEXT NOT NULL,
              region TEXT,
              rank TEXT,
              description TEXT,
              price_int INTEGER NOT NULL DEFAULT 0,
              preview_type TEXT NOT NULL DEFAULT 'text',
              preview_path TEXT,
              is_active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS shop_stocks(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              listing_id INTEGER NOT NULL,
              creds_text TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'available', -- available|reserved|sold
              reserved_order_id INTEGER,
              sold_order_id INTEGER,
              created_at TEXT NOT NULL,
              sold_at TEXT
            );

            CREATE TABLE IF NOT EXISTS shop_orders(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              order_code TEXT UNIQUE NOT NULL,
              user_id INTEGER NOT NULL,
              username TEXT,
              first_name TEXT,
              listing_id INTEGER NOT NULL,
              amount_int INTEGER NOT NULL,
              status TEXT NOT NULL, -- WAITING_PROOF|VERIFYING|PAID|DELIVERED|REJECTED
              proof_file_id TEXT,
              proof_kind TEXT,
              proof_message_id INTEGER,
              created_at TEXT NOT NULL,
              paid_at TEXT,
              delivered_at TEXT
            );

            CREATE TABLE IF NOT EXISTS shop_claims(
              code TEXT PRIMARY KEY,
              order_id INTEGER NOT NULL,
              user_id INTEGER NOT NULL,
              listing_id INTEGER NOT NULL,
              stock_id INTEGER,
              status TEXT NOT NULL, -- UNUSED|USED|REVOKED
              created_at TEXT NOT NULL,
              used_at TEXT
            );

            CREATE TABLE IF NOT EXISTS shop_messages(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              direction TEXT NOT NULL, -- in|out
              text TEXT,
              tg_message_id INTEGER,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS shop_deliveries(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              order_id INTEGER NOT NULL,
              user_id INTEGER NOT NULL,
              listing_id INTEGER NOT NULL,
              claim_code TEXT,
              stock_id INTEGER,
              status TEXT NOT NULL, -- sent|error
              error TEXT,
              created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_shop_stock_listing ON shop_stocks(listing_id, status);
            CREATE INDEX IF NOT EXISTS idx_shop_order_user ON shop_orders(user_id);
            """)

        self.seed_setting("payment_instructions",
            "Instruksi pembayaran:\n- BCA: xxxx a.n. Nama\n- DANA: 08xx\nSetelah bayar, kirim bukti (foto/pdf)."
        )

    # ===== settings =====
    def seed_setting(self, key: str, value: str):
        with self.conn() as con:
            row = con.execute("SELECT 1 FROM shop_settings WHERE key=?", (key,)).fetchone()
            if not row:
                con.execute("INSERT INTO shop_settings(key,value) VALUES(?,?)", (key, value))

    def get_setting(self, key: str, default=""):
        with self.conn() as con:
            row = con.execute("SELECT value FROM shop_settings WHERE key=?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        with self.conn() as con:
            con.execute("""
            INSERT INTO shop_settings(key,value) VALUES(?,?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (key, value or ""))

    # ===== listings =====
    def create_listing(self, game, title, region, rank, description, price_int, preview_type="text"):
        now = utcnow_iso()
        with self.conn() as con:
            con.execute("""
            INSERT INTO shop_listings(game,title,region,rank,description,price_int,preview_type,is_active,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """, (game, title, region, rank, description, int(price_int), preview_type, 1, now, now))

    def list_listings(self, active_only=True):
        with self.conn() as con:
            if active_only:
                return con.execute("SELECT * FROM shop_listings WHERE is_active=1 ORDER BY id DESC").fetchall()
            return con.execute("SELECT * FROM shop_listings ORDER BY id DESC").fetchall()

    def get_listing(self, listing_id: int):
        with self.conn() as con:
            return con.execute("SELECT * FROM shop_listings WHERE id=?", (int(listing_id),)).fetchone()

    def update_listing(self, listing_id: int, game, title, region, rank, description, price_int, preview_type, is_active):
        now = utcnow_iso()
        with self.conn() as con:
            con.execute("""
            UPDATE shop_listings
            SET game=?, title=?, region=?, rank=?, description=?, price_int=?, preview_type=?, is_active=?, updated_at=?
            WHERE id=?
            """, (game, title, region, rank, description, int(price_int), preview_type, int(is_active), now, int(listing_id)))

    def update_listing_preview(self, listing_id: int, preview_path: str):
        now = utcnow_iso()
        with self.conn() as con:
            con.execute("UPDATE shop_listings SET preview_path=?, updated_at=? WHERE id=?",
                        (preview_path, now, int(listing_id)))

    def delete_listing(self, listing_id: int):
        with self.conn() as con:
            con.execute("DELETE FROM shop_listings WHERE id=?", (int(listing_id),))
            con.execute("DELETE FROM shop_stocks WHERE listing_id=?", (int(listing_id),))

    def stock_counts(self, listing_id: int):
        with self.conn() as con:
            a = con.execute("SELECT COUNT(*) c FROM shop_stocks WHERE listing_id=? AND status='available'", (int(listing_id),)).fetchone()["c"]
            r = con.execute("SELECT COUNT(*) c FROM shop_stocks WHERE listing_id=? AND status='reserved'", (int(listing_id),)).fetchone()["c"]
            s = con.execute("SELECT COUNT(*) c FROM shop_stocks WHERE listing_id=? AND status='sold'", (int(listing_id),)).fetchone()["c"]
        return int(a), int(r), int(s)

    # ===== stocks =====
    def add_stock_bulk(self, listing_id: int, creds_lines: list[str]):
        now = utcnow_iso()
        with self.conn() as con:
            for c in creds_lines:
                c = (c or "").strip()
                if not c:
                    continue
                con.execute("""
                INSERT INTO shop_stocks(listing_id,creds_text,status,created_at)
                VALUES(?,?,'available',?)
                """, (int(listing_id), c, now))

    def list_stocks(self, listing_id: int, limit=300):
        with self.conn() as con:
            return con.execute("""
            SELECT * FROM shop_stocks WHERE listing_id=?
            ORDER BY id DESC LIMIT ?
            """, (int(listing_id), int(limit))).fetchall()

    def reserve_one_stock(self, listing_id: int, order_id: int):
        with self.conn() as con:
            row = con.execute("""
              SELECT id FROM shop_stocks
              WHERE listing_id=? AND status='available'
              ORDER BY id ASC LIMIT 1
            """, (int(listing_id),)).fetchone()
            if not row:
                return None
            sid = int(row["id"])
            con.execute("""
              UPDATE shop_stocks
              SET status='reserved', reserved_order_id=?
              WHERE id=?
            """, (int(order_id), sid))
            return sid

    def get_stock(self, stock_id: int):
        with self.conn() as con:
            return con.execute("SELECT * FROM shop_stocks WHERE id=?", (int(stock_id),)).fetchone()

    def mark_stock_sold(self, stock_id: int, order_id: int):
        now = utcnow_iso()
        with self.conn() as con:
            con.execute("""
            UPDATE shop_stocks
            SET status='sold', sold_order_id=?, sold_at=?
            WHERE id=?
            """, (int(order_id), now, int(stock_id)))

    # ===== orders =====
    def create_order(self, user_id: int, username: str, first_name: str, listing_id: int, amount_int: int):
        code = gen_order_code()
        now = utcnow_iso()
        with self.conn() as con:
            con.execute("""
            INSERT INTO shop_orders(order_code,user_id,username,first_name,listing_id,amount_int,status,created_at)
            VALUES(?,?,?,?,?,?, 'WAITING_PROOF', ?)
            """, (code, int(user_id), username, first_name, int(listing_id), int(amount_int), now))
            oid = con.execute("SELECT last_insert_rowid() id").fetchone()["id"]
        return int(oid), code

    def get_order(self, order_code: str):
        with self.conn() as con:
            return con.execute("""
            SELECT o.*, l.game listing_game, l.title listing_title
            FROM shop_orders o
            LEFT JOIN shop_listings l ON l.id=o.listing_id
            WHERE o.order_code=?
            """, (order_code,)).fetchone()

    def list_orders(self, status=None, limit=300):
        q = """
        SELECT o.*, l.game listing_game, l.title listing_title
        FROM shop_orders o
        LEFT JOIN shop_listings l ON l.id=o.listing_id
        """
        args = []
        if status:
            q += " WHERE o.status=?"
            args.append(status)
        q += " ORDER BY o.id DESC LIMIT ?"
        args.append(int(limit))
        with self.conn() as con:
            return con.execute(q, tuple(args)).fetchall()

    def set_order_proof(self, order_id: int, file_id: str, kind: str, message_id: int):
        with self.conn() as con:
            con.execute("""
            UPDATE shop_orders
            SET proof_file_id=?, proof_kind=?, proof_message_id=?, status='VERIFYING'
            WHERE id=?
            """, (file_id, kind, int(message_id), int(order_id)))

    def mark_paid(self, order_id: int):
        now = utcnow_iso()
        with self.conn() as con:
            con.execute("UPDATE shop_orders SET status='PAID', paid_at=? WHERE id=?", (now, int(order_id)))

    def mark_delivered(self, order_id: int):
        now = utcnow_iso()
        with self.conn() as con:
            con.execute("UPDATE shop_orders SET status='DELIVERED', delivered_at=? WHERE id=?", (now, int(order_id)))

    def reject_order(self, order_id: int):
        with self.conn() as con:
            con.execute("UPDATE shop_orders SET status='REJECTED' WHERE id=?", (int(order_id),))

    # ===== claims =====
    def create_claim(self, order_id: int, user_id: int, listing_id: int, stock_id: int):
        code = gen_claim_code()
        now = utcnow_iso()
        with self.conn() as con:
            con.execute("""
            INSERT INTO shop_claims(code,order_id,user_id,listing_id,stock_id,status,created_at)
            VALUES(?,?,?,?,?,'UNUSED',?)
            """, (code, int(order_id), int(user_id), int(listing_id), int(stock_id), now))
        return code

    def get_claim(self, code: str):
        with self.conn() as con:
            return con.execute("""
            SELECT c.*, o.order_code, o.status order_status, l.game listing_game, l.title listing_title
            FROM shop_claims c
            LEFT JOIN shop_orders o ON o.id=c.order_id
            LEFT JOIN shop_listings l ON l.id=c.listing_id
            WHERE c.code=?
            """, (code,)).fetchone()

    def mark_claim_used(self, code: str):
        now = utcnow_iso()
        with self.conn() as con:
            con.execute("UPDATE shop_claims SET status='USED', used_at=? WHERE code=?", (now, code))

    def revoke_claim(self, code: str, revoked: bool):
        with self.conn() as con:
            con.execute("UPDATE shop_claims SET status=? WHERE code=?", ("REVOKED" if revoked else "UNUSED", code))

    def list_claims(self, limit=300):
        with self.conn() as con:
            return con.execute("""
            SELECT c.*, l.game listing_game, l.title listing_title
            FROM shop_claims c
            LEFT JOIN shop_listings l ON l.id=c.listing_id
            ORDER BY c.created_at DESC LIMIT ?
            """, (int(limit),)).fetchall()

    # ===== deliveries & chat log =====
    def log_delivery(self, order_id, user_id, listing_id, claim_code, stock_id, status, error=None):
        with self.conn() as con:
            con.execute("""
            INSERT INTO shop_deliveries(order_id,user_id,listing_id,claim_code,stock_id,status,error,created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """, (int(order_id), int(user_id), int(listing_id), claim_code, int(stock_id), status, error, utcnow_iso()))

    def list_deliveries(self, user_id=None, limit=300):
        q = """
        SELECT d.*, l.game listing_game, l.title listing_title
        FROM shop_deliveries d
        LEFT JOIN shop_listings l ON l.id=d.listing_id
        """
        args = []
        if user_id:
            q += " WHERE d.user_id=?"
            args.append(int(user_id))
        q += " ORDER BY d.id DESC LIMIT ?"
        args.append(int(limit))
        with self.conn() as con:
            return con.execute(q, tuple(args)).fetchall()

    def log_msg(self, user_id, direction, text, tg_message_id=None):
        with self.conn() as con:
            con.execute("""
            INSERT INTO shop_messages(user_id,direction,text,tg_message_id,created_at)
            VALUES(?,?,?,?,?)
            """, (int(user_id), direction, text or "", tg_message_id, utcnow_iso()))

    def list_msgs(self, user_id, limit=200):
        with self.conn() as con:
            return con.execute("""
            SELECT * FROM shop_messages WHERE user_id=?
            ORDER BY id DESC LIMIT ?
            """, (int(user_id), int(limit))).fetchall()
