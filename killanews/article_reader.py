"""Recupero del testo integrale degli articoli dalle pagine pubbliche.

Regole rispettate:
- si scarica solo la pagina pubblica, senza credenziali e senza cookie di sessione;
- se la pagina dichiara contenuto riservato agli abbonati (isAccessibleForFree = false)
  il testo non viene estratto e si mostra l'anteprima con il collegamento alla fonte;
- per le testate con paywall il recupero è disattivato nel catalogo (testo_completo = false).
"""
import json
import logging
import re
from dataclasses import dataclass

import requests

from . import config
from .database import now_iso
from .feed_manager import html_to_text

log = logging.getLogger(__name__)

try:  # estrattore di qualità, facoltativo
    import trafilatura  # type: ignore
except Exception:  # pragma: no cover - dipende dall'ambiente
    trafilatura = None

try:
    import lxml.html  # type: ignore
except Exception:  # pragma: no cover
    lxml = None

MIN_FULL_CHARS = 600


@dataclass
class ExtractResult:
    status: str            # completo | anteprima | non_disponibile
    text: str = ""
    author: str = ""
    subtitle: str = ""
    reason: str = ""


_JSONLD = re.compile(r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>')
_META = re.compile(r'(?is)<meta\s+[^>]*(?:property|name)=["\']([^"\']+)["\'][^>]*content=["\']([^"\']*)["\']')


def _iter_jsonld(page: str):
    for block in _JSONLD.findall(page):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        stack = [data]
        while stack:
            item = stack.pop()
            if isinstance(item, list):
                stack.extend(item)
            elif isinstance(item, dict):
                yield item
                if "@graph" in item:
                    stack.append(item["@graph"])


def is_paywalled(page: str) -> bool:
    for item in _iter_jsonld(page):
        value = item.get("isAccessibleForFree")
        if isinstance(value, bool) and value is False:
            return True
        if isinstance(value, str) and value.strip().lower() in ("false", "no", "0"):
            return True
    return False


def _jsonld_article(page: str):
    for item in _iter_jsonld(page):
        typ = item.get("@type")
        types = typ if isinstance(typ, list) else [typ]
        if any(t and "Article" in str(t) for t in types):
            body = item.get("articleBody") or ""
            author = item.get("author") or ""
            if isinstance(author, list):
                author = ", ".join(a.get("name", "") if isinstance(a, dict) else str(a) for a in author)
            elif isinstance(author, dict):
                author = author.get("name", "")
            subtitle = item.get("alternativeHeadline") or item.get("description") or ""
            return html_to_text(str(body)), str(author).strip(), html_to_text(str(subtitle))
    return "", "", ""


def _meta(page: str):
    return {k.lower(): v for k, v in _META.findall(page[:200000])}


def _lxml_extract(page: str) -> str:
    if lxml is None:
        return ""
    try:
        tree = lxml.html.fromstring(page)
    except (ValueError, lxml.etree.ParserError):  # type: ignore[attr-defined]
        return ""
    for bad in tree.xpath("//script|//style|//nav|//footer|//aside|//form|//noscript|//figure"):
        bad.getparent().remove(bad)
    candidates = tree.xpath("//*[@itemprop='articleBody']") or tree.xpath("//article") or [tree]
    best = ""
    for node in candidates:
        paragraphs = [re.sub(r"\s+", " ", p.text_content()).strip() for p in node.xpath(".//p")]
        text = "\n\n".join(p for p in paragraphs if len(p) > 40)
        if len(text) > len(best):
            best = text
    return best


def extract_from_html(page: str, preview: str = "") -> ExtractResult:
    if is_paywalled(page):
        return ExtractResult("anteprima", reason="La pagina indica che l'articolo è riservato agli abbonati.")
    meta = _meta(page)
    body, author, subtitle = _jsonld_article(page)
    text = ""
    if trafilatura is not None:
        try:
            text = trafilatura.extract(page, include_comments=False, include_tables=False,
                                       favor_precision=True) or ""
        except Exception:  # l'estrattore esterno non deve far cadere il programma
            log.exception("trafilatura ha generato un errore")
            text = ""
        text = "\n\n".join(p.strip() for p in text.split("\n") if p.strip())
    if len(body) > len(text):
        text = body
    if len(text) < MIN_FULL_CHARS:
        alt = _lxml_extract(page)
        if len(alt) > len(text):
            text = alt
    author = author or meta.get("author", "") or meta.get("article:author", "")
    if author.startswith("http"):
        author = ""
    subtitle = subtitle or meta.get("og:description", "") or meta.get("description", "")
    needed = max(MIN_FULL_CHARS, int(len(preview) * 1.3))
    if len(text) >= needed:
        if subtitle and subtitle.strip() == preview.strip():
            subtitle = ""
        return ExtractResult("completo", text=text, author=author, subtitle=subtitle[:400])
    return ExtractResult("anteprima", author=author, subtitle=subtitle[:400],
                         reason="Il testo integrale non è disponibile sulla pagina pubblica.")


def fetch_full_text(url: str, preview: str = "") -> ExtractResult:
    if not url:
        return ExtractResult("anteprima", reason="Collegamento all'articolo assente.")
    try:
        resp = requests.get(url, timeout=20, headers={
            "User-Agent": config.USER_AGENT, "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "it-IT,it;q=0.9,en;q=0.7"})
    except requests.RequestException as exc:
        return ExtractResult("anteprima", reason=f"Pagina non raggiungibile ({exc.__class__.__name__}).")
    if resp.status_code in (401, 402, 403):
        return ExtractResult("anteprima", reason="L'accesso alla pagina è riservato.")
    if resp.status_code >= 400:
        return ExtractResult("anteprima", reason=f"La pagina ha risposto con errore {resp.status_code}.")
    resp.encoding = resp.encoding if resp.encoding and resp.encoding.lower() != "iso-8859-1" else resp.apparent_encoding
    return extract_from_html(resp.text, preview)


def save_extract(db, article_id: int, result: ExtractResult):
    if result.status == "completo":
        db.execute("UPDATE articles SET content = ?, content_status = 'completo', "
                   "author = CASE WHEN author = '' THEN ? ELSE author END, "
                   "subtitle = CASE WHEN subtitle = '' THEN ? ELSE subtitle END WHERE id = ?",
                   (result.text, result.author, result.subtitle, article_id))
        db.fts_index(article_id)
    else:
        db.execute("UPDATE articles SET author = CASE WHEN author = '' THEN ? ELSE author END, "
                   "subtitle = CASE WHEN subtitle = '' THEN ? ELSE subtitle END WHERE id = ?",
                   (result.author, result.subtitle, article_id))
    db.commit()


def split_paragraphs(text: str):
    """Paragrafi non vuoti di un testo (separatore: riga vuota o a capo)."""
    parts = re.split(r"\n\s*\n|\n", text or "")
    return [p.strip() for p in parts if p.strip()]


def build_reader_text(article, catalog_name: str = ""):
    """Testo mostrato nel lettore e mappa dei paragrafi [(inizio, fine)]
    da usare con la sintesi vocale. Restituisce (testo, paragrafi, offset)."""
    from .models import format_date, CONTENT_LABELS
    header = [article.title]
    if article.subtitle:
        header.append(article.subtitle)
    header.append(f"Testata: {article.source_name}")
    header.append(f"Data: {format_date(article.published, with_weekday=True)}")
    if article.author:
        header.append(f"Autore: {article.author}")
    header.append(f"Categoria: {catalog_name or article.category_name}")
    header.append(f"Stato del testo: {CONTENT_LABELS.get(article.content_status, article.content_status)}")
    body = split_paragraphs(article.body_text) or ["Per questo articolo il feed non fornisce testo."]
    footer = []
    if article.is_partial:
        footer.append("Attenzione: questo è soltanto un estratto. Il testo completo è disponibile "
                      "sul sito della testata: usa il pulsante Apri articolo originale.")
    if article.link:
        footer.append(f"Fonte originale: {article.link}")
    paragraphs = header + [""] + body + [""] + footer
    text_parts, offsets, pos = [], [], 0
    spoken = []
    for p in paragraphs:
        if p:
            offsets.append((pos, pos + len(p)))
            spoken.append(p)
        text_parts.append(p)
        pos += len(p) + 1  # '\n'
    return "\n".join(text_parts), spoken, offsets


def mark_fetched(db, article_id):
    db.execute("UPDATE articles SET fetched = ? WHERE id = ?", (now_iso(), article_id))
    db.commit()
