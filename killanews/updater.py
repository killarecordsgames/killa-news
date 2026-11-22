"""Aggiornamento delle fonti in background (automatico ogni N minuti e manuale).

L'aggiornamento gira in un thread separato con una propria connessione al database:
l'interfaccia non si blocca e la lettura dell'utente non viene interrotta. I feed
vengono scaricati in parallelo e salvati in sequenza. I risultati sono comunicati con
una funzione di richiamo: l'interfaccia la inoltra al proprio thread (wx.CallAfter)."""
import datetime
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from . import feed_manager
from .catalog import Catalog
from .database import Database, now_iso

log = logging.getLogger(__name__)


@dataclass
class UpdateSummary:
    started_at: str = ""
    finished_at: str = ""
    checked: int = 0
    new_articles: int = 0
    failed: list = field(default_factory=list)   # [(nome testata, url, errore)]
    offline: bool = False
    manual: bool = False
    removed_old: int = 0
    cancelled: bool = False
    discovered: list = field(default_factory=list)   # [(nome testata, url del feed trovato)]


DISCOVERY_INTERVAL_DAYS = 7
DISCOVERY_MAX_PER_RUN = 8


def discover_missing_feeds(db, catalog, max_sources=DISCOVERY_MAX_PER_RUN, workers=4):
    """Per le testate senza feed cerca i feed che il sito stesso dichiara, li verifica
    e li aggiunge. Ogni testata viene riprovata al massimo una volta alla settimana.
    Restituisce [(nome testata, url, feed_id)]."""
    now = datetime.datetime.now(datetime.timezone.utc)
    candidates = []
    for src in catalog.sources(include_disabled=False):
        if src["feed_count"] or not src["site_url"]:
            continue
        last = db.get_setting_raw(f"discovery:{src['id']}")
        if last:
            try:
                if now - datetime.datetime.fromisoformat(last) < datetime.timedelta(days=DISCOVERY_INTERVAL_DAYS):
                    continue
            except ValueError:
                pass
        candidates.append(src)
        if len(candidates) >= max_sources:
            break
    if not candidates:
        return []

    def work(src):
        try:
            return src, feed_manager.discover_feeds(src["site_url"])
        except Exception as exc:
            log.info("Ricerca feed non riuscita per %s: %s", src["name"], exc)
            return src, []

    found = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for src, feeds in pool.map(work, candidates):
            db.set_setting_raw(f"discovery:{src['id']}", now.replace(microsecond=0).isoformat())
            useful = [(u, t) for u, t in feeds if "comment" not in (t + u).lower()][:2]
            category = "italia/cronaca_locale" if src["region"] else "generale"
            for url, _title in useful:
                catalog.add_feed(src["id"], url, category, "trovato automaticamente sul sito della testata")
                row = db.query_one("SELECT id FROM feeds WHERE source_id = ? AND url = ?", (src["id"], url))
                found.append((src["name"], url, row["id"] if row else None))
    return found


class Updater:
    def __init__(self, db_path, interval_seconds, auto_enabled, retention_days,
                 on_start=None, on_done=None, max_workers=6):
        self.db_path = db_path
        self.interval_seconds = interval_seconds      # funzione -> int
        self.auto_enabled = auto_enabled              # funzione -> bool
        self.retention_days = retention_days          # funzione -> int
        self.on_start = on_start
        self.on_done = on_done
        self.max_workers = max_workers
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._manual = False
        self._only_source = None
        self._lock = threading.Lock()
        self._thread = None
        self.running = False
        self.last_summary = None
        self._next_auto = 0.0

    def start(self, initial_delay=3.0):
        self._next_auto = time.monotonic() + initial_delay
        self._thread = threading.Thread(target=self._loop, name="KillaNewsUpdater", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._wake.set()

    def trigger(self, source_id=None):
        """Richiede un aggiornamento immediato (manuale)."""
        with self._lock:
            self._manual = True
            self._only_source = source_id
        self._wake.set()

    def reschedule(self):
        self._next_auto = time.monotonic() + self.interval_seconds()
        self._wake.set()

    def _loop(self):
        while not self._stop.is_set():
            timeout = max(0.5, self._next_auto - time.monotonic())
            self._wake.wait(timeout)
            self._wake.clear()
            if self._stop.is_set():
                break
            with self._lock:
                manual, only_source = self._manual, self._only_source
                self._manual, self._only_source = False, None
            due = time.monotonic() >= self._next_auto
            if manual or (due and self.auto_enabled()):
                try:
                    self.run_once(manual=manual, source_id=only_source)
                except Exception:
                    log.exception("Errore inatteso durante l'aggiornamento")
                    self.running = False
            if due or manual:
                self._next_auto = time.monotonic() + self.interval_seconds()

    def run_once(self, manual=False, source_id=None) -> UpdateSummary:
        summary = UpdateSummary(started_at=now_iso(), manual=manual)
        self.running = True
        if self.on_start:
            self.on_start(manual)
        db = Database(self.db_path)
        try:
            catalog = Catalog(db)
            feeds = [f for f in catalog.feeds(source_id=source_id, only_enabled=True)]
            names = {f["id"]: f["source_name"] for f in feeds}
            urls = {f["id"]: f["url"] for f in feeds}
            network_errors = 0
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                futures = [pool.submit(feed_manager.fetch_feed, f) for f in feeds]
                for future in as_completed(futures):
                    if self._stop.is_set():
                        summary.cancelled = True
                        break
                    try:
                        result = future.result()
                    except Exception:  # non dovrebbe accadere: fetch_feed gestisce gli errori
                        log.exception("Errore nel recupero di un feed")
                        continue
                    summary.checked += 1
                    try:
                        summary.new_articles += feed_manager.store_result(db, catalog, result)
                    except Exception:
                        log.exception("Errore nel salvataggio del feed %s", urls.get(result.feed_id))
                        result.ok, result.error = False, "errore: dati non salvati"
                    if not result.ok:
                        if result.network_error:
                            network_errors += 1
                        summary.failed.append((names.get(result.feed_id, "?"), urls.get(result.feed_id, ""),
                                               result.error))
            summary.offline = bool(feeds) and network_errors == len(feeds)
            if not summary.offline and not self._stop.is_set():
                try:
                    found = discover_missing_feeds(db, catalog) if source_id is None else []
                except Exception:
                    log.exception("Errore nella ricerca automatica dei feed")
                    found = []
                for name, url, feed_id in found:
                    summary.discovered.append((name, url))
                    feed = db.query_one("SELECT * FROM feeds WHERE id = ?", (feed_id,)) if feed_id else None
                    if feed:
                        try:
                            summary.new_articles += feed_manager.store_result(
                                db, catalog, feed_manager.fetch_feed(feed))
                        except Exception:
                            log.exception("Errore nel primo download del feed trovato %s", url)
            if not summary.offline:
                summary.removed_old = feed_manager.prune_old_articles(db, self.retention_days())
        finally:
            db.close()
            self.running = False
        summary.finished_at = now_iso()
        self.last_summary = summary
        if self.on_done:
            self.on_done(summary)
        return summary
