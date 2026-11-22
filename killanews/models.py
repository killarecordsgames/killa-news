"""Modelli dati e funzioni di formattazione condivise."""
import datetime
from dataclasses import dataclass, field

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]
GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]

CONTENT_LABELS = {
    "completo": "testo completo",
    "anteprima": "testo parziale (anteprima del feed)",
    "non_disponibile": "testo non disponibile",
}


@dataclass
class Article:
    id: int
    title: str
    source_name: str
    source_id: int
    published: str
    category_id: str = "generale"
    category_name: str = ""
    subtitle: str = ""
    description: str = ""
    content: str = ""
    content_status: str = "anteprima"
    author: str = ""
    link: str = ""
    site_url: str = ""
    fulltext_allowed: bool = False
    saved: bool = False
    offline: bool = False
    to_read: bool = False
    folder_name: str = ""
    last_viewed: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def body_text(self) -> str:
        return self.content or self.description or ""

    @property
    def is_partial(self) -> bool:
        return self.content_status != "completo"

    def status_label(self) -> str:
        parts = []
        if self.saved:
            parts.append("salvato")
        if self.to_read:
            parts.append("da leggere")
        if self.offline:
            parts.append("disponibile offline")
        return ", ".join(parts)


def parse_iso(value: str):
    if not value:
        return None
    try:
        dt = datetime.datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def local_dt(value: str):
    dt = parse_iso(value)
    return dt.astimezone() if dt else None


def format_date(value: str, with_weekday: bool = False) -> str:
    """Data leggibile in italiano, ad esempio '20 novembre 2026, ore 14:05'."""
    dt = local_dt(value)
    if not dt:
        return "data non indicata"
    text = f"{dt.day} {MESI[dt.month - 1]} {dt.year}, ore {dt.hour:02d}:{dt.minute:02d}"
    if with_weekday:
        text = f"{GIORNI[dt.weekday()]} {text}"
    return text


def format_date_short(value: str) -> str:
    """Formato compatto per gli elenchi: 'oggi 14:05', 'ieri 09:10', '18/11/2026 08:00'."""
    dt = local_dt(value)
    if not dt:
        return "senza data"
    today = datetime.datetime.now().astimezone().date()
    if dt.date() == today:
        return f"oggi {dt.hour:02d}:{dt.minute:02d}"
    if dt.date() == today - datetime.timedelta(days=1):
        return f"ieri {dt.hour:02d}:{dt.minute:02d}"
    return f"{dt.day:02d}/{dt.month:02d}/{dt.year} {dt.hour:02d}:{dt.minute:02d}"


def format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("byte", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "byte" else f"{size:.1f} {unit}".replace(".", ",")
        size /= 1024
    return f"{size:.1f} GB"
