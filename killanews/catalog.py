"""Catalogo di categorie e fonti: caricamento dai file JSON, gestione e classificazione."""
import json
import logging
import re
import uuid

from . import config

log = logging.getLogger(__name__)


class CatalogError(Exception):
    pass


def _norm_text(value) -> str:
    return (value or "").strip()


class Catalog:
    def __init__(self, db):
        self.db = db
        self._keywords = None

    # ------------------------------------------------------------------ caricamento
    def load_categories(self, path=None):
        path = path or config.data_file("categories.json")
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        position = 0
        with self.db.conn:
            for cat in data.get("categorie", []):
                position += 1
                self.db.execute(
                    "INSERT INTO categories(id, name, parent_id, position, hidden, keywords) "
                    "VALUES (?, ?, NULL, ?, ?, '[]') ON CONFLICT(id) DO UPDATE SET "
                    "name = excluded.name, position = excluded.position, hidden = excluded.hidden",
                    (cat["id"], cat["nome"], position, 1 if cat.get("nascosta") else 0))
                for sub in cat.get("sottocategorie", []):
                    position += 1
                    self.db.execute(
                        "INSERT INTO categories(id, name, parent_id, position, hidden, keywords) "
                        "VALUES (?, ?, ?, ?, 0, ?) ON CONFLICT(id) DO UPDATE SET name = excluded.name, "
                        "parent_id = excluded.parent_id, position = excluded.position, keywords = excluded.keywords",
                        (sub["id"], sub["nome"], cat["id"], position,
                         json.dumps(sub.get("parole_chiave", []), ensure_ascii=False)))
        self._keywords = None

    def load_sources(self, path=None, force=False):
        """Importa il catalogo delle fonti. Le fonti modificate o eliminate dall'utente
        non vengono sovrascritte. Restituisce il numero di fonti importate."""
        path = path or config.data_file("sources.json")
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        count = 0
        with self.db.conn:
            for src in data.get("fonti", []):
                self._validate_source_dict(src)
                key = src["id"]
                row = self.db.query_one("SELECT id, user_modified, deleted FROM sources WHERE key = ?", (key,))
                values = (
                    _norm_text(src["nome"]), _norm_text(src.get("paese")), _norm_text(src.get("regione")),
                    _norm_text(src.get("provincia")), _norm_text(src.get("citta")),
                    _norm_text(src.get("gruppo")), _norm_text(src.get("sito")),
                    1 if src.get("testo_completo") else 0,
                )
                if row is None:
                    cur = self.db.execute(
                        "INSERT INTO sources(key, name, country, region, province, city, group_name, site_url, "
                        "fulltext_allowed, origin) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'catalogo')",
                        (key,) + values)
                    source_id = cur.lastrowid
                elif row["deleted"] or (row["user_modified"] and not force):
                    continue
                else:
                    source_id = row["id"]
                    self.db.execute(
                        "UPDATE sources SET name=?, country=?, region=?, province=?, city=?, group_name=?, "
                        "site_url=?, fulltext_allowed=? WHERE id=?", values + (source_id,))
                for feed in src.get("feed", []):
                    self._upsert_feed(source_id, feed)
                count += 1
        return count

    @staticmethod
    def _validate_source_dict(src):
        if not src.get("id") or not src.get("nome"):
            raise CatalogError("Ogni fonte deve avere 'id' e 'nome'.")
        for feed in src.get("feed", []):
            if not re.match(r"^https?://", feed.get("url", "")):
                raise CatalogError(f"Indirizzo del feed non valido per {src['nome']}: {feed.get('url')}")

    def _upsert_feed(self, source_id, feed):
        self.db.execute(
            "INSERT INTO feeds(source_id, url, category_id, is_main, highlight, verification) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(source_id, url) DO UPDATE SET "
            "category_id = excluded.category_id, is_main = excluded.is_main, "
            "highlight = excluded.highlight, verification = excluded.verification",
            (source_id, feed["url"].strip(), feed.get("categoria", "generale"),
             1 if feed.get("principale") else 0, 1 if feed.get("evidenza") else 0,
             feed.get("verifica", "")))

    def ensure_loaded(self, settings):
        """Al primo avvio (o quando cambia il catalogo incluso) carica categorie e fonti."""
        self.load_categories()
        with open(config.data_file("sources.json"), encoding="utf-8") as fh:
            version = json.load(fh).get("versione_catalogo", 1)
        if settings.get("catalog_version", 0) < version or not self.db.query_one("SELECT 1 FROM sources"):
            self.load_sources()
            settings.set("catalog_version", version, notify=False)

    # ------------------------------------------------------------------ categorie
    def categories_tree(self):
        """Restituisce [(categoria, [sottocategorie])] in ordine, escluse le nascoste."""
        rows = self.db.query("SELECT * FROM categories ORDER BY position")
        top = [r for r in rows if r["parent_id"] is None and not r["hidden"]]
        return [(t, [r for r in rows if r["parent_id"] == t["id"]]) for t in top]

    def category_name(self, category_id: str) -> str:
        row = self.db.query_one("SELECT name, parent_id FROM categories WHERE id = ?", (category_id,))
        if not row:
            return "Notizie"
        if row["parent_id"]:
            parent = self.db.query_one("SELECT name FROM categories WHERE id = ?", (row["parent_id"],))
            if parent:
                return f"{parent['name']} - {row['name']}"
        return row["name"]

    def _keyword_table(self):
        if self._keywords is None:
            table = []
            for row in self.db.query("SELECT id, parent_id, keywords FROM categories WHERE parent_id IS NOT NULL"):
                try:
                    words = [w.lower() for w in json.loads(row["keywords"] or "[]") if w.strip()]
                except ValueError:
                    words = []
                if words:
                    table.append((row["id"], row["parent_id"], words))
            self._keywords = table
        return self._keywords

    def classify(self, feed_category: str, title: str, description: str):
        """Categorie dell'articolo: quella del feed più le sottocategorie individuate
        tramite parole chiave, solo all'interno della stessa categoria principale."""
        cats = {feed_category}
        top = feed_category.split("/")[0]
        if top in ("generale", ""):
            return cats
        haystack = f" {title} {description} ".lower()
        for cat_id, parent, words in self._keyword_table():
            if parent != top or cat_id == feed_category:
                continue
            if any(w in haystack for w in words):
                cats.add(cat_id)
        cats.add(top)
        return cats

    # ------------------------------------------------------------------ fonti
    def sources(self, include_disabled=True):
        sql = ("SELECT s.*, (SELECT COUNT(*) FROM feeds f WHERE f.source_id = s.id AND f.enabled = 1) AS feed_count, "
               "(SELECT MAX(f.last_success) FROM feeds f WHERE f.source_id = s.id) AS last_success, "
               "(SELECT COUNT(*) FROM feeds f WHERE f.source_id = s.id AND f.status LIKE 'errore%') AS feed_errors "
               "FROM sources s WHERE s.deleted = 0")
        if not include_disabled:
            sql += " AND s.enabled = 1"
        sql += " ORDER BY s.name COLLATE NOCASE"
        return self.db.query(sql)

    def source(self, source_id):
        return self.db.query_one("SELECT * FROM sources WHERE id = ?", (source_id,))

    def feeds(self, source_id=None, only_enabled=False):
        sql = "SELECT f.*, s.name AS source_name FROM feeds f JOIN sources s ON s.id = f.source_id WHERE s.deleted = 0"
        params = []
        if source_id is not None:
            sql += " AND f.source_id = ?"
            params.append(source_id)
        if only_enabled:
            sql += " AND f.enabled = 1 AND s.enabled = 1"
        return self.db.query(sql + " ORDER BY s.name, f.id", params)

    def groups(self):
        rows = self.db.query("SELECT DISTINCT group_name FROM sources WHERE deleted = 0 ORDER BY group_name")
        return [r["group_name"] or "Altre testate" for r in rows]

    def local_tree(self):
        """{regione: {provincia: {citta: [fonti]}}} con '' per i livelli non indicati."""
        tree = {}
        rows = [r for r in self.sources(include_disabled=False) if r["region"]]
        rows.sort(key=lambda r: (r["region"].lower(), r["province"].lower(), r["city"].lower(), r["name"].lower()))
        for row in rows:
            tree.setdefault(row["region"], {}).setdefault(row["province"], {}).setdefault(row["city"], []).append(row)
        return tree

    def save_source(self, data: dict, source_id=None, feeds=None):
        """Crea o modifica una fonte. data: name, country, region, province, city, group_name,
        site_url, fulltext_allowed, enabled. feeds: lista di dict url/category_id/is_main/highlight."""
        name = _norm_text(data.get("name"))
        if not name:
            raise CatalogError("Il nome della testata è obbligatorio.")
        site = _norm_text(data.get("site_url"))
        if site and not re.match(r"^https?://", site):
            raise CatalogError("L'indirizzo del sito deve iniziare con http:// o https://")
        fields = (name, _norm_text(data.get("country")), _norm_text(data.get("region")),
                  _norm_text(data.get("province")), _norm_text(data.get("city")),
                  _norm_text(data.get("group_name")), site,
                  1 if data.get("fulltext_allowed") else 0, 0 if data.get("enabled") is False else 1)
        with self.db.conn:
            if source_id is None:
                key = "utente_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") + "_" + uuid.uuid4().hex[:8]
                cur = self.db.execute(
                    "INSERT INTO sources(name, country, region, province, city, group_name, site_url, "
                    "fulltext_allowed, enabled, key, origin, user_modified) VALUES (?,?,?,?,?,?,?,?,?,?, 'utente', 1)",
                    fields + (key,))
                source_id = cur.lastrowid
            else:
                self.db.execute(
                    "UPDATE sources SET name=?, country=?, region=?, province=?, city=?, group_name=?, site_url=?, "
                    "fulltext_allowed=?, enabled=?, user_modified=1 WHERE id=?", fields + (source_id,))
            if feeds is not None:
                keep = []
                for feed in feeds:
                    url = _norm_text(feed.get("url"))
                    if not url:
                        continue
                    if not re.match(r"^https?://", url):
                        raise CatalogError(f"Indirizzo del feed non valido: {url}")
                    self.db.execute(
                        "INSERT INTO feeds(source_id, url, category_id, is_main, highlight, verification) "
                        "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(source_id, url) DO UPDATE SET "
                        "category_id = excluded.category_id, is_main = excluded.is_main, highlight = excluded.highlight",
                        (source_id, url, feed.get("category_id") or "generale", 1 if feed.get("is_main") else 0,
                         1 if feed.get("highlight") else 0, feed.get("verification", "aggiunto dall'utente")))
                    keep.append(url)
                if keep:
                    placeholders = ",".join("?" * len(keep))
                    self.db.execute(f"DELETE FROM feeds WHERE source_id = ? AND url NOT IN ({placeholders})",
                                    [source_id] + keep)
                else:
                    self.db.execute("DELETE FROM feeds WHERE source_id = ?", (source_id,))
        return source_id

    def add_feed(self, source_id, url, category_id="generale", verification=""):
        with self.db.conn:
            self.db.execute(
                "INSERT INTO feeds(source_id, url, category_id, is_main, verification) VALUES (?, ?, ?, 1, ?) "
                "ON CONFLICT(source_id, url) DO NOTHING", (source_id, url, category_id, verification))
            self.db.execute("UPDATE sources SET user_modified = 1 WHERE id = ?", (source_id,))

    def delete_source(self, source_id):
        """Le fonti del catalogo vengono nascoste (per non reinserirle), quelle dell'utente eliminate."""
        row = self.source(source_id)
        if not row:
            return
        with self.db.conn:
            if row["origin"] == "catalogo":
                self.db.execute("UPDATE sources SET deleted = 1, enabled = 0 WHERE id = ?", (source_id,))
            else:
                ids = [r["id"] for r in self.db.query(
                    "SELECT id FROM articles WHERE source_id = ? AND id NOT IN (SELECT article_id FROM favorites)",
                    (source_id,))]
                for aid in ids:
                    self.db.fts_delete(aid)
                saved = self.db.query_one("SELECT COUNT(*) FROM favorites f JOIN articles a ON a.id = f.article_id "
                                          "WHERE a.source_id = ?", (source_id,))[0]
                if saved:
                    # Conserva gli articoli salvati: la fonte resta nascosta.
                    self.db.execute("UPDATE sources SET deleted = 1, enabled = 0 WHERE id = ?", (source_id,))
                    self.db.execute("DELETE FROM articles WHERE source_id = ? AND id NOT IN "
                                    "(SELECT article_id FROM favorites)", (source_id,))
                else:
                    self.db.execute("DELETE FROM sources WHERE id = ?", (source_id,))

    def set_source_enabled(self, source_id, enabled: bool):
        with self.db.conn:
            self.db.execute("UPDATE sources SET enabled = ?, user_modified = 1 WHERE id = ?",
                            (1 if enabled else 0, source_id))

    def restore_catalog(self):
        """Ripristina le fonti del catalogo nascoste o modificate."""
        with self.db.conn:
            self.db.execute("UPDATE sources SET deleted = 0, enabled = 1, user_modified = 0 WHERE origin = 'catalogo'")
        return self.load_sources(force=True)

    def import_sources_file(self, path):
        return self.load_sources(path=path, force=True)

    def export_sources(self, path):
        out = {"_info": "Esportazione delle fonti di KILLA NEWS", "versione_catalogo": 1, "fonti": []}
        for s in self.sources():
            out["fonti"].append({
                "id": s["key"], "nome": s["name"], "paese": s["country"], "regione": s["region"],
                "provincia": s["province"], "citta": s["city"], "gruppo": s["group_name"],
                "sito": s["site_url"], "testo_completo": bool(s["fulltext_allowed"]),
                "feed": [{"url": f["url"], "categoria": f["category_id"], "principale": bool(f["is_main"]),
                          "evidenza": bool(f["highlight"]), "verifica": f["verification"]}
                         for f in self.feeds(s["id"])],
            })
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
