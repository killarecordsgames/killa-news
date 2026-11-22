"""Archivio offline: articoli scaricati, spazio occupato, esportazione in testo."""
import datetime
import os
import re

from . import article_reader
from .database import now_iso
from .models import format_date, CONTENT_LABELS


class DownloadManager:
    def __init__(self, db, settings=None):
        self.db = db
        self.settings = settings

    def is_offline(self, article_id) -> bool:
        return self.db.query_one("SELECT 1 FROM downloads WHERE article_id = ?", (article_id,)) is not None

    def download(self, article, allow_fetch=True):
        """Rende l'articolo disponibile offline. Se consentito, prima recupera il testo integrale.
        Restituisce lo stato del testo salvato ('completo' o 'anteprima')."""
        status = article.content_status
        if (allow_fetch and status != "completo" and article.fulltext_allowed and article.link
                and (self.settings is None or self.settings.get("fetch_full_text", True))):
            result = article_reader.fetch_full_text(article.link, article.description)
            article_reader.save_extract(self.db, article.id, result)
            status = result.status if result.status == "completo" else status
        row = self.db.query_one("SELECT length(title) + length(description) + length(content) + "
                                "length(subtitle) AS n FROM articles WHERE id = ?", (article.id,))
        size = int(row["n"] or 0) * 2 if row else 0
        with self.db.conn:
            self.db.execute("INSERT INTO downloads(article_id, downloaded_at, size_bytes) VALUES (?, ?, ?) "
                            "ON CONFLICT(article_id) DO UPDATE SET downloaded_at = excluded.downloaded_at, "
                            "size_bytes = excluded.size_bytes", (article.id, now_iso(), size))
        return status

    def remove(self, article_id):
        with self.db.conn:
            self.db.execute("DELETE FROM downloads WHERE article_id = ?", (article_id,))

    def stats(self):
        row = self.db.query_one("SELECT COUNT(*) AS n, COALESCE(SUM(size_bytes), 0) AS size FROM downloads")
        return row["n"], row["size"]

    def remove_older_than(self, days: int) -> int:
        limit = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
        with self.db.conn:
            cur = self.db.execute("DELETE FROM downloads WHERE downloaded_at < ?", (limit,))
        return cur.rowcount

    def clear(self) -> int:
        with self.db.conn:
            cur = self.db.execute("DELETE FROM downloads")
        return cur.rowcount

    @staticmethod
    def article_as_text(article) -> str:
        lines = [article.title]
        if article.subtitle:
            lines.append(article.subtitle)
        lines += ["", f"Testata: {article.source_name}", f"Data: {format_date(article.published)}"]
        if article.author:
            lines.append(f"Autore: {article.author}")
        lines += [f"Categoria: {article.category_name}",
                  f"Stato del testo: {CONTENT_LABELS.get(article.content_status, article.content_status)}",
                  "", article.body_text, ""]
        if article.link:
            lines.append(f"Fonte originale: {article.link}")
        lines.append("Esportato con KILLA NEWS - Killa Records")
        return "\n".join(lines)

    @staticmethod
    def article_as_html(article, font_size=12) -> str:
        """Versione stampabile dell'articolo (HTML semplice, caratteri grandi e leggibili)."""
        import html as _html
        e = _html.escape
        parts = [f'<html><body><font size="+1"><b>{e(article.title)}</b></font>']
        if article.subtitle:
            parts.append(f"<p><i>{e(article.subtitle)}</i></p>")
        meta = [f"Testata: {e(article.source_name)}", f"Data: {e(format_date(article.published))}"]
        if article.author:
            meta.append(f"Autore: {e(article.author)}")
        meta.append(f"Categoria: {e(article.category_name)}")
        meta.append(f"Stato del testo: {e(CONTENT_LABELS.get(article.content_status, article.content_status))}")
        parts.append("<p>" + "<br>".join(meta) + "</p><hr>")
        for par in article_reader.split_paragraphs(article.body_text):
            parts.append(f"<p>{e(par)}</p>")
        if article.is_partial:
            parts.append("<p><i>Questo è un estratto: il testo completo è disponibile sul sito della testata.</i></p>")
        if article.link:
            parts.append(f"<hr><p>Fonte originale: {e(article.link)}</p>")
        parts.append("<p><small>Stampato con KILLA NEWS - Killa Records</small></p></body></html>")
        return "".join(parts)

    def export_txt(self, article, folder) -> str:
        os.makedirs(folder, exist_ok=True)
        safe = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", article.title).strip()[:90] or "articolo"
        path = os.path.join(folder, f"{safe}.txt")
        n = 2
        while os.path.exists(path):
            path = os.path.join(folder, f"{safe} ({n}).txt")
            n += 1
        with open(path, "w", encoding="utf-8-sig") as fh:  # BOM: Blocco note lo apre correttamente
            fh.write(self.article_as_text(article))
        return path
