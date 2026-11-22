"""Database SQLite di KILLA NEWS: schema, migrazioni, backup e accesso sicuro da più thread.

Ogni thread usa la propria connessione (la classe Database va istanziata per thread).
Il database usa la modalità WAL, così l'aggiornamento in background non blocca
la lettura dell'interfaccia."""
import datetime
import glob
import logging
import os
import shutil
import sqlite3
import threading

from . import config

log = logging.getLogger(__name__)

_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    hidden INTEGER NOT NULL DEFAULT 0,
    keywords TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT '',
    region TEXT NOT NULL DEFAULT '',
    province TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT '',
    group_name TEXT NOT NULL DEFAULT '',
    site_url TEXT NOT NULL DEFAULT '',
    fulltext_allowed INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    origin TEXT NOT NULL DEFAULT 'catalogo',
    user_modified INTEGER NOT NULL DEFAULT 0,
    deleted INTEGER NOT NULL DEFAULT 0,
    language TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    category_id TEXT NOT NULL DEFAULT 'generale',
    is_main INTEGER NOT NULL DEFAULT 0,
    highlight INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    verification TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'mai controllato',
    last_error TEXT NOT NULL DEFAULT '',
    last_checked TEXT NOT NULL DEFAULT '',
    last_success TEXT NOT NULL DEFAULT '',
    error_count INTEGER NOT NULL DEFAULT 0,
    etag TEXT NOT NULL DEFAULT '',
    modified TEXT NOT NULL DEFAULT '',
    UNIQUE(source_id, url)
);

CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE NOT NULL,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    feed_id INTEGER,
    title TEXT NOT NULL,
    subtitle TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    content_status TEXT NOT NULL DEFAULT 'anteprima',
    author TEXT NOT NULL DEFAULT '',
    link TEXT NOT NULL DEFAULT '',
    norm_link TEXT NOT NULL DEFAULT '',
    published TEXT NOT NULL,
    fetched TEXT NOT NULL,
    category_id TEXT NOT NULL DEFAULT 'generale',
    is_main INTEGER NOT NULL DEFAULT 0,
    highlight INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published DESC);
CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source_id, published DESC);
CREATE INDEX IF NOT EXISTS idx_articles_normlink ON articles(source_id, norm_link);

CREATE TABLE IF NOT EXISTS article_categories (
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    category_id TEXT NOT NULL,
    PRIMARY KEY (article_id, category_id)
);
CREATE INDEX IF NOT EXISTS idx_artcat_cat ON article_categories(category_id);

CREATE TABLE IF NOT EXISTS folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS favorites (
    article_id INTEGER PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
    folder_id INTEGER REFERENCES folders(id) ON DELETE SET NULL,
    saved_at TEXT NOT NULL,
    to_read INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS history (
    article_id INTEGER PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
    last_viewed TEXT NOT NULL,
    view_count INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_history_last ON history(last_viewed DESC);

CREATE TABLE IF NOT EXISTS downloads (
    article_id INTEGER PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
    downloaded_at TEXT NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS translations (
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    target TEXT NOT NULL DEFAULT 'it',
    source_lang TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    subtitle TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    body_hash TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (article_id, target)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
    title, description, content, author, source_name,
    tokenize = 'unicode61 remove_diacritics 2'
);
"""

# Migrazioni future: {versione_di_arrivo: [istruzioni SQL]}.
# Esempio per la 1.1.0:  2: ["ALTER TABLE articles ADD COLUMN image_url TEXT NOT NULL DEFAULT ''"]
MIGRATIONS = {
    # 1.2.0: lingua delle testate (per la traduzione e per tenere la Prima pagina in italiano)
    2: ["ALTER TABLE sources ADD COLUMN language TEXT NOT NULL DEFAULT ''"],
}

_init_lock = threading.Lock()


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


class Database:
    """Connessione SQLite per il thread corrente."""

    def __init__(self, path: str = None):
        self.path = path or config.db_path()
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(self.path, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        with _init_lock:
            self._ensure_schema()
        self.fts = self._has_table("articles_fts")

    # --- schema ---------------------------------------------------------
    def _has_table(self, name: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name = ?", (name,)).fetchone()
        return row is not None

    def _ensure_schema(self):
        try:
            self.conn.executescript(_SCHEMA_V1)
        except sqlite3.DatabaseError as exc:
            log.exception("Database danneggiato: %s", exc)
            raise
        try:
            self.conn.executescript(_FTS_SQL)
        except sqlite3.OperationalError:
            log.warning("FTS5 non disponibile: la ricerca userà LIKE.")
        row = self.conn.execute("SELECT version FROM schema_version").fetchone()
        if row is None:
            self.conn.execute("INSERT INTO schema_version(version) VALUES (?)",
                              (config.DB_SCHEMA_VERSION,))
            self.conn.commit()
            return
        current = row["version"]
        for version in sorted(v for v in MIGRATIONS if v > current):
            log.info("Migrazione del database alla versione %s", version)
            with self.conn:
                for statement in MIGRATIONS[version]:
                    self.conn.execute(statement)
                self.conn.execute("UPDATE schema_version SET version = ?", (version,))

    def schema_version(self) -> int:
        return self.conn.execute("SELECT version FROM schema_version").fetchone()["version"]

    # --- utilità ----------------------------------------------------------
    def execute(self, sql, params=()):
        return self.conn.execute(sql, params)

    def query(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    def query_one(self, sql, params=()):
        return self.conn.execute(sql, params).fetchone()

    def commit(self):
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except sqlite3.Error:
            pass

    # --- impostazioni grezze ---------------------------------------------
    def get_setting_raw(self, key):
        row = self.query_one("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else None

    def set_setting_raw(self, key, value):
        self.execute("INSERT INTO settings(key, value) VALUES(?, ?) "
                     "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
        self.commit()

    # --- FTS ----------------------------------------------------------------
    def fts_index(self, article_id: int):
        if not self.fts:
            return
        row = self.query_one(
            "SELECT a.title, a.description, a.content, a.author, s.name AS source_name "
            "FROM articles a JOIN sources s ON s.id = a.source_id WHERE a.id = ?", (article_id,))
        self.execute("DELETE FROM articles_fts WHERE rowid = ?", (article_id,))
        if row:
            self.execute("INSERT INTO articles_fts(rowid, title, description, content, author, source_name) "
                         "VALUES (?, ?, ?, ?, ?, ?)",
                         (article_id, row["title"], row["description"], row["content"],
                          row["author"], row["source_name"]))

    def fts_delete(self, article_id: int):
        if self.fts:
            self.execute("DELETE FROM articles_fts WHERE rowid = ?", (article_id,))

    # --- manutenzione -------------------------------------------------------
    def integrity_ok(self) -> bool:
        try:
            return self.query_one("PRAGMA integrity_check")[0] == "ok"
        except sqlite3.Error:
            return False

    def size_bytes(self) -> int:
        total = 0
        for suffix in ("", "-wal", "-shm"):
            p = self.path + suffix
            if os.path.exists(p):
                total += os.path.getsize(p)
        return total


def backup_database(db: Database, keep: int = 5) -> str:
    """Crea una copia coerente del database nella cartella backup e conserva le ultime `keep`."""
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    target = os.path.join(config.backup_dir(), f"killanews_{stamp}.db")
    dest = sqlite3.connect(target)
    try:
        db.conn.backup(dest)
    finally:
        dest.close()
    backups = sorted(glob.glob(os.path.join(config.backup_dir(), "killanews_*.db")))
    for old in backups[:-keep]:
        try:
            os.remove(old)
        except OSError:
            pass
    return target


def list_backups():
    return sorted(glob.glob(os.path.join(config.backup_dir(), "killanews_*.db")), reverse=True)


def schedule_restore(backup_file: str) -> None:
    """Prepara il ripristino: il file viene copiato al prossimo avvio, a database chiuso."""
    pending = os.path.join(config.user_data_dir(), "restore_pending.db")
    shutil.copy2(backup_file, pending)


def apply_pending_restore() -> bool:
    """Da chiamare all'avvio, prima di aprire il database."""
    pending = os.path.join(config.user_data_dir(), "restore_pending.db")
    if not os.path.exists(pending):
        return False
    target = config.db_path()
    for suffix in ("-wal", "-shm"):
        if os.path.exists(target + suffix):
            os.remove(target + suffix)
    shutil.move(pending, target)
    return True
