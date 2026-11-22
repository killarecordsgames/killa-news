"""Statistiche anonime d'uso di KILLA NEWS (si possono disattivare nelle Impostazioni).

Ogni installazione ha un identificativo casuale, creato al primo avvio e non legato a
nessuna persona. Vengono inviati solo: identificativo casuale, versione, tipo di
installazione, quante volte il programma è stato aperto e quante volte sono state usate
le sezioni (per esempio «sport: 3»). Nessun titolo, testo, ricerca, nome o indirizzo.
Se l'invio non riesce i conteggi restano salvati e partono la volta successiva."""
import json
import logging
import threading
import uuid

import requests

from . import config

log = logging.getLogger(__name__)

ENDPOINT = "https://srkepkkkwrmutzcecrdw.supabase.co/functions/v1/killa-news-statistiche"

SECTIONS = ("prima_pagina", "tutti_i_giornali", "italia", "cronaca", "economia", "sport", "tecnologia", "cultura",
            "salute", "giornali_locali", "giornali_internazionali", "notizie_dal_mondo", "articoli_salvati",
            "cronologia", "cerca", "killa_records", "articoli_letti", "traduzioni", "condivisioni", "voce_nvda")

_CATEGORY_SECTION = {"italia": "italia", "cronaca": "cronaca", "economia": "economia", "sport": "sport",
                     "tecnologia": "tecnologia", "cultura": "cultura", "salute": "salute",
                     "esteri": "notizie_dal_mondo"}


def section_of(view) -> str:
    """Sezione del menu a cui appartiene una vista ('' se non interessa)."""
    if not view:
        return ""
    kind = view.get("kind", "")
    key = str(view.get("key", ""))
    if kind.startswith("home"):
        return "prima_pagina"
    if kind == "international" or key == "international" or key.startswith(("int-", "int_", "intc", "intcont")):
        return "giornali_internazionali"
    if kind == "local" or key == "local" or key.startswith(("loc-", "local", "city", "region", "prov")):
        return "giornali_locali"
    if kind == "category":
        return _CATEGORY_SECTION.get(str(view.get("category_id", "")).split("/")[0], "")
    if kind in ("all", "group", "source"):
        return "tutti_i_giornali"
    if kind in ("saved", "offline"):
        return "articoli_salvati"
    if kind == "history":
        return "cronologia"
    if kind in ("search", "search_panel"):
        return "cerca"
    if key == "killa" or key.startswith("killa:"):
        return "killa_records"
    return ""


class Stats:
    def __init__(self, settings):
        self.settings = settings
        self._lock = threading.Lock()
        self._counts = {}
        self._opens = 0
        self._sending = False
        try:
            saved = json.loads(settings.get("stats_pending", "") or "{}")
            self._counts = {k: int(v) for k, v in saved.get("sezioni", {}).items() if k in SECTIONS}
            self._opens = int(saved.get("aperture", 0))
        except (ValueError, TypeError, AttributeError):
            pass

    @property
    def enabled(self):
        return bool(self.settings.get("send_usage_stats", True))

    def installation_id(self):
        value = self.settings.get("stats_id", "") or ""
        if len(value) != 32:
            value = uuid.uuid4().hex
            self.settings.set("stats_id", value, notify=False)
        return value

    def count(self, section, amount=1):
        if section in SECTIONS and self.enabled:
            with self._lock:
                self._counts[section] = self._counts.get(section, 0) + amount

    def count_view(self, view):
        self.count(section_of(view))

    def program_opened(self):
        if self.enabled:
            with self._lock:
                self._opens += 1

    def save(self):
        """Conserva i conteggi non ancora inviati (alla chiusura del programma)."""
        with self._lock:
            data = {"sezioni": dict(self._counts), "aperture": self._opens}
        self.settings.set("stats_pending", json.dumps(data), notify=False)

    def payload(self, install_kind):
        with self._lock:
            return {"installazione": self.installation_id(), "versione": config.APP_VERSION, "tipo": install_kind,
                    "aperture": self._opens, "sezioni": dict(self._counts)}

    def send(self, install_kind, session=None, background=True):
        """Invia i conteggi e, se l'invio riesce, li azzera."""
        if not self.enabled:
            with self._lock:
                self._counts, self._opens = {}, 0
            self.settings.set("stats_pending", "", notify=False)
            return
        if self._sending:
            return
        data = self.payload(install_kind)
        if not data["aperture"] and not data["sezioni"]:
            return
        self._sending = True

        def work():
            try:
                s = session or requests.Session()
                r = s.post(ENDPOINT, json=data, timeout=15, headers={"User-Agent": config.USER_AGENT})
                if r.status_code == 200:
                    with self._lock:
                        for k, v in data["sezioni"].items():
                            self._counts[k] = max(0, self._counts.get(k, 0) - v)
                            if not self._counts[k]:
                                del self._counts[k]
                        self._opens = max(0, self._opens - data["aperture"])
                else:
                    log.info("Statistiche non inviate: risposta %s", r.status_code)
            except Exception as exc:  # senza rete si riprova la volta dopo
                log.info("Statistiche non inviate: %s", exc)
            finally:
                self._sending = False

        if background:
            threading.Thread(target=work, name="statistiche", daemon=True).start()
        else:
            work()
