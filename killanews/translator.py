"""Traduzione automatica degli articoli in italiano.

Usa il servizio di traduzione gratuito di Google (lo stesso usato da molti componenti
aggiuntivi di NVDA), senza account né chiavi. Se non risponde prova MyMemory.
Le traduzioni vengono salvate nel database: lo stesso articolo si traduce una volta sola."""
import logging
import re

import requests

from . import config

log = logging.getLogger(__name__)

TARGET = "it"
_MAX_CHUNK = 1800
_TIMEOUT = 20

LANGUAGE_NAMES = {
    "it": "italiano", "en": "inglese", "fr": "francese", "de": "tedesco", "es": "spagnolo", "pt": "portoghese",
    "nl": "olandese", "sv": "svedese", "no": "norvegese", "nb": "norvegese", "da": "danese", "fi": "finlandese",
    "pl": "polacco", "ro": "rumeno", "el": "greco", "tr": "turco", "ru": "russo", "uk": "ucraino",
    "cs": "ceco", "hu": "ungherese", "ar": "arabo", "he": "ebraico", "iw": "ebraico", "fa": "persiano",
    "ja": "giapponese", "zh": "cinese", "zh-CN": "cinese", "zh-TW": "cinese", "ko": "coreano", "hi": "hindi",
    "ur": "urdu", "bn": "bengalese", "id": "indonesiano", "ms": "malese", "th": "thailandese",
    "vi": "vietnamita", "tl": "filippino", "sw": "swahili", "hr": "croato", "sr": "serbo", "bg": "bulgaro",
}


class TranslationError(Exception):
    pass


def language_name(code: str) -> str:
    if not code:
        return "lingua sconosciuta"
    return LANGUAGE_NAMES.get(code, LANGUAGE_NAMES.get(code.split("-")[0], code))


def _chunks(text: str):
    """Divide il testo in blocchi di paragrafi interi, abbastanza piccoli per il servizio."""
    out, cur = [], ""
    for par in text.split("\n"):
        while len(par) > _MAX_CHUNK:  # paragrafo lunghissimo: si taglia alla fine di una frase
            cut = max(par.rfind(". ", 0, _MAX_CHUNK), par.rfind(" ", 0, _MAX_CHUNK))
            cut = cut + 1 if cut > 0 else _MAX_CHUNK
            if cur:
                out.append(cur)
                cur = ""
            out.append(par[:cut])
            par = par[cut:].lstrip()
        if len(cur) + len(par) + 1 > _MAX_CHUNK and cur:
            out.append(cur)
            cur = par
        else:
            cur = f"{cur}\n{par}" if cur else par
    if cur:
        out.append(cur)
    return out


def _google(chunk: str, session):
    r = session.get("https://translate.googleapis.com/translate_a/single",
                    params={"client": "gtx", "sl": "auto", "tl": TARGET, "dt": "t", "q": chunk},
                    timeout=_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    text = "".join(part[0] for part in (data[0] or []) if part and part[0])
    lang = data[2] if len(data) > 2 and isinstance(data[2], str) else ""
    return text, lang


def _mymemory(chunk: str, session, source_lang: str):
    if not source_lang or source_lang == TARGET:
        raise TranslationError("lingua di partenza sconosciuta")
    r = session.get("https://api.mymemory.translated.net/get",
                    params={"q": chunk[:480], "langpair": f"{source_lang}|{TARGET}"}, timeout=_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if str(data.get("responseStatus")) != "200":
        raise TranslationError(data.get("responseDetails") or "servizio non disponibile")
    return data["responseData"]["translatedText"], source_lang


def translate_text(text: str, source_lang: str = "", session=None):
    """Traduce il testo in italiano. Restituisce (traduzione, lingua_originale)."""
    text = (text or "").strip()
    if not text:
        return "", source_lang
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", config.USER_AGENT)
    out, lang = [], source_lang
    for chunk in _chunks(text):
        try:
            translated, detected = _google(chunk, session)
        except Exception as exc:  # rete, limite di richieste, risposta inattesa
            log.warning("Traduzione Google non riuscita: %s", exc)
            try:
                translated, detected = _mymemory(chunk, session, lang)
            except Exception as exc2:
                raise TranslationError(
                    "Il servizio di traduzione non risponde. Controlla la connessione a Internet e riprova "
                    "tra qualche minuto.") from exc2
        lang = lang or detected
        out.append(translated)
    return "\n".join(out), lang


def looks_italian(text: str) -> bool:
    """Stima veloce, senza rete: il testo sembra già in italiano?"""
    words = re.findall(r"[a-zàèéìòù]+", (text or "").lower())[:300]
    if len(words) < 5:
        return False
    common = {"il", "la", "di", "che", "e", "per", "un", "una", "del", "della", "non", "con", "nel", "sono",
              "alla", "gli", "dei", "le", "da", "anche", "è", "più", "ha", "delle"}
    return sum(1 for w in words if w in common) / len(words) > 0.12


class TranslationStore:
    """Traduzioni salvate nel database (tabella translations)."""

    def __init__(self, db):
        self.db = db

    def get(self, article_id):
        row = self.db.query_one("SELECT * FROM translations WHERE article_id = ? AND target = ?",
                                (article_id, TARGET))
        return dict(row) if row else None

    def save(self, article_id, source_lang, title, subtitle, body, body_hash):
        with self.db.conn:
            self.db.execute(
                "INSERT INTO translations(article_id, target, source_lang, title, subtitle, body, body_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(article_id, target) DO UPDATE SET "
                "source_lang=excluded.source_lang, title=excluded.title, subtitle=excluded.subtitle, "
                "body=excluded.body, body_hash=excluded.body_hash",
                (article_id, TARGET, source_lang, title, subtitle, body, body_hash))


def body_hash(text: str) -> str:
    import hashlib
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()


def translate_article(article, store=None, session=None):
    """Traduce titolo, sottotitolo e testo di un articolo (usa la copia salvata se c'è).
    Restituisce un dict con title, subtitle, body, source_lang."""
    h = body_hash(article.body_text)
    if store:
        cached = store.get(article.id)
        if cached and cached["body_hash"] == h:
            return cached
    session = session or requests.Session()
    joined = "\n".join(p for p in (article.title, article.subtitle) if p)
    head, lang = translate_text(joined, session=session)
    body, lang = translate_text(article.body_text, lang, session=session) if article.body_text else ("", lang)
    head_lines = head.split("\n")
    title = head_lines[0] if head_lines else article.title
    subtitle = "\n".join(head_lines[1:]) if article.subtitle else ""
    result = {"title": title, "subtitle": subtitle, "body": body, "source_lang": lang, "body_hash": h}
    if store:
        try:
            store.save(article.id, lang, title, subtitle, body, h)
        except Exception as exc:  # la traduzione resta valida anche se non si riesce a salvarla
            log.warning("Traduzione non salvata: %s", exc)
    return result


__all__ = ["translate_text", "translate_article", "TranslationStore", "TranslationError", "language_name",
           "looks_italian"]
