"""Cronologia degli articoli consultati."""
from .database import now_iso


class HistoryManager:
    def __init__(self, db, settings=None):
        self.db = db
        self.settings = settings

    def record(self, article_id):
        if self.settings is not None and not self.settings.get("history_enabled", True):
            return
        with self.db.conn:
            self.db.execute(
                "INSERT INTO history(article_id, last_viewed, view_count) VALUES (?, ?, 1) "
                "ON CONFLICT(article_id) DO UPDATE SET last_viewed = excluded.last_viewed, "
                "view_count = history.view_count + 1", (article_id, now_iso()))

    def remove(self, article_id):
        with self.db.conn:
            self.db.execute("DELETE FROM history WHERE article_id = ?", (article_id,))

    def clear(self):
        with self.db.conn:
            self.db.execute("DELETE FROM history")

    def count(self):
        return self.db.query_one("SELECT COUNT(*) FROM history")[0]
