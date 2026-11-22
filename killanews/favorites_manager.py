"""Articoli salvati, cartelle personalizzate e articoli da leggere."""
import sqlite3

from .database import now_iso


class FavoritesError(Exception):
    pass


class FavoritesManager:
    def __init__(self, db):
        self.db = db

    def is_saved(self, article_id) -> bool:
        return self.db.query_one("SELECT 1 FROM favorites WHERE article_id = ?", (article_id,)) is not None

    def save(self, article_id, folder_id=None, to_read=False):
        with self.db.conn:
            self.db.execute(
                "INSERT INTO favorites(article_id, folder_id, saved_at, to_read) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(article_id) DO UPDATE SET folder_id = COALESCE(excluded.folder_id, favorites.folder_id), "
                "to_read = MAX(favorites.to_read, excluded.to_read)",
                (article_id, folder_id, now_iso(), 1 if to_read else 0))

    def toggle(self, article_id) -> bool:
        """Salva o rimuove; restituisce True se ora l'articolo è salvato."""
        if self.is_saved(article_id):
            self.remove(article_id)
            return False
        self.save(article_id)
        return True

    def remove(self, article_id):
        with self.db.conn:
            self.db.execute("DELETE FROM favorites WHERE article_id = ?", (article_id,))

    def set_to_read(self, article_id, value: bool):
        if not self.is_saved(article_id):
            self.save(article_id, to_read=value)
            return
        with self.db.conn:
            self.db.execute("UPDATE favorites SET to_read = ? WHERE article_id = ?", (1 if value else 0, article_id))

    def move_to_folder(self, article_id, folder_id):
        if not self.is_saved(article_id):
            self.save(article_id, folder_id=folder_id)
            return
        with self.db.conn:
            self.db.execute("UPDATE favorites SET folder_id = ? WHERE article_id = ?", (folder_id, article_id))

    # cartelle
    def folders(self):
        return self.db.query("SELECT f.*, (SELECT COUNT(*) FROM favorites v WHERE v.folder_id = f.id) AS items "
                             "FROM folders f ORDER BY name COLLATE NOCASE")

    def create_folder(self, name) -> int:
        name = (name or "").strip()
        if not name:
            raise FavoritesError("Il nome della cartella non può essere vuoto.")
        try:
            with self.db.conn:
                cur = self.db.execute("INSERT INTO folders(name, created) VALUES (?, ?)", (name, now_iso()))
        except sqlite3.IntegrityError:
            raise FavoritesError(f"Esiste già una cartella chiamata «{name}».")
        return cur.lastrowid

    def rename_folder(self, folder_id, name):
        name = (name or "").strip()
        if not name:
            raise FavoritesError("Il nome della cartella non può essere vuoto.")
        try:
            with self.db.conn:
                self.db.execute("UPDATE folders SET name = ? WHERE id = ?", (name, folder_id))
        except sqlite3.IntegrityError:
            raise FavoritesError(f"Esiste già una cartella chiamata «{name}».")

    def delete_folder(self, folder_id):
        """Elimina la cartella: gli articoli restano tra i salvati, senza cartella."""
        with self.db.conn:
            self.db.execute("UPDATE favorites SET folder_id = NULL WHERE folder_id = ?", (folder_id,))
            self.db.execute("DELETE FROM folders WHERE id = ?", (folder_id,))

    def count(self):
        return self.db.query_one("SELECT COUNT(*) FROM favorites")[0]
