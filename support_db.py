import sqlite3
from datetime import datetime, timezone

def utcnow_iso():
    return datetime.now(timezone.utc).isoformat()

class SupportDB:
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
            CREATE TABLE IF NOT EXISTS support_messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              direction TEXT NOT NULL, -- in|out
              text TEXT,
              tg_message_id INTEGER,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_support_user ON support_messages(user_id, id);
            """)

    def log_msg(self, user_id: int, direction: str, text: str, tg_message_id=None):
        with self.conn() as con:
            con.execute("""
            INSERT INTO support_messages(user_id,direction,text,tg_message_id,created_at)
            VALUES(?,?,?,?,?)
            """, (int(user_id), direction, text or "", tg_message_id, utcnow_iso()))

    def list_threads(self, limit=200):
        with self.conn() as con:
            return con.execute("""
            SELECT user_id, MAX(id) last_id, MAX(created_at) last_time
            FROM support_messages
            GROUP BY user_id
            ORDER BY last_id DESC
            LIMIT ?
            """, (int(limit),)).fetchall()

    def list_msgs(self, user_id: int, limit=200):
        with self.conn() as con:
            rows = con.execute("""
            SELECT * FROM support_messages
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT ?
            """, (int(user_id), int(limit))).fetchall()
        return list(reversed(rows))
