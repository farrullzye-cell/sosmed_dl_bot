import os
import sqlite3
from datetime import datetime, timezone, date

def utcnow_iso():
    return datetime.now(timezone.utc).isoformat()

def today_iso():
    return date.today().isoformat()

class DB:
    def __init__(self, path: str):
        self.path = path
        self._init()

    def conn(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA synchronous=NORMAL;")
        return con

    def _init(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with self.conn() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                is_banned INTEGER NOT NULL DEFAULT 0,
                premium_until TEXT,
                created_at TEXT NOT NULL,
                last_seen TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS daily_usage (
                user_id INTEGER NOT NULL,
                day TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, day)
            );

            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                platform TEXT,
                title TEXT,
                file_path TEXT,
                file_size INTEGER,
                status TEXT NOT NULL,
                error TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS admin_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_user_id INTEGER,
                data TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """)
        self._migrate()

    def _migrate(self):
        with self.conn() as con:
            cols = [r["name"] for r in con.execute("PRAGMA table_info(users)").fetchall()]
            if "daily_limit_override" not in cols:
                con.execute("ALTER TABLE users ADD COLUMN daily_limit_override INTEGER;")
            if "max_mb_override" not in cols:
                con.execute("ALTER TABLE users ADD COLUMN max_mb_override INTEGER;")
            if "note" not in cols:
                con.execute("ALTER TABLE users ADD COLUMN note TEXT;")

    # ===== Settings =====
    def get_setting(self, key: str, default=None):
        with self.conn() as con:
            row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value):
        if value is None:
            value = ""
        with self.conn() as con:
            con.execute("""
                INSERT INTO settings(key,value) VALUES(?,?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (key, str(value)))

    def all_settings(self):
        with self.conn() as con:
            rows = con.execute("SELECT key,value FROM settings ORDER BY key").fetchall()
        return {r["key"]: r["value"] for r in rows}

    def seed_settings(self, defaults: dict):
        """Set default jika key belum ada."""
        with self.conn() as con:
            for k, v in defaults.items():
                row = con.execute("SELECT 1 FROM settings WHERE key=?", (k,)).fetchone()
                if not row:
                    con.execute("INSERT INTO settings(key,value) VALUES(?,?)", (k, str(v)))

    # ===== Users =====
    def upsert_user(self, user_id: int, username: str, first_name: str):
        now = utcnow_iso()
        with self.conn() as con:
            row = con.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)).fetchone()
            if row:
                con.execute("""
                    UPDATE users
                    SET username=?, first_name=?, last_seen=?
                    WHERE user_id=?
                """, (username, first_name, now, user_id))
            else:
                con.execute("""
                    INSERT INTO users (user_id, username, first_name, is_banned, premium_until, created_at, last_seen)
                    VALUES (?, ?, ?, 0, NULL, ?, ?)
                """, (user_id, username, first_name, now, now))

    def get_user(self, user_id: int):
        with self.conn() as con:
            return con.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

    def delete_user(self, user_id: int):
        with self.conn() as con:
            con.execute("DELETE FROM daily_usage WHERE user_id=?", (user_id,))
            con.execute("DELETE FROM downloads WHERE user_id=?", (user_id,))
            con.execute("DELETE FROM users WHERE user_id=?", (user_id,))

    def is_banned(self, user_id: int) -> bool:
        u = self.get_user(user_id)
        return bool(u and u["is_banned"] == 1)

    def set_ban(self, user_id: int, banned: bool):
        with self.conn() as con:
            con.execute("UPDATE users SET is_banned=? WHERE user_id=?", (1 if banned else 0, user_id))

    # ===== Premium =====
    def set_premium_days(self, user_id: int, days: int):
        from datetime import timedelta
        base = datetime.now(timezone.utc)
        u = self.get_user(user_id)
        if u and u["premium_until"]:
            try:
                current_until = datetime.fromisoformat(u["premium_until"])
                if current_until > base:
                    base = current_until
            except Exception:
                pass
        new_until = base + timedelta(days=days)
        with self.conn() as con:
            con.execute("UPDATE users SET premium_until=? WHERE user_id=?", (new_until.isoformat(), user_id))

    def clear_premium(self, user_id: int):
        with self.conn() as con:
            con.execute("UPDATE users SET premium_until=NULL WHERE user_id=?", (user_id,))

    def is_premium(self, user_id: int) -> bool:
        u = self.get_user(user_id)
        if not u or not u["premium_until"]:
            return False
        try:
            until = datetime.fromisoformat(u["premium_until"])
            return until > datetime.now(timezone.utc)
        except Exception:
            return False

    # ===== Limits override per user =====
    def set_limits(self, user_id: int, daily_limit_override=None, max_mb_override=None):
        with self.conn() as con:
            con.execute("""
                UPDATE users
                SET daily_limit_override = COALESCE(?, daily_limit_override),
                    max_mb_override = COALESCE(?, max_mb_override)
                WHERE user_id=?
            """, (daily_limit_override, max_mb_override, user_id))

    def clear_limits(self, user_id: int):
        with self.conn() as con:
            con.execute("""
                UPDATE users
                SET daily_limit_override=NULL, max_mb_override=NULL
                WHERE user_id=?
            """, (user_id,))

    def set_note(self, user_id: int, note: str):
        with self.conn() as con:
            con.execute("UPDATE users SET note=? WHERE user_id=?", (note, user_id))

    # ===== Daily usage =====
    def inc_daily(self, user_id: int) -> int:
        d = today_iso()
        with self.conn() as con:
            row = con.execute("SELECT count FROM daily_usage WHERE user_id=? AND day=?", (user_id, d)).fetchone()
            if row:
                newc = int(row["count"]) + 1
                con.execute("UPDATE daily_usage SET count=? WHERE user_id=? AND day=?", (newc, user_id, d))
                return newc
            else:
                con.execute("INSERT INTO daily_usage (user_id, day, count) VALUES (?, ?, 1)", (user_id, d))
                return 1

    def get_daily(self, user_id: int) -> int:
        d = today_iso()
        with self.conn() as con:
            row = con.execute("SELECT count FROM daily_usage WHERE user_id=? AND day=?", (user_id, d)).fetchone()
            return int(row["count"]) if row else 0

    def reset_daily_today(self, user_id: int):
        d = today_iso()
        with self.conn() as con:
            con.execute("DELETE FROM daily_usage WHERE user_id=? AND day=?", (user_id, d))

    # ===== Downloads =====
    def log_download(self, user_id: int, url: str, platform: str, status: str, title=None, file_path=None, file_size=None, error=None):
        with self.conn() as con:
            con.execute("""
                INSERT INTO downloads (user_id, url, platform, title, file_path, file_size, status, error, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, url, platform, title, file_path, file_size, status, error, utcnow_iso()))

    def list_downloads(self, limit=200, user_id=None, status=None, platform=None):
        q = "SELECT d.*, u.username FROM downloads d LEFT JOIN users u ON u.user_id=d.user_id WHERE 1=1"
        args = []
        if user_id:
            q += " AND d.user_id=?"
            args.append(int(user_id))
        if status:
            q += " AND d.status=?"
            args.append(status)
        if platform:
            q += " AND d.platform=?"
            args.append(platform)
        q += " ORDER BY d.id DESC LIMIT ?"
        args.append(int(limit))
        with self.conn() as con:
            return con.execute(q, tuple(args)).fetchall()

    # ===== Admin actions =====
    def log_admin(self, admin_id: int, action: str, target_user_id=None, data=None):
        with self.conn() as con:
            con.execute("""
                INSERT INTO admin_actions (admin_id, action, target_user_id, data, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (admin_id, action, target_user_id, data, utcnow_iso()))

    def list_admin_actions(self, limit=200):
        with self.conn() as con:
            return con.execute("SELECT * FROM admin_actions ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()

    # ===== Web stats/users =====
    def stats(self):
        with self.conn() as con:
            total_users = con.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
            banned_users = con.execute("SELECT COUNT(*) c FROM users WHERE is_banned=1").fetchone()["c"]
            total_downloads = con.execute("SELECT COUNT(*) c FROM downloads").fetchone()["c"]
            last_downloads = con.execute("""
                SELECT d.*, u.username
                FROM downloads d
                LEFT JOIN users u ON u.user_id=d.user_id
                ORDER BY d.id DESC LIMIT 20
            """).fetchall()
            platforms = con.execute("""
                SELECT COALESCE(platform,'unknown') platform, COUNT(*) c
                FROM downloads
                GROUP BY COALESCE(platform,'unknown')
                ORDER BY c DESC
                LIMIT 10
            """).fetchall()

        return {
            "total_users": total_users,
            "banned_users": banned_users,
            "total_downloads": total_downloads,
            "last_downloads": last_downloads,
            "platforms": platforms,
        }

    def list_users(self, limit=300, q: str = None):
        base = "SELECT * FROM users"
        args = []
        if q:
            q = q.strip()
            if q.isdigit():
                base += " WHERE user_id=?"
                args.append(int(q))
            else:
                base += " WHERE username LIKE ? OR first_name LIKE ?"
                args.extend([f"%{q}%", f"%{q}%"])
        base += " ORDER BY last_seen DESC LIMIT ?"
        args.append(int(limit))
        with self.conn() as con:
            return con.execute(base, tuple(args)).fetchall()
