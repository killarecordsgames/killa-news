"""Interrogazioni sulle notizie: elenchi per sezione, prima pagina, ricerca universale."""
import datetime
import re

from . import world
from .models import Article

_BASE_SELECT = """
SELECT a.*, s.name AS source_name, s.site_url AS site_url, s.fulltext_allowed AS fulltext_allowed,
       s.country AS country, c.name AS cat_name, cp.name AS parent_cat_name,
       CASE WHEN fav.article_id IS NULL THEN 0 ELSE 1 END AS saved,
       COALESCE(fav.to_read, 0) AS to_read, COALESCE(fo.name, '') AS folder_name,
       CASE WHEN dl.article_id IS NULL THEN 0 ELSE 1 END AS offline,
       COALESCE(h.last_viewed, '') AS last_viewed
FROM articles a
JOIN sources s ON s.id = a.source_id
LEFT JOIN categories c ON c.id = a.category_id
LEFT JOIN categories cp ON cp.id = c.parent_id
LEFT JOIN favorites fav ON fav.article_id = a.id
LEFT JOIN folders fo ON fo.id = fav.folder_id
LEFT JOIN downloads dl ON dl.article_id = a.id
LEFT JOIN history h ON h.article_id = a.id
"""


def row_to_article(row) -> Article:
    cat = row["cat_name"] or "Notizie"
    if row["parent_cat_name"]:
        cat = f"{row['parent_cat_name']} - {cat}"
    return Article(
        id=row["id"], title=row["title"], source_name=row["source_name"], source_id=row["source_id"],
        published=row["published"], category_id=row["category_id"], category_name=cat,
        subtitle=row["subtitle"], description=row["description"], content=row["content"],
        content_status=row["content_status"], author=row["author"], link=row["link"],
        site_url=row["site_url"], fulltext_allowed=bool(row["fulltext_allowed"]),
        saved=bool(row["saved"]), offline=bool(row["offline"]), to_read=bool(row["to_read"]),
        folder_name=row["folder_name"], last_viewed=row["last_viewed"],
        extra={"country": row["country"]})


def _cat_clause(category_id):
    return ("a.id IN (SELECT article_id FROM article_categories WHERE category_id = ? OR category_id LIKE ?)",
            [category_id, category_id + "/%"])


def _since(hours=0, days=0):
    dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours, days=days)
    return dt.replace(microsecond=0).isoformat()


class NewsManager:
    def __init__(self, db, settings=None):
        self.db = db
        self.settings = settings

    def _limit(self):
        try:
            return int(self.settings.get("max_list_items", 500)) if self.settings else 500
        except (TypeError, ValueError):
            return 500

    def _run(self, where, params, order="a.published DESC", include_deleted=False, limit=None):
        clauses = list(where)
        if not include_deleted:
            clauses.append("s.deleted = 0")
        sql = _BASE_SELECT
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += f" ORDER BY {order} LIMIT ?"
        rows = self.db.query(sql, list(params) + [limit or self._limit()])
        return [row_to_article(r) for r in rows]

    # ------------------------------------------------------------ viste
    def list_view(self, view: dict):
        kind = view.get("kind")
        # La Prima pagina resta in italiano: le testate che scrivono in altre lingue
        # si leggono nella sezione Giornali internazionali.
        it = "(s.language = '' OR s.language = 'it')"
        if kind == "home_main":
            return self._run(["a.is_main = 1", "a.published >= ?", it], [_since(days=2)])
        if kind == "home_latest":
            return self._run(["a.published >= ?", it], [_since(hours=3)])
        if kind == "home_recent":
            return self._run([it], [], limit=200)
        if kind == "home_highlight":
            return self._run(["a.highlight = 1", "a.published >= ?", it], [_since(days=1)])
        if kind == "home_deep":
            return self._run(["(length(a.content) >= 3000 OR length(a.description) >= 500)",
                              "a.published >= ?", it], [_since(days=7)])
        if kind == "all":
            return self._run([], [])
        if kind == "category":
            clause, params = _cat_clause(view["category_id"])
            return self._run([clause], params)
        if kind == "source":
            return self._run(["a.source_id = ?"], [view["source_id"]])
        if kind == "group":
            return self._run(["s.group_name = ?"], [view["group"]])
        if kind == "local":
            where, params = ["s.region <> ''"], []
            for key, col in (("region", "s.region"), ("province", "s.province"), ("city", "s.city")):
                if view.get(key):
                    where.append(f"{col} = ?")
                    params.append(view[key])
            return self._run(where, params)
        if kind == "international":
            where, params = ["s.country <> ''", "s.country <> ?", "s.region = ''"], [world.HOME_COUNTRY]
            if view.get("country"):
                where.append("s.country = ?")
                params.append(view["country"])
            elif view.get("continent"):
                clause, p = _continent_clause(view["continent"], self.countries(international=True))
                where.append(clause)
                params.extend(p)
            return self._run(where, params)
        if kind == "saved":
            where, params = ["fav.article_id IS NOT NULL"], []
            if view.get("folder_id") is not None:
                where.append("fav.folder_id = ?")
                params.append(view["folder_id"])
            if view.get("to_read"):
                where.append("fav.to_read = 1")
            return self._run(where, params, order="fav.saved_at DESC", include_deleted=True, limit=5000)
        if kind == "offline":
            return self._run(["dl.article_id IS NOT NULL"], [], order="dl.downloaded_at DESC",
                             include_deleted=True, limit=5000)
        if kind == "history":
            return self._run(["h.article_id IS NOT NULL"], [], order="h.last_viewed DESC",
                             include_deleted=True, limit=2000)
        if kind == "search":
            return self.search(**view.get("params", {}))
        return []

    def get_article(self, article_id):
        rows = self.db.query(_BASE_SELECT + " WHERE a.id = ?", [article_id])
        return row_to_article(rows[0]) if rows else None

    def count_since(self, iso_value):
        return self.db.query_one("SELECT COUNT(*) FROM articles WHERE fetched >= ?", (iso_value,))[0]

    # ------------------------------------------------------------ ricerca
    @staticmethod
    def _fts_expression(text):
        words = re.findall(r"[\w'’-]+", text, flags=re.UNICODE)
        terms = []
        for w in words:
            w = w.replace('"', "").strip("'’-")
            if len(w) >= 2:
                terms.append(f'"{w}"*')
        return " ".join(terms)

    def search(self, text="", category_id="", source_id=None, country="", date_from="", date_to="",
               period="", limit=500, continent=""):
        """Ricerca nei titoli, nei testi, negli autori e nei nomi delle testate.

        period: '' | 'oggi' | '24h' | '7g' | '30g'. date_from/date_to: 'AAAA-MM-GG'."""
        where, params = [], []
        text = (text or "").strip()
        if text:
            expr = self._fts_expression(text) if self.db.fts else ""
            if expr:
                where.append("a.id IN (SELECT rowid FROM articles_fts WHERE articles_fts MATCH ?)")
                params.append(expr)
            else:
                for word in text.split():
                    like = f"%{word}%"
                    where.append("(a.title LIKE ? OR a.description LIKE ? OR a.content LIKE ? "
                                 "OR a.author LIKE ? OR s.name LIKE ?)")
                    params.extend([like] * 5)
        if category_id:
            clause, p = _cat_clause(category_id)
            where.append(clause)
            params.extend(p)
        if source_id:
            where.append("a.source_id = ?")
            params.append(source_id)
        if country:
            where.append("s.country = ?")
            params.append(country)
        elif continent:
            clause, p = _continent_clause(continent, self.countries(international=True))
            where.append(clause)
            params.extend(p)
        if period == "oggi":
            start = datetime.datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
            where.append("a.published >= ?")
            params.append(start.astimezone(datetime.timezone.utc).isoformat())
        elif period in ("24h", "7g", "30g"):
            hours = {"24h": 24, "7g": 24 * 7, "30g": 24 * 30}[period]
            where.append("a.published >= ?")
            params.append(_since(hours=hours))
        if date_from:
            where.append("a.published >= ?")
            params.append(_local_day_start(date_from))
        if date_to:
            where.append("a.published < ?")
            params.append(_local_day_start(date_to, add_days=1))
        return self._run(where, params, include_deleted=True, limit=limit)

    def countries(self, international=False):
        rows = [r[0] for r in self.db.query(
            "SELECT DISTINCT country FROM sources WHERE deleted = 0 AND country <> '' ORDER BY country")]
        if international:
            rows = [c for c in rows if world.is_international(c)]
        return rows

    def continents(self):
        """Continenti per cui esiste almeno una testata (nell'ordine standard)."""
        present = {world.continent_of(c) or "Altri paesi" for c in self.countries(international=True)}
        return [c for c in world.CONTINENTS + ["Altri paesi"] if c in present]


def _continent_clause(continent, known_countries):
    """Clausola SQL per le testate di un continente («Altri paesi» = paesi non classificati)."""
    if continent == "Altri paesi":
        names = [c for c in known_countries if not world.continent_of(c)]
    else:
        names = [c for c in known_countries if world.continent_of(c) == continent]
    if not names:
        return "0", []
    return "s.country IN (" + ",".join("?" * len(names)) + ")", names


def _local_day_start(value, add_days=0):
    day = datetime.date.fromisoformat(value) + datetime.timedelta(days=add_days)
    local = datetime.datetime(day.year, day.month, day.day).astimezone()
    return local.astimezone(datetime.timezone.utc).replace(microsecond=0).isoformat()


def parse_italian_date(text: str):
    """Converte 'GG/MM/AAAA' (o 'GG-MM-AAAA', 'AAAA-MM-GG') in 'AAAA-MM-GG'. Solleva ValueError."""
    text = (text or "").strip()
    if not text:
        return ""
    m = re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", text)
    if m:
        d, mth, y = map(int, m.groups())
        return datetime.date(y, mth, d).isoformat()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if m:
        y, mth, d = map(int, m.groups())
        return datetime.date(y, mth, d).isoformat()
    raise ValueError("Formato della data non valido. Usa giorno/mese/anno, per esempio 20/11/2026.")
