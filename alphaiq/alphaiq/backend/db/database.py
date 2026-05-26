"""
AlphaIQ Database — SQLite (local/dev) or PostgreSQL (production)
Full schema: users, watchlists, competitions, trades, signals
"""

import asyncio, hashlib, json, logging, os, sqlite3
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from pathlib import Path

log = logging.getLogger("db")

DB_PATH = os.getenv("DATABASE_URL", str(Path(__file__).parent.parent / "data" / "alphaiq.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id           TEXT PRIMARY KEY,
    username     TEXT UNIQUE NOT NULL,
    email        TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    skill_rating  INTEGER DEFAULT 1000,
    competitions_won INTEGER DEFAULT 0,
    created_at   TEXT DEFAULT (datetime('now')),
    alpaca_key   TEXT,
    alpaca_secret TEXT,
    alpaca_paper  INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS watchlists (
    id      TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    symbol  TEXT NOT NULL,
    added_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS signals (
    id         TEXT PRIMARY KEY,
    symbol     TEXT NOT NULL,
    action     TEXT NOT NULL,
    confidence REAL NOT NULL,
    price      REAL NOT NULL,
    indicators TEXT,
    reasons    TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS paper_trades (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    comp_id    TEXT,
    symbol     TEXT NOT NULL,
    side       TEXT NOT NULL,
    qty        REAL NOT NULL,
    price      REAL NOT NULL,
    pnl        REAL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS competitions (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    start_date  TEXT NOT NULL,
    end_date    TEXT NOT NULL,
    start_cash  REAL DEFAULT 100000,
    status      TEXT DEFAULT 'active',
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS competition_entries (
    id          TEXT PRIMARY KEY,
    comp_id     TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    cash        REAL NOT NULL,
    portfolio_value REAL NOT NULL,
    total_return REAL DEFAULT 0,
    rank        INTEGER DEFAULT 0,
    updated_at  TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (comp_id) REFERENCES competitions(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS mentor_messages (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS whale_alerts (
    id         TEXT PRIMARY KEY,
    symbol     TEXT NOT NULL,
    vol_ratio  REAL NOT NULL,
    dollar_vol REAL NOT NULL,
    pressure   TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
"""

class Database:
    def __init__(self):
        self.path = DB_PATH
        self._conn: Optional[sqlite3.Connection] = None

    async def init(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        await self._seed_competition()
        log.info(f"✅ Database ready: {self.path}")

    async def close(self):
        if self._conn:
            self._conn.close()

    def _exec(self, sql: str, params=()) -> sqlite3.Cursor:
        return self._conn.execute(sql, params)

    def _commit(self):
        self._conn.commit()

    # ── Users ─────────────────────────────────────────────────────────────────
    async def create_user(self, id: str, username: str, email: str, password_hash: str) -> Dict:
        try:
            self._exec(
                "INSERT INTO users (id, username, email, password_hash) VALUES (?,?,?,?)",
                (id, username, email, password_hash)
            )
            self._commit()
            return await self.get_user_by_id(id)
        except sqlite3.IntegrityError:
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        row = self._exec("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        return dict(row) if row else None

    async def get_user_by_id(self, id: str) -> Optional[Dict]:
        row = self._exec("SELECT * FROM users WHERE id=?", (id,)).fetchone()
        return dict(row) if row else None

    async def save_alpaca_keys(self, user_id: str, api_key: str, secret: str, paper: bool):
        self._exec(
            "UPDATE users SET alpaca_key=?, alpaca_secret=?, alpaca_paper=? WHERE id=?",
            (api_key, secret, 1 if paper else 0, user_id)
        )
        self._commit()

    async def update_skill_rating(self, user_id: str, delta: int):
        self._exec("UPDATE users SET skill_rating=skill_rating+? WHERE id=?", (delta, user_id))
        self._commit()

    # ── Watchlist ─────────────────────────────────────────────────────────────
    async def get_watchlist(self, user_id: str) -> List[str]:
        rows = self._exec("SELECT symbol FROM watchlists WHERE user_id=?", (user_id,)).fetchall()
        return [r["symbol"] for r in rows]

    async def add_to_watchlist(self, user_id: str, symbol: str):
        import uuid
        try:
            self._exec("INSERT INTO watchlists (id, user_id, symbol) VALUES (?,?,?)",
                      (str(uuid.uuid4()), user_id, symbol.upper()))
            self._commit()
        except sqlite3.IntegrityError:
            pass

    async def remove_from_watchlist(self, user_id: str, symbol: str):
        self._exec("DELETE FROM watchlists WHERE user_id=? AND symbol=?", (user_id, symbol.upper()))
        self._commit()

    # ── Paper Trades ──────────────────────────────────────────────────────────
    async def save_paper_trade(self, trade: Dict):
        import uuid
        self._exec(
            "INSERT INTO paper_trades (id, user_id, comp_id, symbol, side, qty, price, pnl) VALUES (?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), trade["user_id"], trade.get("comp_id"),
             trade["symbol"], trade["side"], trade["qty"], trade["price"], trade.get("pnl", 0))
        )
        self._commit()

    async def get_user_trades(self, user_id: str, limit: int = 50) -> List[Dict]:
        rows = self._exec(
            "SELECT * FROM paper_trades WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Competitions ──────────────────────────────────────────────────────────
    async def _seed_competition(self):
        existing = self._exec("SELECT id FROM competitions WHERE status='active'").fetchone()
        if existing:
            return
        import uuid
        from datetime import date, timedelta
        today     = date.today()
        monday    = today - timedelta(days=today.weekday())
        friday    = monday + timedelta(days=4)
        self._exec(
            "INSERT INTO competitions (id, name, start_date, end_date, status) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), f"Week {today.isocalendar()[1]} Arena",
             str(monday), str(friday), "active")
        )
        self._commit()
        log.info("🏆 Weekly competition seeded")

    async def get_active_competition(self) -> Optional[Dict]:
        row = self._exec("SELECT * FROM competitions WHERE status='active' ORDER BY created_at DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    async def get_leaderboard(self, comp_id: str, limit: int = 20) -> List[Dict]:
        rows = self._exec("""
            SELECT ce.*, u.username, u.skill_rating
            FROM competition_entries ce
            JOIN users u ON ce.user_id = u.id
            WHERE ce.comp_id=?
            ORDER BY ce.total_return DESC
            LIMIT ?
        """, (comp_id, limit)).fetchall()
        return [dict(r) for r in rows]

    async def upsert_competition_entry(self, comp_id: str, user_id: str, cash: float,
                                        portfolio_value: float, total_return: float):
        import uuid
        existing = self._exec(
            "SELECT id FROM competition_entries WHERE comp_id=? AND user_id=?",
            (comp_id, user_id)
        ).fetchone()
        if existing:
            self._exec(
                "UPDATE competition_entries SET cash=?, portfolio_value=?, total_return=?, updated_at=datetime('now') WHERE comp_id=? AND user_id=?",
                (cash, portfolio_value, total_return, comp_id, user_id)
            )
        else:
            self._exec(
                "INSERT INTO competition_entries (id, comp_id, user_id, cash, portfolio_value, total_return) VALUES (?,?,?,?,?,?)",
                (str(uuid.uuid4()), comp_id, user_id, cash, portfolio_value, total_return)
            )
        self._commit()

    # ── Mentor Messages ───────────────────────────────────────────────────────
    async def save_message(self, user_id: str, role: str, content: str):
        import uuid
        self._exec(
            "INSERT INTO mentor_messages (id, user_id, role, content) VALUES (?,?,?,?)",
            (str(uuid.uuid4()), user_id, role, content)
        )
        self._commit()

    async def get_conversation(self, user_id: str, limit: int = 20) -> List[Dict]:
        rows = self._exec(
            "SELECT role, content, created_at FROM mentor_messages WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return list(reversed([dict(r) for r in rows]))

    # ── Whale Alerts ──────────────────────────────────────────────────────────
    async def save_whale_alert(self, symbol: str, vol_ratio: float, dollar_vol: float, pressure: str):
        import uuid
        self._exec(
            "INSERT INTO whale_alerts (id, symbol, vol_ratio, dollar_vol, pressure) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), symbol, vol_ratio, dollar_vol, pressure)
        )
        self._commit()

    async def get_recent_whale_alerts(self, limit: int = 30) -> List[Dict]:
        rows = self._exec(
            "SELECT * FROM whale_alerts ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
