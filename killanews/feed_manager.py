"""Recupero e salvataggio delle notizie dai feed RSS/Atom.

- Richieste HTTP con ETag/Last-Modified (nessun traffico inutile).
- Controllo dei duplicati per testata (GUID, collegamento normalizzato, titolo).
- Nessun aggiramento di paywall: si legge soltanto ciò che il feed pubblica.
"""
import calendar
import datetime
import hashlib
import html
import logging
import re
import threading
import urllib.parse
from dataclasses import dataclass, field

import feedparser
import requests

from . import config
from .database import now_iso

log = logging.getLogger(__name__)

TIMEOUT = 20
MAX_ENTRIES_PER_FEED = 100
FULL_CONTENT_MIN_CHARS = 1200
_TRACKING_PARAMS = re.compile(r"^(utm_|fbclid|gclid|ref$|refresh_ce|ns_|cmpid|ito$|xtor)", re.I)
_local = threading.local()


def session() -> requests.Session:
    s = getattr(_local, "session", None)
    if s is None:
        s = requests.Session()
        s.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.9, */*;q=0.5",
            "Accept-Language": "it-IT,it;q=0.9,en;q=0.7",
        })
        _local.session = s
    return s


# ----------------------------------------------------------------------- testo
_BLOCK_TAGS = re.compile(r"(?i)<\s*(br|/p|/div|/li|/h[1-6]|/blockquote|/tr)\s*/?>")
_TAG = re.compile(r"<[^>]+>")
_SCRIPT = re.compile(r"(?is)<(script|style|noscript|iframe)[^>]*>.*?</\1>")


def html_to_text(value: str) -> str:
    """Converte HTML in testo semplice mantenendo i paragrafi."""
    if not value:
        return ""
    text = _SCRIPT.sub(" ", value)
    text = _BLOCK_TAGS.sub("\n\n", text)
    text = _TAG.sub(" ", text)
    text = html.unescape(text).replace("\xa0", " ")
    lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.split("\n")]
    paragraphs, current = [], []
    for line in lines:
        if line:
            current.append(line)
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(p for p in paragraphs if p)


def normalize_link(url: str) -> str:
    """Rimuove parametri di tracciamento, frammenti e barre finali per confrontare i collegamenti."""
    if not url:
        return ""
    try:
        parts = urllib.parse.urlsplit(url.strip())
    except ValueError:
        return url.strip().lower()
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
             if not _TRACKING_PARAMS.match(k)]
    path = re.sub(r"/{2,}", "/", parts.path).rstrip("/")
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return urllib.parse.urlunsplit(("", netloc, path, urllib.parse.urlencode(query), "")).lstrip("/")


def make_uid(source_id: int, guid: str, norm_link: str, title: str) -> str:
    basis = guid or norm_link or title.strip().lower()
    return hashlib.sha1(f"{source_id}|{basis}".encode("utf-8")).hexdigest()


def entry_date(entry) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        value = entry.get(key)
        if value:
            try:
                dt = datetime.datetime.fromtimestamp(calendar.timegm(value), tz=datetime.timezone.utc)
            except (OverflowError, ValueError, TypeError):
                continue
            if dt > now + datetime.timedelta(minutes=10):
                dt = now  # date nel futuro dovute a fusi orari errati
            return dt.replace(microsecond=0).isoformat()
    return now.replace(microsecond=0).isoformat()


# ----------------------------------------------------------------------- risultati
@dataclass
class ParsedEntry:
    guid: str
    title: str
    link: str
    norm_link: str
    published: str
    description: str
    content: str
    author: str


@dataclass
class FetchResult:
    feed_id: int
    source_id: int
    ok: bool
    not_modified: bool = False
    network_error: bool = False
    error: str = ""
    etag: str = ""
    modified: str = ""
    feed_title: str = ""
    entries: list = field(default_factory=list)


def parse_feed_bytes(data: bytes, base_url: str = "") -> tuple:
    """Analizza il contenuto di un feed. Restituisce (titolo_feed, [ParsedEntry]).
    Solleva ValueError se il contenuto non è un feed valido."""
    parsed = feedparser.parse(data, response_headers={"content-location": base_url} if base_url else None)
    if not parsed.entries and (parsed.bozo or not parsed.feed):
        reason = getattr(parsed, "bozo_exception", None)
        raise ValueError(f"il contenuto non è un feed RSS o Atom valido ({reason})" if reason
                         else "il contenuto non è un feed RSS o Atom valido")
    entries = []
    for entry in parsed.entries[:MAX_ENTRIES_PER_FEED]:
        title = html_to_text(entry.get("title", "")).replace("\n", " ").strip()
        link = (entry.get("link") or "").strip()
        if not title and not link:
            continue
        description = html_to_text(entry.get("summary", "") or entry.get("description", ""))
        content = ""
        for block in entry.get("content", []) or []:
            text = html_to_text(block.get("value", ""))
            if len(text) > len(content):
                content = text
        author = (entry.get("author") or "").strip()
        if not title:
            title = description[:120] or link
        entries.append(ParsedEntry(
            guid=(entry.get("id") or entry.get("guid") or "").strip(),
            title=title, link=link, norm_link=normalize_link(link), published=entry_date(entry),
            description=description, content=content, author=author))
    return (html_to_text(parsed.feed.get("title", "")) if parsed.feed else ""), entries


def fetch_feed(feed_row) -> FetchResult:
    """Scarica un feed (usabile da più thread contemporaneamente)."""
    headers = {}
    if feed_row["etag"]:
        headers["If-None-Match"] = feed_row["etag"]
    if feed_row["modified"]:
        headers["If-Modified-Since"] = feed_row["modified"]
    result = FetchResult(feed_id=feed_row["id"], source_id=feed_row["source_id"], ok=False)
    try:
        resp = session().get(feed_row["url"], headers=headers, timeout=TIMEOUT)
    except (requests.ConnectionError, requests.Timeout) as exc:
        result.network_error = True
        result.error = "non raggiungibile: " + _short_error(exc)
        return result
    except requests.RequestException as exc:
        result.error = "errore: " + _short_error(exc)
        return result
    if resp.status_code == 304:
        result.ok = True
        result.not_modified = True
        result.etag, result.modified = feed_row["etag"], feed_row["modified"]
        return result
    if resp.status_code >= 400:
        result.error = f"errore HTTP {resp.status_code}"
        return result
    try:
        result.feed_title, result.entries = parse_feed_bytes(resp.content, resp.url)
    except ValueError as exc:
        result.error = "errore: " + str(exc)
        return result
    result.ok = True
    result.etag = resp.headers.get("ETag", "")
    result.modified = resp.headers.get("Last-Modified", "")
    return result


def _short_error(exc) -> str:
    text = str(exc)
    if "NameResolution" in text or "getaddrinfo" in text:
        return "indirizzo non trovato o connessione assente"
    if "timed out" in text.lower():
        return "tempo di attesa scaduto"
    return text[:160]


# ----------------------------------------------------------------------- salvataggio
def store_result(db, catalog, result: FetchResult) -> int:
    """Aggiorna lo stato del feed e salva i nuovi articoli. Restituisce quanti sono nuovi."""
    now = now_iso()
    feed = db.query_one("SELECT * FROM feeds WHERE id = ?", (result.feed_id,))
    if feed is None:
        return 0
    if not result.ok:
        db.execute("UPDATE feeds SET status = ?, last_error = ?, last_checked = ?, error_count = error_count + 1 "
                   "WHERE id = ?", (result.error.split(":")[0], result.error, now, result.feed_id))
        db.commit()
        return 0
    db.execute("UPDATE feeds SET status = 'ok', last_error = '', last_checked = ?, last_success = ?, "
               "error_count = 0, etag = ?, modified = ? WHERE id = ?",
               (now, now, result.etag, result.modified, result.feed_id))
    source = db.query_one("SELECT name FROM sources WHERE id = ?", (result.source_id,))
    new_count = 0
    for e in result.entries:
        uid = make_uid(result.source_id, e.guid, e.norm_link, e.title)
        existing = db.query_one("SELECT id FROM articles WHERE uid = ?", (uid,))
        if existing is None and e.norm_link:
            existing = db.query_one("SELECT id FROM articles WHERE source_id = ? AND norm_link = ?",
                                    (result.source_id, e.norm_link))
        if existing is None:
            existing = db.query_one(
                "SELECT id FROM articles WHERE source_id = ? AND title = ? AND published >= ?",
                (result.source_id, e.title, _days_before(e.published, 2)))
        cats = catalog.classify(feed["category_id"], e.title, e.description)
        if existing is not None:
            article_id = existing["id"]
            if feed["is_main"] or feed["highlight"]:
                db.execute("UPDATE articles SET is_main = MAX(is_main, ?), highlight = MAX(highlight, ?) WHERE id = ?",
                           (feed["is_main"], feed["highlight"], article_id))
        else:
            content, status = "", "anteprima"
            if len(e.content) >= FULL_CONTENT_MIN_CHARS and len(e.content) > len(e.description):
                content, status = e.content, "completo"
            elif not e.description and not e.content:
                status = "non_disponibile"
            cur = db.execute(
                "INSERT INTO articles(uid, source_id, feed_id, title, description, content, content_status, "
                "author, link, norm_link, published, fetched, category_id, is_main, highlight) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (uid, result.source_id, result.feed_id, e.title, e.description, content, status, e.author,
                 e.link, e.norm_link, e.published, now, feed["category_id"], feed["is_main"], feed["highlight"]))
            article_id = cur.lastrowid
            new_count += 1
        for cat in cats:
            db.execute("INSERT OR IGNORE INTO article_categories(article_id, category_id) VALUES (?, ?)",
                       (article_id, cat))
        if existing is None:
            db.fts_index(article_id)
    db.commit()
    log.debug("%s: %d nuovi articoli", source["name"] if source else result.source_id, new_count)
    return new_count


def _days_before(iso_value: str, days: int) -> str:
    try:
        dt = datetime.datetime.fromisoformat(iso_value)
    except ValueError:
        dt = datetime.datetime.now(datetime.timezone.utc)
    return (dt - datetime.timedelta(days=days)).isoformat()


def prune_old_articles(db, days: int) -> int:
    """Elimina gli articoli più vecchi di `days` giorni che non sono salvati né scaricati."""
    if days <= 0:
        return 0
    limit = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
    ids = [r["id"] for r in db.query(
        "SELECT id FROM articles WHERE published < ? AND id NOT IN (SELECT article_id FROM favorites) "
        "AND id NOT IN (SELECT article_id FROM downloads)", (limit,))]
    for aid in ids:
        db.fts_delete(aid)
    db.execute("DELETE FROM history WHERE article_id IN (SELECT id FROM articles WHERE published < ? AND "
               "id NOT IN (SELECT article_id FROM favorites) AND id NOT IN (SELECT article_id FROM downloads))",
               (limit,))
    db.execute("DELETE FROM articles WHERE published < ? AND id NOT IN (SELECT article_id FROM favorites) "
               "AND id NOT IN (SELECT article_id FROM downloads)", (limit,))
    db.commit()
    return len(ids)


# ----------------------------------------------------------------------- scoperta feed
_LINK_TAG = re.compile(r"<link\b[^>]*>", re.I)
_ATTR = re.compile(r'([a-zA-Z_:-]+)\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s>]+))')


def discover_feeds(site_url: str, validate: bool = True):
    """Cerca i feed dichiarati dal sito stesso (<link rel="alternate" type="application/rss+xml">).
    Restituisce [(url, titolo)] verificati scaricandoli. Non inventa indirizzi."""
    resp = session().get(site_url, timeout=TIMEOUT, headers={"Accept": "text/html,*/*"})
    resp.raise_for_status()
    found = []
    for tag in _LINK_TAG.findall(resp.text[:400000]):
        attrs = {}
        for m in _ATTR.finditer(tag):
            attrs[m.group(1).lower()] = html.unescape(m.group(3) or m.group(4) or m.group(5) or "")
        rel = attrs.get("rel", "").lower()
        typ = attrs.get("type", "").lower()
        if "alternate" in rel and ("rss" in typ or "atom" in typ) and attrs.get("href"):
            url = urllib.parse.urljoin(resp.url, attrs["href"])
            if url not in [f[0] for f in found]:
                found.append((url, attrs.get("title", "")))
    if not validate:
        return found
    valid = []
    for url, title in found[:10]:
        try:
            r = session().get(url, timeout=TIMEOUT)
            r.raise_for_status()
            feed_title, entries = parse_feed_bytes(r.content, r.url)
            valid.append((url, title or feed_title or url))
        except (requests.RequestException, ValueError) as exc:
            log.info("Feed dichiarato ma non valido %s: %s", url, exc)
    return valid


def test_feed_url(url: str):
    """Verifica un indirizzo: restituisce (ok, messaggio, numero_articoli)."""
    try:
        r = session().get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return False, "Non raggiungibile: " + _short_error(exc), 0
    if r.status_code >= 400:
        return False, f"Errore HTTP {r.status_code}", 0
    try:
        title, entries = parse_feed_bytes(r.content, r.url)
    except ValueError as exc:
        return False, str(exc), 0
    return True, f"Feed valido: {title or url}, {len(entries)} articoli", len(entries)
