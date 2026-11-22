"""Elenco delle novità di KILLA NEWS (file data/novita.md).

Formato del file:
    ## Versione 1.4.0 (data)
    - Aggiunto: ...
    - Corretto: ...
    - Modificato: ..."""
import re

from . import config
from .app_updates import is_newer, parse_version

_HEAD = re.compile(r"^##\s*Versione\s+(\d+(?:\.\d+)*)\s*(?:\((.*?)\))?\s*$", re.M)
KINDS = ("Aggiunto", "Corretto", "Modificato")


def parse(text):
    """[(versione, data, [righe])] dalla più recente alla più vecchia."""
    out = []
    matches = list(_HEAD.finditer(text or ""))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        lines = [ln.strip()[2:].strip() for ln in text[m.end():end].splitlines() if ln.strip().startswith("- ")]
        out.append((m.group(1), m.group(2) or "", lines))
    out.sort(key=lambda s: parse_version(s[0]), reverse=True)
    return out


def load():
    try:
        with open(config.data_file("novita.md"), encoding="utf-8") as fh:
            return parse(fh.read())
    except OSError:
        return []


def between(sections, old, new):
    """Sezioni con versione > old e <= new."""
    return [s for s in sections if is_newer(s[0], old) and not is_newer(s[0], new)]


def as_text(sections, new_version, old_version="", title=""):
    """Testo leggibile con le frecce: versione nuova, versione precedente e novità."""
    lines = []
    if title:
        lines.append(title)
    lines.append(f"Versione nuova: {new_version}")
    if old_version:
        lines.append(f"Versione precedente: {old_version}")
    lines.append("")
    if not sections:
        lines.append("Nessuna novità descritta per questa versione.")
    for version, date, items in sections:
        lines.append(f"Novità della versione {version}" + (f", {date}" if date else "") + ":")
        for item in items:
            lines.append("- " + item)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
