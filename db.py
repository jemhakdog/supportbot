"""SQLite schema + helpers. One file, WAL mode, stdlib sqlite3 + FTS5."""
import pathlib
import sqlite3

DB_PATH = pathlib.Path(__file__).parent / "var" / "supportbot.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS docs (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    title    TEXT NOT NULL,
    added_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS chunks (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id  INTEGER NOT NULL,
    ordinal INTEGER NOT NULL DEFAULT 0,
    text    TEXT NOT NULL
);
-- plain FTS5 table; rowid is kept equal to chunks.id (BUILD §2: no pgvector)
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(text);
CREATE TABLE IF NOT EXISTS tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    subject     TEXT NOT NULL DEFAULT '',
    body        TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT 'general',
    urgency     TEXT NOT NULL DEFAULT 'normal',
    sentiment   TEXT NOT NULL DEFAULT 'neutral',
    status      TEXT NOT NULL DEFAULT 'processing',
    draft       TEXT NOT NULL DEFAULT '',
    confidence  REAL NOT NULL DEFAULT 0,
    n_sources   INTEGER NOT NULL DEFAULT 0,
    citations   TEXT NOT NULL DEFAULT '[]',  -- json [{n,doc,text}]
    critic      TEXT NOT NULL DEFAULT '[]',  -- json [{sentence,supported,matched}]
    reply       TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get(path=None) -> sqlite3.Connection:
    p = pathlib.Path(path) if path else DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def init(path=None) -> None:
    with get(path) as con:
        con.executescript(SCHEMA)


def get_setting(con: sqlite3.Connection, key: str, default: str = "") -> str:
    row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(con: sqlite3.Connection, key: str, value: str) -> None:
    con.execute(
        "INSERT INTO settings(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
